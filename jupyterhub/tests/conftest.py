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
import copy
import os
import sys
from subprocess import TimeoutExpired
from unittest import mock
from warnings import warn

import pytest_asyncio
from packaging.version import parse as parse_version
from pytest import fixture, mark, raises
from sqlalchemy import event
from tornado.httpclient import HTTPError
from tornado.platform.asyncio import AsyncIOMainLoop

import jupyterhub.services.service

from .. import crypto, orm, scopes
from ..roles import (
    assign_default_roles,
    create_role,
    get_default_roles,
    mock_roles,
    update_roles,
)
from ..utils import random_port
from . import mocking
from .mocking import MockHub
from .test_services import mockservice_cmd
from .utils import add_user

# global db session object
_db = None

_pytest_asyncio_24 = parse_version(pytest_asyncio.__version__) >= parse_version(
    "0.24.0.dev0"
)


def pytest_collection_modifyitems(items):
    if _pytest_asyncio_24:
        # apply loop_scope="module" to all async tests by default
        # this is only for pytest_asyncio >= 0.24
        # pytest_asyncio < 0.24 uses overridden `event_loop` fixture
        # this can be hopefully be removed in favor of config if
        # https://github.com/pytest-dev/pytest-asyncio/issues/793
        # is addressed
        pytest_asyncio_tests = (
            item for item in items if pytest_asyncio.is_async_test(item)
        )
        asyncio_scope_marker = mark.asyncio(loop_scope="module")
        for async_test in pytest_asyncio_tests:
            # add asyncio marker _if_ not already present
            asyncio_marker = async_test.get_closest_marker('asyncio')
            if not asyncio_marker or not asyncio_marker.kwargs:
                async_test.add_marker(asyncio_scope_marker, append=False)


if not _pytest_asyncio_24:
    # pre-pytest-asyncio 0.24, overriding event_loop fixture
    # was the way to change scope of event_loop
    # post-0.24 uses modifyitems above
    @fixture(scope='module')
    def event_loop(request):
        """Same as pytest-asyncio.event_loop, but re-scoped to module-level"""
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        return event_loop


@fixture(scope='module')
def ssl_tmpdir(tmpdir_factory):
    return tmpdir_factory.mktemp('ssl')


@fixture(scope='module')
async def app(request, ssl_tmpdir):
    """Mock a jupyterhub app for testing"""
    mocked_app = None
    ssl_enabled = getattr(
        request.module, 'ssl_enabled', os.environ.get('SSL_ENABLED', False)
    )
    kwargs = dict()
    if ssl_enabled:
        kwargs.update(dict(internal_ssl=True, internal_certs_location=str(ssl_tmpdir)))

    mocked_app = MockHub.instance(**kwargs)

    def fin():
        # disconnect logging during cleanup because pytest closes captured FDs prematurely
        mocked_app.log.handlers = []
        MockHub.clear_instance()
        try:
            mocked_app.stop()
        except Exception as e:
            print(f"Error stopping Hub: {e}", file=sys.stderr)

    request.addfinalizer(fin)
    await mocked_app.initialize([])
    await mocked_app.start()
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
    # make sure some initial db contents are filled out
    # specifically, the 'default' jupyterhub oauth client
    app = MockHub(db_url='sqlite:///:memory:')
    app.init_db()
    _db = app.db
    for role in get_default_roles():
        create_role(_db, role)
    user = orm.User(name="user")
    _db.add(user)
    _db.commit()
    assign_default_roles(_db, user)
    _db.commit()
    return _db


@fixture(scope='module')
async def io_loop(request):
    """Mostly obsolete fixture for tornado event loop

    Main purpose is to register cleanup (close) after we're done with the loop.
    The main reason to depend on this fixture is to ensure your cleanup
    happens before the io_loop is closed.
    """
    warn(
        "jupyterhub's io_loop fixture is deprecated. Use async fixtures to get the event loop.",
        DeprecationWarning,
    )
    io_loop = AsyncIOMainLoop()
    event_loop = asyncio.get_running_loop()
    assert asyncio.get_event_loop() is event_loop
    assert io_loop.asyncio_loop is event_loop
    return io_loop


@fixture(autouse=True)
async def cleanup_after(request):
    """function-scoped fixture to shutdown user servers

    allows cleanup of servers between tests
    without having to launch a whole new app
    """

    try:
        yield
    finally:
        if _db is not None:
            # cleanup after failed transactions
            _db.rollback()

        if not MockHub.initialized():
            return
        app = MockHub.instance()
        if app.db_file.closed:
            return

        # cleanup users
        for orm_user in app.db.query(orm.User):
            user = app.users[orm_user]
            for name, spawner in list(user.spawners.items()):
                if spawner.active:
                    try:
                        await app.proxy.delete_user(user, name)
                    except HTTPError:
                        pass
                    print(f"Stopping leftover server {spawner._log_name}")
                    await user.stop(name)
            if user.name not in {'admin', 'user'}:
                app.log.debug(f"Deleting test user {user.name}")
                app.users.delete(user.id)
        # delete groups
        for group in app.db.query(orm.Group):
            app.log.debug(f"Deleting test group {group.name}")
            app.db.delete(group)
        # delete shares
        for share in app.db.query(orm.Share):
            app.log.debug(f"Deleting test share {share}")
            app.db.delete(share)

        # clear services
        for name, service in app._service_map.items():
            if service.managed:
                service.stop()
        for orm_service in app.db.query(orm.Service):
            if orm_service.oauth_client:
                app.oauth_provider.remove_client(orm_service.oauth_client_id)
            app.db.delete(orm_service)
        app._service_map.clear()
        app.db.commit()


_username_counter = 0


def new_username(prefix='testuser'):
    """Return a new unique username"""
    global _username_counter
    _username_counter += 1
    return f'{prefix}-{_username_counter}'


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


_groupname_counter = 0
_rolename_counter = 0


def new_group_name(prefix='testgroup'):
    """Return a new unique group name"""
    global _groupname_counter
    _groupname_counter += 1
    return f'{prefix}-{_groupname_counter}'


def new_role_name(prefix='testrole'):
    """Return a new unique role name"""
    global _rolename_counter
    _rolename_counter += 1
    return f'{prefix}-{_rolename_counter}'


@fixture
def groupname():
    """allocate a temporary group name

    unique each time the fixture is used
    """
    yield new_group_name()


@fixture
def group(app):
    """Fixture for creating a temporary group

    Each time the fixture is used, a new group is created

    The group is deleted after the test
    """
    group = orm.Group(name=new_group_name())
    app.db.add(group)
    app.db.commit()
    yield group


@fixture
def role(app):
    """Fixture for creating a temporary role

    Each time the fixture is used, a new role is created

    The role is deleted after the test
    """
    role = orm.Role(name=new_role_name())
    app.db.add(role)
    app.db.commit()
    yield role
    app.db.delete(role)
    app.db.commit()


class MockServiceSpawner(jupyterhub.services.service._ServiceSpawner):
    """mock services for testing.

    Shorter intervals, etc.
    """

    poll_interval = 1


async def _mockservice(request, app, name, external=False, url=False):
    """
    Add a service to the application

    Args:
        request: pytest request fixture
        app: MockHub application
        external (bool):
          If False (default), launch the service.
          Otherwise, consider it 'external,
          registering a service in the database,
          but don't start it.
        url (bool):
          If True, register the service at a URL
          (as opposed to headless, API-only).
    """
    spec = {'name': name, 'command': mockservice_cmd, 'admin': True}
    port = random_port()
    if url:
        if app.internal_ssl:
            spec['url'] = f'https://127.0.0.1:{port}'
        else:
            spec['url'] = f'http://127.0.0.1:{port}'

    if external:
        spec['oauth_redirect_uri'] = f'http://127.0.0.1:{port}'

    event_loop = asyncio.get_running_loop()

    with mock.patch.object(
        jupyterhub.services.service, '_ServiceSpawner', MockServiceSpawner
    ):
        app.services = [spec]
        app.init_services()
        mock_roles(app, name, 'services')
        assert name in app._service_map
        service = app._service_map[name]
        token = service.orm.api_tokens[0]

        async def start():
            # wait for proxy to be updated before starting the service
            await app.proxy.add_all_services(app._service_map)
            await service.start()

        if not external:
            await start()

        def cleanup():
            if not external:
                event_loop.run_until_complete(service.stop())
            app.services[:] = []
            app._service_map.clear()

        request.addfinalizer(cleanup)
        # ensure process finishes starting
        if not external:
            with raises(TimeoutExpired):
                service.proc.wait(1)
        if url:
            await service.server.wait_up(http=True)
    return service


_service_name_counter = 0


@fixture
def service_name():
    global _service_name_counter
    _service_name_counter += 1
    name = f'test-service-{_service_name_counter}'
    return name


@fixture
async def mockservice(request, app, service_name):
    """Mock a service with no external service url"""
    yield await _mockservice(request, app, name=service_name, url=False)


@fixture
async def mockservice_external(request, app, service_name):
    """Mock an externally managed service (don't start anything)"""
    yield await _mockservice(request, app, name=service_name, external=True, url=False)


@fixture
async def mockservice_url(request, app, service_name):
    """Mock a service with its own url to test external services"""
    yield await _mockservice(request, app, name=service_name, url=True)


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
def full_spawn(app):
    """Fixture enabling full instrumented server via InstrumentedSpawner"""
    with mock.patch.dict(
        app.tornado_settings, {'spawner_class': mocking.InstrumentedSpawner}
    ):
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


@fixture
def create_temp_role(app):
    """Generate a temporary role with certain scopes.
    Convenience function that provides setup, database handling and teardown"""
    temp_roles = []
    index = [1]

    def temp_role_creator(scopes, role_name=None):
        if not role_name:
            role_name = f'temp_role_{index[0]}'
            index[0] += 1
        temp_role = orm.Role(name=role_name, scopes=list(scopes))
        temp_roles.append(temp_role)
        app.db.add(temp_role)
        app.db.commit()
        return temp_role

    yield temp_role_creator
    for role in temp_roles:
        app.db.delete(role)
    app.db.commit()


@fixture
def create_user_with_scopes(app, create_temp_role):
    """Generate a temporary user with specific scopes.
    Convenience function that provides setup, database handling and teardown"""
    temp_users = []
    counter = 0
    get_role = create_temp_role

    def temp_user_creator(*scopes, name=None):
        nonlocal counter
        if name is None:
            counter += 1
            name = f"temp_user_{counter}"
        role = get_role(scopes)
        orm_user = orm.User(name=name)
        app.db.add(orm_user)
        app.db.commit()
        temp_users.append(orm_user)
        update_roles(app.db, orm_user, roles=[role.name])
        return app.users[orm_user.id]

    yield temp_user_creator


@fixture
def create_service_with_scopes(app, create_temp_role):
    """Generate a temporary service with specific scopes.
    Convenience function that provides setup, database handling and teardown"""
    temp_service = []
    counter = 0
    role_function = create_temp_role

    def temp_service_creator(*scopes, name=None):
        nonlocal counter
        if name is None:
            counter += 1
            name = f"temp_service_{counter}"
        role = role_function(scopes)
        app.services.append({'name': name})
        app.init_services()
        orm_service = orm.Service.find(app.db, name)
        app.db.commit()
        update_roles(app.db, orm_service, roles=[role.name])
        return orm_service

    yield temp_service_creator
    for service in temp_service:
        app.db.delete(service)
    app.db.commit()


@fixture
def preserve_scopes():
    """Revert any custom scopes after test"""
    scope_definitions = copy.deepcopy(scopes.scope_definitions)
    yield scope_definitions
    scopes.scope_definitions = scope_definitions


# collect db query counts and report the top N tests by db query count
@fixture(autouse=True)
def count_db_executions(request, record_property):
    if 'app' in request.fixturenames:
        app = request.getfixturevalue("app")
        initial_count = app.db_query_count
        yield
        # populate property, collected later in pytest_terminal_summary
        record_property("db_executions", app.db_query_count - initial_count)
    elif 'db' in request.fixturenames:
        # some use the 'db' fixture directly for one-off database tests
        count = 0
        engine = request.getfixturevalue("db").get_bind()

        @event.listens_for(engine, "before_execute")
        def before_execute(conn, clauseelement, multiparams, params, execution_options):
            nonlocal count
            count += 1

        yield
        record_property("db_executions", count)
    else:
        # nothing to do, still have to yield
        yield


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # collect db_executions property
    # populated by the count_db_executions fixture
    db_counts = {}
    for report in terminalreporter.getreports(""):
        properties = dict(report.user_properties)
        db_executions = properties.get("db_executions", 0)
        if db_executions:
            db_counts[report.nodeid] = db_executions

    total_queries = sum(db_counts.values())
    if total_queries == 0:
        # nothing to report (e.g. test subset)
        return
    n = min(10, len(db_counts))
    terminalreporter.section(f"top {n} database queries")
    terminalreporter.line(f"{total_queries:<6} (total)")
    for nodeid in sorted(db_counts, key=db_counts.get, reverse=True)[:n]:
        queries = db_counts[nodeid]
        if queries:
            terminalreporter.line(f"{queries:<6} {nodeid}")


@fixture
def service_data(service_name):
    """Data used to create service at runtime"""
    return {
        "name": service_name,
        "oauth_client_id": f"service-{service_name}",
        "api_token": f"api_token-{service_name}",
        "oauth_redirect_uri": "http://127.0.0.1:5555/oauth_callback-from-api",
        "oauth_no_confirm": True,
        "oauth_client_allowed_scopes": ["inherit"],
        "info": {'foo': 'bar'},
    }
