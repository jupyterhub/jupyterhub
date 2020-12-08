"""py.test fixtures

Fixtures for jupyterhub components
----------------------------------
- `app`
- `auth_state_enabled`
- `db`
- `io_loop`
- single user servers
    - `cleanup_after`: allows cleanup of single user servers between tests
- mocked service
    - `MockServiceSpawner`
    - `mockservice`: mocked service with no external service url
    - `mockservice_url`: mocked service with a url to test external services

Fixtures to add functionality or spawning behavior
--------------------------------------------------
- `admin_access`
- `no_patience`
- `slow_spawn`
- `never_spawn`
- `bad_spawn`
- `slow_bad_spawn`

"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import inspect
import logging
import os
import sys
from getpass import getuser
from subprocess import TimeoutExpired
from unittest import mock

from pytest import fixture
from pytest import raises
from tornado import ioloop
from tornado.httpclient import HTTPError
from tornado.platform.asyncio import AsyncIOMainLoop

import jupyterhub.services.service
from . import mocking
from .. import crypto
from .. import orm
from ..utils import random_port
from .mocking import MockHub
from .test_services import mockservice_cmd
from .utils import add_user
from .utils import ssl_setup

# global db session object
_db = None


def pytest_collection_modifyitems(items):
    """This function is automatically run by pytest passing all collected test
    functions.

    We use it to add asyncio marker to all async tests and assert we don't use
    test functions that are async generators which wouldn't make sense.
    """
    for item in items:
        if inspect.iscoroutinefunction(item.obj):
            item.add_marker('asyncio')
        assert not inspect.isasyncgenfunction(item.obj)


@fixture(scope='module')
def ssl_tmpdir(tmpdir_factory):
    return tmpdir_factory.mktemp('ssl')


@fixture(scope='module')
def app(request, io_loop, ssl_tmpdir):
    """Mock a jupyterhub app for testing"""
    mocked_app = None
    ssl_enabled = getattr(
        request.module, 'ssl_enabled', os.environ.get('SSL_ENABLED', False)
    )
    kwargs = dict()
    if ssl_enabled:
        kwargs.update(dict(internal_ssl=True, internal_certs_location=str(ssl_tmpdir)))

    mocked_app = MockHub.instance(**kwargs)

    async def make_app():
        await mocked_app.initialize([])
        await mocked_app.start()

    def fin():
        # disconnect logging during cleanup because pytest closes captured FDs prematurely
        mocked_app.log.handlers = []
        MockHub.clear_instance()
        try:
            mocked_app.stop()
        except Exception as e:
            print("Error stopping Hub: %s" % e, file=sys.stderr)

    request.addfinalizer(fin)
    io_loop.run_sync(make_app)
    return mocked_app


@fixture
def auth_state_enabled(app):
    app.authenticator.auth_state = {'who': 'cares'}
    app.authenticator.enable_auth_state = True
    ck = crypto.CryptKeeper.instance()
    before_keys = ck.keys
    ck.keys = [os.urandom(32)]
    try:
        yield
    finally:
        ck.keys = before_keys
        app.authenticator.enable_auth_state = False
        app.authenticator.auth_state = None


@fixture
def db():
    """Get a db session"""
    global _db
    if _db is None:
        _db = orm.new_session_factory('sqlite:///:memory:')()
        user = orm.User(name=getuser())
        _db.add(user)
        _db.commit()
    return _db


@fixture(scope='module')
def event_loop(request):
    """Same as pytest-asyncio.event_loop, but re-scoped to module-level"""
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    return event_loop


@fixture(scope='module')
def io_loop(event_loop, request):
    """Same as pytest-tornado.io_loop, but re-scoped to module-level"""
    ioloop.IOLoop.configure(AsyncIOMainLoop)
    io_loop = AsyncIOMainLoop()
    io_loop.make_current()
    assert asyncio.get_event_loop() is event_loop
    assert io_loop.asyncio_loop is event_loop

    def _close():
        io_loop.clear_current()
        io_loop.close(all_fds=True)

    request.addfinalizer(_close)
    return io_loop


@fixture(autouse=True)
def cleanup_after(request, io_loop):
    """function-scoped fixture to shutdown user servers

    allows cleanup of servers between tests
    without having to launch a whole new app
    """
    try:
        yield
    finally:
        if not MockHub.initialized():
            return
        app = MockHub.instance()
        for uid, user in app.users.items():
            for name, spawner in list(user.spawners.items()):
                if spawner.active:
                    try:
                        io_loop.run_sync(lambda: app.proxy.delete_user(user, name))
                    except HTTPError:
                        pass
                    io_loop.run_sync(lambda: user.stop(name))
        app.db.commit()


_username_counter = 0


def new_username(prefix='testuser'):
    """Return a new unique username"""
    global _username_counter
    _username_counter += 1
    return '{}-{}'.format(prefix, _username_counter)


@fixture
def username():
    """allocate a temporary username

    unique each time the fixture is used
    """
    yield new_username()


@fixture
def user(app):
    """Fixture for creating a temporary user

    Each time the fixture is used, a new user is created
    """
    user = add_user(app.db, app, name=new_username())
    yield user


@fixture
def admin_user(app, username):
    """Fixture for creating a temporary admin user"""
    user = add_user(app.db, app, name=new_username('testadmin'), admin=True)
    yield user


class MockServiceSpawner(jupyterhub.services.service._ServiceSpawner):
    """mock services for testing.

    Shorter intervals, etc.
    """

    poll_interval = 1


_mock_service_counter = 0


def _mockservice(request, app, url=False):
    global _mock_service_counter
    _mock_service_counter += 1
    name = 'mock-service-%i' % _mock_service_counter
    spec = {'name': name, 'command': mockservice_cmd, 'admin': True}
    if url:
        if app.internal_ssl:
            spec['url'] = 'https://127.0.0.1:%i' % random_port()
        else:
            spec['url'] = 'http://127.0.0.1:%i' % random_port()

    io_loop = app.io_loop

    with mock.patch.object(
        jupyterhub.services.service, '_ServiceSpawner', MockServiceSpawner
    ):
        app.services = [spec]
        app.init_services()
        assert name in app._service_map
        service = app._service_map[name]

        async def start():
            # wait for proxy to be updated before starting the service
            await app.proxy.add_all_services(app._service_map)
            service.start()

        io_loop.run_sync(start)

        def cleanup():
            asyncio.get_event_loop().run_until_complete(service.stop())
            app.services[:] = []
            app._service_map.clear()

        request.addfinalizer(cleanup)
        # ensure process finishes starting
        with raises(TimeoutExpired):
            service.proc.wait(1)
        if url:
            io_loop.run_sync(service.server.wait_up)
    return service


@fixture
def mockservice(request, app):
    """Mock a service with no external service url"""
    yield _mockservice(request, app, url=False)


@fixture
def mockservice_url(request, app):
    """Mock a service with its own url to test external services"""
    yield _mockservice(request, app, url=True)


@fixture
def admin_access(app):
    """Grant admin-access with this fixture"""
    with mock.patch.dict(app.tornado_settings, {'admin_access': True}):
        yield


@fixture
def no_patience(app):
    """Set slow-spawning timeouts to zero"""
    with mock.patch.dict(
        app.tornado_settings, {'slow_spawn_timeout': 0.1, 'slow_stop_timeout': 0.1}
    ):
        yield


@fixture
def slow_spawn(app):
    """Fixture enabling SlowSpawner"""
    with mock.patch.dict(app.tornado_settings, {'spawner_class': mocking.SlowSpawner}):
        yield


@fixture
def never_spawn(app):
    """Fixture enabling NeverSpawner"""
    with mock.patch.dict(app.tornado_settings, {'spawner_class': mocking.NeverSpawner}):
        yield


@fixture
def bad_spawn(app):
    """Fixture enabling BadSpawner"""
    with mock.patch.dict(app.tornado_settings, {'spawner_class': mocking.BadSpawner}):
        yield


@fixture
def slow_bad_spawn(app):
    """Fixture enabling SlowBadSpawner"""
    with mock.patch.dict(
        app.tornado_settings, {'spawner_class': mocking.SlowBadSpawner}
    ):
        yield
