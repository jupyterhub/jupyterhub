"""mock utilities for testing

Functions
---------
- mock_authenticate
- mock_check_account
- mock_open_session

Spawners
--------
- MockSpawner: based on LocalProcessSpawner
- SlowSpawner:
- NeverSpawner:
- BadSpawner:
- SlowBadSpawner
- FormSpawner

Other components
----------------
- MockPAMAuthenticator
- MockHub
- MockSingleUserServer
- InstrumentedSpawner

- public_host
- public_url

"""

import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from tempfile import NamedTemporaryFile
from unittest import mock
from urllib.parse import urlparse

from pamela import PAMError
from sqlalchemy import event
from tornado.httputil import url_concat
from traitlets import Bool, Dict, default

from .. import metrics, orm, roles
from ..app import JupyterHub
from ..auth import PAMAuthenticator
from ..spawner import SimpleLocalProcessSpawner
from ..utils import random_port, url_path_join, utcnow
from .utils import AsyncSession, public_url, ssl_setup


def mock_authenticate(username, password, service, encoding):
    # just use equality for testing
    if password == username:
        return True
    else:
        raise PAMError("Fake")


def mock_check_account(username, service, encoding):
    if username.startswith('notallowed'):
        raise PAMError("Fake")
    else:
        return True


def mock_open_session(username, service, encoding):
    pass


class MockSpawner(SimpleLocalProcessSpawner):
    """Base mock spawner

    - disables user-switching that we need root permissions to do
    - spawns `jupyterhub.tests.mocksu` instead of a full single-user server
    """

    def user_env(self, env):
        env = super().user_env(env)
        if self.handler:
            env['HANDLER_ARGS'] = self.handler.request.query
        return env

    @default('cmd')
    def _cmd_default(self):
        return [sys.executable, '-m', 'jupyterhub.tests.mocksu']

    use_this_api_token = None

    def start(self):
        # preserve any JupyterHub env in mock spawner
        for key in os.environ:
            if 'JUPYTERHUB' in key and key not in self.env_keep:
                self.env_keep.append(key)

        if self.use_this_api_token:
            self.api_token = self.use_this_api_token
        elif self.will_resume:
            self.use_this_api_token = self.api_token
        return super().start()


class SlowSpawner(MockSpawner):
    """A spawner that takes a few seconds to start"""

    delay = 5
    _start_future = None

    async def start(self):
        (ip, port) = await super().start()
        if self._start_future is not None:
            await self._start_future
        else:
            await asyncio.sleep(self.delay)
        return ip, port

    async def stop(self):
        await asyncio.sleep(self.delay)
        await super().stop()


class NeverSpawner(MockSpawner):
    """A spawner that will never start"""

    @default('start_timeout')
    def _start_timeout_default(self):
        return 1

    def start(self):
        """Return a Future that will never finish"""
        return asyncio.Future()

    async def stop(self):
        pass

    async def poll(self):
        return 0


class BadSpawner(MockSpawner):
    """Spawner that fails immediately"""

    def start(self):
        raise RuntimeError("I don't work!")


class SlowBadSpawner(MockSpawner):
    """Spawner that fails after a short delay"""

    async def start(self):
        await asyncio.sleep(0.5)
        raise RuntimeError("I don't work!")


class FormSpawner(MockSpawner):
    """A spawner that has an options form defined"""

    options_form = "IMAFORM"

    def options_from_form(self, form_data):
        options = {'notspecified': 5}
        if 'bounds' in form_data:
            options['bounds'] = [int(i) for i in form_data['bounds']]
        if 'energy' in form_data:
            options['energy'] = form_data['energy'][0]
        if 'hello_file' in form_data:
            options['hello'] = form_data['hello_file'][0]

        if 'illegal_argument' in form_data:
            raise ValueError("You are not allowed to specify 'illegal_argument'")
        return options


class FalsyCallableFormSpawner(FormSpawner):
    """A spawner that has a callable options form defined returning a falsy value"""

    options_form = lambda a, b: ""


class MockStructGroup:
    """Mock grp.struct_group"""

    def __init__(self, name, members, gid=1111):
        self.gr_name = name
        self.gr_mem = members
        self.gr_gid = gid


class MockStructPasswd:
    """Mock pwd.struct_passwd"""

    def __init__(self, name, gid=1111):
        self.pw_name = name
        self.pw_gid = gid


class MockPAMAuthenticator(PAMAuthenticator):
    auth_state = None
    # If true, return admin users marked as admin.
    return_admin = False

    @default('admin_users')
    def _admin_users_default(self):
        return {'admin'}

    def system_user_exists(self, user):
        # skip the add-system-user bit
        return not user.name.startswith('dne')

    async def authenticate(self, *args, **kwargs):
        with mock.patch.multiple(
            'pamela',
            authenticate=mock_authenticate,
            open_session=mock_open_session,
            close_session=mock_open_session,
            check_account=mock_check_account,
        ):
            username = await super().authenticate(*args, **kwargs)
        if username is None:
            return
        elif self.auth_state:
            return {'name': username, 'auth_state': self.auth_state}
        else:
            return username


class MockHub(JupyterHub):
    """Hub with various mock bits"""

    # disable some inherited traits with hardcoded values
    db_file = None
    last_activity_interval = 2
    log_datefmt = '%M:%S'

    @default('log_level')
    def _default_log_level(self):
        return 10

    # MockHub additional traits
    external_certs = Dict()

    def __init__(self, *args, **kwargs):
        if 'internal_certs_location' in kwargs:
            cert_location = kwargs['internal_certs_location']
            kwargs['external_certs'] = ssl_setup(cert_location, 'hub-ca')
        super().__init__(*args, **kwargs)
        if 'allow_all' not in self.config.Authenticator:
            self.config.Authenticator.allow_all = True

        if 'api_url' not in self.config.ConfigurableHTTPProxy:
            proxy_port = random_port()
            proxy_proto = "https" if self.internal_ssl else "http"
            self.config.ConfigurableHTTPProxy.api_url = (
                f"{proxy_proto}://127.0.0.1:{proxy_port}"
            )

    @default('subdomain_host')
    def _subdomain_host_default(self):
        return os.environ.get('JUPYTERHUB_TEST_SUBDOMAIN_HOST', '')

    @default('bind_url')
    def _default_bind_url(self):
        if self.subdomain_host:
            port = urlparse(self.subdomain_host).port
        else:
            port = random_port()
        return f'http://127.0.0.1:{port}/@/space%20word/'

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

    @default('hub_port')
    def _hub_port_default(self):
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

    def init_tornado_application(self):
        """Instantiate the tornado Application object"""
        super().init_tornado_application()
        # reconnect tornado_settings so that mocks can update the real thing
        self.tornado_settings = self.users.settings = self.tornado_application.settings

    def init_services(self):
        # explicitly expire services before reinitializing
        # this only happens in tests because re-initialize
        # does not occur in a real instance
        for service in self.db.query(orm.Service):
            self.db.expire(service)
        return super().init_services()

    test_clean_db = Bool(True)

    def init_db(self):
        """Ensure we start with a clean user & role list"""
        super().init_db()
        if self.test_clean_db:
            for user in self.db.query(orm.User):
                self.db.delete(user)
            for group in self.db.query(orm.Group):
                self.db.delete(group)
            for role in self.db.query(orm.Role):
                self.db.delete(role)
            self.db.commit()

        # count db requests
        self.db_query_count = 0
        engine = self.db.get_bind()

        @event.listens_for(engine, "before_execute")
        def before_execute(conn, clauseelement, multiparams, params, execution_options):
            self.db_query_count += 1

    def init_logging(self):
        super().init_logging()
        # enable log propagation for pytest capture
        self.log.propagate = True
        # clear unneeded handlers
        self.log.handlers.clear()

    async def initialize(self, argv=None):
        self.pid_file = NamedTemporaryFile(delete=False).name
        self.db_file = NamedTemporaryFile()
        self.db_url = os.getenv('JUPYTERHUB_TEST_DB_URL') or self.db_file.name
        if 'mysql' in self.db_url:
            self.db_kwargs['connect_args'] = {'auth_plugin': 'mysql_native_password'}
        await super().initialize([])

        # add an initial user
        user = self.db.query(orm.User).filter(orm.User.name == 'user').first()
        if user is None:
            user = orm.User(name='user')
            # avoid initial state inconsistency by setting initial activity
            user.last_activity = utcnow()
            self.db.add(user)
            self.db.commit()
            metrics.TOTAL_USERS.inc()
        roles.assign_default_roles(self.db, entity=user)
        self.db.commit()

    _stop_called = False

    def stop(self):
        if self._stop_called:
            return
        self._stop_called = True
        # run cleanup in a background thread
        # to avoid multiple eventloops in the same thread errors from asyncio

        def cleanup():
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.cleanup())
            loop.close()

        with ThreadPoolExecutor(1) as pool:
            f = pool.submit(cleanup)
            # wait for cleanup to finish
            f.result()

        # prevent redundant atexit from running
        self._atexit_ran = True
        super().stop()
        self.db_file.close()

    def _stop_event_loop(self):
        # leave it to pytest-asyncio to stop the loop
        pass

    async def login_user(self, name):
        """Login a user by name, returning her cookies."""
        base_url = public_url(self)
        s = AsyncSession()
        if self.internal_ssl:
            s.verify = self.external_certs['files']['ca']
        login_url = base_url + 'hub/login'
        r = await s.get(login_url)
        r.raise_for_status()
        xsrf = r.cookies['_xsrf']

        r = await s.post(
            url_concat(login_url, {"_xsrf": xsrf}),
            data={'username': name, 'password': name},
            allow_redirects=False,
        )
        r.raise_for_status()
        # make second request to get updated xsrf cookie
        r2 = await s.get(
            url_path_join(base_url, "hub/home"),
            allow_redirects=False,
        )
        assert r2.status_code == 200
        assert sorted(s.cookies.keys()) == [
            '_xsrf',
            'jupyterhub-hub-login',
            'jupyterhub-session-id',
        ]
        return s.cookies


class InstrumentedSpawner(MockSpawner):
    """
    Spawner that starts a full singleuser server

    instrumented with the JupyterHub test extension.
    """

    @default("default_url")
    def _default_url(self):
        """Use a default_url that any jupyter server will provide

        Should be:

        - authenticated, so we are testing auth
        - always available (i.e. in mocked ServerApp and NotebookApp)
        - *not* an API handler that raises 403 instead of redirecting
        """
        return "/tree"

    @default('cmd')
    def _cmd_default(self):
        return [sys.executable, '-m', 'jupyterhub.singleuser']

    def start(self):
        self.environment["JUPYTERHUB_SINGLEUSER_TEST_EXTENSION"] = "1"
        return super().start()
