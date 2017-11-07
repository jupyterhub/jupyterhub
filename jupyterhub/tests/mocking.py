"""mock utilities for testing"""

import os
import sys
from tempfile import NamedTemporaryFile
import threading
from unittest import mock
from urllib.parse import urlparse

from tornado import gen
from tornado.concurrent import Future
from tornado.ioloop import IOLoop

from traitlets import default

from ..app import JupyterHub
from ..auth import PAMAuthenticator
from .. import orm
from ..objects import Server
from ..spawner import LocalProcessSpawner
from ..singleuser import SingleUserNotebookApp
from ..utils import random_port, url_path_join
from .utils import async_requests

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

    use_this_api_token = None
    def start(self):
        if self.use_this_api_token:
            self.api_token = self.use_this_api_token
        elif self.will_resume:
            self.use_this_api_token = self.api_token
        return super().start()

class SlowSpawner(MockSpawner):
    """A spawner that takes a few seconds to start"""

    delay = 2
    _start_future = None
    @gen.coroutine
    def start(self):
        (ip, port) = yield super().start()
        if self._start_future is not None:
            yield self._start_future
        else:
            yield gen.sleep(self.delay)
        return ip, port

    @gen.coroutine
    def stop(self):
        yield gen.sleep(self.delay)
        yield super().stop()


class NeverSpawner(MockSpawner):
    """A spawner that will never start"""

    @default('start_timeout')
    def _start_timeout_default(self):
        return 1

    def start(self):
        """Return a Future that will never finish"""
        return Future()

    @gen.coroutine
    def stop(self):
        pass

    @gen.coroutine
    def poll(self):
        return 0


class BadSpawner(MockSpawner):
    """Spawner that fails immediately"""
    def start(self):
        raise RuntimeError("I don't work!")


class SlowBadSpawner(MockSpawner):
    """Spawner that fails after a short delay"""

    @gen.coroutine
    def start(self):
        yield gen.sleep(0.1)
        raise RuntimeError("I don't work!")



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
    auth_state = None
    @default('admin_users')
    def _admin_users_default(self):
        return {'admin'}
    
    def system_user_exists(self, user):
        # skip the add-system-user bit
        return not user.name.startswith('dne')
    
    @gen.coroutine
    def authenticate(self, *args, **kwargs):
        with mock.patch.multiple('pamela',
                authenticate=mock_authenticate,
                open_session=mock_open_session,
                close_session=mock_open_session,
                ):
            username = yield super(MockPAMAuthenticator, self).authenticate(*args, **kwargs)
        if username is None:
            return
        if self.auth_state:
            return {
                'name': username,
                'auth_state': self.auth_state,
            }
        else:
            return username


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

    @default('port')
    def _port_default(self):
        if self.subdomain_host:
            port = urlparse(self.subdomain_host).port
            if port:
                return port
        return random_port()

    @default('authenticator_class')
    def _authenticator_class_default(self):
        return MockPAMAuthenticator
    
    @default('spawner_class')
    def _spawner_class_default(self):
        return MockSpawner
    
    def init_signal(self):
        pass

    def load_config_file(self, *args, **kwargs):
        pass

    @gen.coroutine
    def initialize(self, argv=None):
        self.pid_file = NamedTemporaryFile(delete=False).name
        self.db_file = NamedTemporaryFile()
        self.db_url = os.getenv('JUPYTERHUB_TEST_DB_URL') or self.db_file.name
        yield super().initialize([])

        # add an initial user
        user = self.db.query(orm.User).filter(orm.User.name == 'user').first()
        if user is None:
            user = orm.User(name='user')
            self.db.add(user)
            self.db.commit()

    def stop(self):
        super().stop()
        IOLoop().run_sync(self.cleanup)
        # ignore the call that will fire in atexit
        self.cleanup = lambda : None
        self.db_file.close()
    
    @gen.coroutine
    def login_user(self, name):
        """Login a user by name, returning her cookies."""
        base_url = public_url(self)
        r = yield async_requests.post(base_url + 'hub/login',
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
        return Server.from_url(app.proxy.public_url).host


def public_url(app, user_or_service=None, path=''):
    """Return the full, public base URL (including prefix) of the given JupyterHub instance."""
    if user_or_service:
        if app.subdomain_host:
            host = user_or_service.host
        else:
            host = public_host(app)
        prefix = user_or_service.prefix
    else:
        host = public_host(app)
        prefix = Server.from_url(app.proxy.public_url).base_url
    if path:
        return host + url_path_join(prefix, path)
    else:
        return host + prefix


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
        ip = self.ip = '127.0.0.1'
        port = self.port = random_port()
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
                assert app.hub_auth.oauth_client_id
                assert app.hub_auth.api_token
                app.start()

        self._thread = threading.Thread(target=_run)
        self._thread.start()
        ready = evt.wait(timeout=3)
        assert ready
        return (ip, port)

    @gen.coroutine
    def stop(self):
        self._app.stop()
        self._thread.join(timeout=30)
        assert not self._thread.is_alive()

    @gen.coroutine
    def poll(self):
        if self._thread is None:
            return 0
        if self._thread.is_alive():
            return None
        else:
            return 0

