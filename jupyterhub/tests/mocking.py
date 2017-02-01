"""mock utilities for testing"""

import os
import sys
from tempfile import NamedTemporaryFile
import threading

from unittest import mock

import requests

from tornado import gen
from tornado.concurrent import Future
from tornado.ioloop import IOLoop

from traitlets import default

from ..app import JupyterHub
from ..auth import PAMAuthenticator
from .. import orm
from ..spawner import LocalProcessSpawner
from ..singleuser import SingleUserNotebookApp
from ..utils import random_port

from pamela import PAMError

def mock_authenticate(username, password, service='login'):
    # just use equality for testing
    if password == username:
        return True
    else:
        raise PAMError("Fake")


def mock_open_session(username, service):
    pass


class MockSpawner(LocalProcessSpawner):
    """Base mock spawner
    
    - disables user-switching that we need root permissions to do
    - spawns jupyterhub.tests.mocksu instead of a full single-user server
    """
    def make_preexec_fn(self, *a, **kw):
        # skip the setuid stuff
        return
    
    def _set_user_changed(self, name, old, new):
        pass
    
    def user_env(self, env):
        return env

    @default('cmd')
    def _cmd_default(self):
        return [sys.executable, '-m', 'jupyterhub.tests.mocksu']


class SlowSpawner(MockSpawner):
    """A spawner that takes a few seconds to start"""
    
    @gen.coroutine
    def start(self):
        (ip, port) = yield super().start()
        yield gen.sleep(2)
        return ip, port
    
    @gen.coroutine
    def stop(self):
        yield gen.sleep(2)
        yield super().stop()


class NeverSpawner(MockSpawner):
    """A spawner that will never start"""
    
    @default('start_timeout')
    def _start_timeout_default(self):
        return 1
    
    def start(self):
        """Return a Future that will never finish"""
        return Future()


class FormSpawner(MockSpawner):
    """A spawner that has an options form defined"""
    options_form = "IMAFORM"
    
    def options_from_form(self, form_data):
        options = {}
        options['notspecified'] = 5
        if 'bounds' in form_data:
            options['bounds'] = [int(i) for i in form_data['bounds']]
        if 'energy' in form_data:
            options['energy'] = form_data['energy'][0]
        if 'hello_file' in form_data:
            options['hello'] = form_data['hello_file'][0]
        return options


class MockPAMAuthenticator(PAMAuthenticator):
    @default('admin_users')
    def _admin_users_default(self):
        return {'admin'}
    
    def system_user_exists(self, user):
        # skip the add-system-user bit
        return not user.name.startswith('dne')
    
    def authenticate(self, *args, **kwargs):
        with mock.patch.multiple('pamela',
                authenticate=mock_authenticate,
                open_session=mock_open_session,
                close_session=mock_open_session,
                ):
            return super(MockPAMAuthenticator, self).authenticate(*args, **kwargs)


class MockHub(JupyterHub):
    """Hub with various mock bits"""

    db_file = None
    
    last_activity_interval = 2
    
    base_url = '/@/space%20word/'
    
    log_datefmt = '%M:%S'
    
    @default('subdomain_host')
    def _subdomain_host_default(self):
        return os.environ.get('JUPYTERHUB_TEST_SUBDOMAIN_HOST', '')
    
    @default('ip')
    def _ip_default(self):
        return '127.0.0.1'
    
    @default('authenticator_class')
    def _authenticator_class_default(self):
        return MockPAMAuthenticator
    
    @default('spawner_class')
    def _spawner_class_default(self):
        return MockSpawner
    
    def init_signal(self):
        pass
    
    def start(self, argv=None):
        self.db_file = NamedTemporaryFile()
        self.pid_file = NamedTemporaryFile(delete=False).name
        self.db_url = self.db_file.name
        
        evt = threading.Event()
        
        @gen.coroutine
        def _start_co():
            assert self.io_loop._running
            # put initialize in start for SQLAlchemy threading reasons
            yield super(MockHub, self).initialize(argv=argv)
            # add an initial user
            user = orm.User(name='user')
            self.db.add(user)
            self.db.commit()
            yield super(MockHub, self).start()
            yield self.hub.server.wait_up(http=True)
            self.io_loop.add_callback(evt.set)
        
        def _start():
            self.io_loop = IOLoop()
            self.io_loop.make_current()
            self.io_loop.add_callback(_start_co)
            self.io_loop.start()
        
        self._thread = threading.Thread(target=_start)
        self._thread.start()
        ready = evt.wait(timeout=10)
        assert ready
    
    def stop(self):
        super().stop()
        self._thread.join()
        IOLoop().run_sync(self.cleanup)
        # ignore the call that will fire in atexit
        self.cleanup = lambda : None
        self.db_file.close()
    
    def login_user(self, name):
        """Login a user by name, returning her cookies."""
        base_url = public_url(self)
        r = requests.post(base_url + 'hub/login',
            data={
                'username': name,
                'password': name,
            },
            allow_redirects=False,
        )
        r.raise_for_status()
        assert r.cookies
        return r.cookies


def public_host(app):
    """Return the public *host* (no URL prefix) of the given JupyterHub instance."""
    if app.subdomain_host:
        return app.subdomain_host
    else:
        return app.proxy.public_server.host


def public_url(app, user_or_service=None):
    """Return the full, public base URL (including prefix) of the given JupyterHub instance."""
    if user_or_service:
        if app.subdomain_host:
            host = user_or_service.host
        else:
            host = public_host(app)
        return host + user_or_service.server.base_url
    else:
        return public_host(app) + app.proxy.public_server.base_url


# single-user-server mocking:

class MockSingleUserServer(SingleUserNotebookApp):
    """Mock-out problematic parts of single-user server when run in a thread
    
    Currently:
    
    - disable signal handler
    """

    def init_signal(self):
        pass


class StubSingleUserSpawner(MockSpawner):
    """Spawner that starts a MockSingleUserServer in a thread."""
    _thread = None
    @gen.coroutine
    def start(self):
        self.user.server.port = random_port()
        env = self.get_env()
        args = self.get_args()
        evt = threading.Event()
        print(args, env)
        def _run():
            io_loop = IOLoop()
            io_loop.make_current()
            io_loop.add_callback(lambda : evt.set())
            
            with mock.patch.dict(os.environ, env):
                app = self._app = MockSingleUserServer()
                app.initialize(args)
                app.start()
        
        self._thread = threading.Thread(target=_run)
        self._thread.start()
        ready = evt.wait(timeout=3)
        assert ready
    
    @gen.coroutine
    def stop(self):
        self._app.stop()
        self._thread.join()
    
    @gen.coroutine
    def poll(self):
        if self._thread is None:
            return 0
        if self._thread.is_alive():
            return None
        else:
            return 0

