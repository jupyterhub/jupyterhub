"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import logging
from itertools import chain
from unittest import mock
from urllib.parse import urlparse

import pytest
from requests import HTTPError
from traitlets import Any, Tuple
from traitlets.config import Config

from jupyterhub import auth, crypto, orm

from .mocking import MockHub, MockPAMAuthenticator, MockStructGroup, MockStructPasswd
from .utils import add_user, async_requests, get_page, public_url


async def test_pam_auth():
    authenticator = MockPAMAuthenticator(allow_all=True)
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'match', 'password': 'match'}
    )
    assert authorized['name'] == 'match'

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'match', 'password': 'nomatch'}
    )
    assert authorized is None

    # Account check is on by default for increased security
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'notallowedmatch', 'password': 'notallowedmatch'}
    )
    assert authorized is None


async def test_pam_auth_account_check_disabled():
    authenticator = MockPAMAuthenticator(allow_all=True, check_account=False)
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'allowedmatch', 'password': 'allowedmatch'}
    )
    assert authorized['name'] == 'allowedmatch'

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'notallowedmatch', 'password': 'notallowedmatch'}
    )
    assert authorized['name'] == 'notallowedmatch'


async def test_pam_auth_admin_groups():
    jh_users = MockStructGroup(
        'jh_users',
        ['group_admin', 'also_group_admin', 'override_admin', 'non_admin'],
        1234,
    )
    jh_admins = MockStructGroup('jh_admins', ['group_admin'], 5678)
    wheel = MockStructGroup('wheel', ['also_group_admin'], 9999)
    system_groups = [jh_users, jh_admins, wheel]

    group_admin = MockStructPasswd('group_admin', 1234)
    also_group_admin = MockStructPasswd('also_group_admin', 1234)
    override_admin = MockStructPasswd('override_admin', 1234)
    non_admin = MockStructPasswd('non_admin', 1234)
    system_users = [group_admin, also_group_admin, override_admin, non_admin]

    user_group_map = {
        'group_admin': [jh_users.gr_gid, jh_admins.gr_gid],
        'also_group_admin': [jh_users.gr_gid, wheel.gr_gid],
        'override_admin': [jh_users.gr_gid],
        'non_admin': [jh_users.gr_gid],
    }

    def getgrnam(name):
        return [x for x in system_groups if x.gr_name == name][0]

    def getpwnam(name):
        return [x for x in system_users if x.pw_name == name][0]

    def getgrouplist(name, group):
        return user_group_map[name]

    authenticator = MockPAMAuthenticator(
        admin_groups={'jh_admins', 'wheel'},
        admin_users={'override_admin'},
        allow_all=True,
    )

    # Check admin_group applies as expected
    with mock.patch.multiple(
        authenticator,
        _getgrnam=getgrnam,
        _getpwnam=getpwnam,
        _getgrouplist=getgrouplist,
    ):
        authorized = await authenticator.get_authenticated_user(
            None, {'username': 'group_admin', 'password': 'group_admin'}
        )
    assert authorized['name'] == 'group_admin'
    assert authorized['admin'] is True

    # Check multiple groups work, just in case.
    with mock.patch.multiple(
        authenticator,
        _getgrnam=getgrnam,
        _getpwnam=getpwnam,
        _getgrouplist=getgrouplist,
    ):
        authorized = await authenticator.get_authenticated_user(
            None,
            {'username': 'also_group_admin', 'password': 'also_group_admin'},
        )
    assert authorized['name'] == 'also_group_admin'
    assert authorized['admin'] is True

    # Check admin_users still applies correctly
    with mock.patch.multiple(
        authenticator,
        _getgrnam=getgrnam,
        _getpwnam=getpwnam,
        _getgrouplist=getgrouplist,
    ):
        authorized = await authenticator.get_authenticated_user(
            None,
            {'username': 'override_admin', 'password': 'override_admin'},
        )
    assert authorized['name'] == 'override_admin'
    assert authorized['admin'] is True

    # Check it doesn't admin everyone
    with mock.patch.multiple(
        authenticator,
        _getgrnam=getgrnam,
        _getpwnam=getpwnam,
        _getgrouplist=getgrouplist,
    ):
        authorized = await authenticator.get_authenticated_user(
            None, {'username': 'non_admin', 'password': 'non_admin'}
        )
    assert authorized['name'] == 'non_admin'
    assert authorized['admin'] is False


async def test_pam_auth_allowed():
    authenticator = MockPAMAuthenticator(
        allowed_users={'wash', 'kaylee'}, allow_all=False
    )

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'kaylee', 'password': 'kaylee'}
    )
    assert authorized['name'] == 'kaylee'

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'wash', 'password': 'nomatch'}
    )
    assert authorized is None

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'mal', 'password': 'mal'}
    )
    assert authorized is None


async def test_pam_auth_allowed_groups():
    class TestAuthenticator(MockPAMAuthenticator):
        @staticmethod
        def _getpwnam(name):
            return MockStructPasswd(name=name)

        @staticmethod
        def _getgrnam(name):
            if name == "group":
                return MockStructGroup('grp', ['kaylee'], gid=1234)
            else:
                return None

        @staticmethod
        def _getgrouplist(username, gid):
            gids = [gid]
            if username == "kaylee":
                gids.append(1234)
            return gids

    authenticator = TestAuthenticator(allowed_groups={'group'}, allow_all=False)

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'kaylee', 'password': 'kaylee'}
    )
    assert authorized['name'] == 'kaylee'

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'mal', 'password': 'mal'}
    )
    assert authorized is None


async def test_pam_auth_blocked():
    # Null case compared to next case
    authenticator = MockPAMAuthenticator(allow_all=True)
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'wash', 'password': 'wash'}
    )
    assert authorized['name'] == 'wash'

    # Blocklist basics
    authenticator = MockPAMAuthenticator(blocked_users={'wash'}, allow_all=True)
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'wash', 'password': 'wash'}
    )
    assert authorized is None

    # User in both allowed and blocked: default deny.  Make error someday?
    authenticator = MockPAMAuthenticator(
        blocked_users={'wash'},
        allowed_users={'wash', 'kaylee'},
        allow_all=True,
    )
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'wash', 'password': 'wash'}
    )
    assert authorized is None

    # User not in blocked set can log in
    authenticator = MockPAMAuthenticator(
        blocked_users={'wash'},
        allowed_users={'wash', 'kaylee'},
    )
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'kaylee', 'password': 'kaylee'}
    )
    assert authorized['name'] == 'kaylee'

    # User in allowed, blocked irrelevent
    authenticator = MockPAMAuthenticator(
        blocked_users={'mal'}, allowed_users={'wash', 'kaylee'}
    )
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'wash', 'password': 'wash'}
    )
    assert authorized['name'] == 'wash'

    # User in neither list
    authenticator = MockPAMAuthenticator(
        blocked_users={'mal'},
        allowed_users={'wash', 'kaylee'},
    )
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'simon', 'password': 'simon'}
    )
    assert authorized is None

    authenticator = MockPAMAuthenticator(
        blocked_users=set(), allowed_users={'wash', 'kaylee'}
    )
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'kaylee', 'password': 'kaylee'}
    )
    assert authorized['name'] == 'kaylee'


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
async def test_deprecated_signatures():
    def deprecated_xlist(self, username):
        return True

    with mock.patch.multiple(
        MockPAMAuthenticator,
        check_whitelist=deprecated_xlist,
        check_group_whitelist=deprecated_xlist,
        check_blacklist=deprecated_xlist,
    ):
        deprecated_authenticator = MockPAMAuthenticator()
        authorized = await deprecated_authenticator.get_authenticated_user(
            None, {'username': 'test', 'password': 'test'}
        )

        assert authorized is not None


async def test_pam_auth_no_such_group():
    authenticator = MockPAMAuthenticator(
        allowed_groups={'nosuchcrazygroup'},
    )
    authenticator._getpwnam = MockStructPasswd
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'kaylee', 'password': 'kaylee'}
    )
    assert authorized is None


async def test_wont_add_system_user():
    user = orm.User(name='lioness4321')
    authenticator = auth.PAMAuthenticator(allowed_users={'mal'})
    authenticator.create_system_users = False
    with pytest.raises(KeyError):
        await authenticator.add_user(user)


async def test_cant_add_system_user():
    user = orm.User(name='lioness4321')
    authenticator = auth.PAMAuthenticator(allowed_users={'mal'})
    authenticator.add_user_cmd = ['jupyterhub-fake-command']
    authenticator.create_system_users = True

    class DummyFile:
        def read(self):
            return b'dummy error'

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.returncode = 1
            self.stdout = DummyFile()

        def wait(self):
            return

    with mock.patch.object(auth, 'Popen', DummyPopen):
        with pytest.raises(RuntimeError) as exc:
            await authenticator.add_user(user)
        assert str(exc.value) == 'Failed to create system user lioness4321: dummy error'


async def test_add_system_user():
    user = orm.User(name='lioness4321')
    authenticator = auth.PAMAuthenticator(allowed_users={'mal'})
    authenticator.create_system_users = True
    authenticator.add_user_cmd = ['echo', '/home/USERNAME']

    record = {}

    class DummyPopen:
        def __init__(self, cmd, *args, **kwargs):
            record['cmd'] = cmd
            self.returncode = 0

        def wait(self):
            return

    with mock.patch.object(auth, 'Popen', DummyPopen):
        await authenticator.add_user(user)
    assert record['cmd'] == ['echo', '/home/lioness4321', 'lioness4321']


async def test_delete_user():
    user = orm.User(name='zoe')
    a = MockPAMAuthenticator(allowed_users={'mal'})

    assert 'zoe' not in a.allowed_users
    await a.add_user(user)
    assert 'zoe' in a.allowed_users
    a.delete_user(user)
    assert 'zoe' not in a.allowed_users


def test_urls():
    a = auth.PAMAuthenticator()
    logout = a.logout_url('/base/url/')
    login = a.login_url('/base/url')
    assert logout == '/base/url/logout'
    assert login == '/base/url/login'


def test_handlers(app):
    a = auth.PAMAuthenticator()
    handlers = a.get_handlers(app)
    assert handlers[0][0] == '/login'


async def test_auth_state(app, auth_state_enabled):
    """auth_state enabled and available"""
    name = 'kiwi'
    user = add_user(app.db, app, name=name)
    assert user.encrypted_auth_state is None
    cookies = await app.login_user(name)
    auth_state = await user.get_auth_state()
    assert auth_state == app.authenticator.auth_state


async def test_auth_admin_non_admin(app):
    """admin should be passed through for non-admin users"""
    name = 'kiwi'
    user = add_user(app.db, app, name=name, admin=False)
    assert user.admin is False
    cookies = await app.login_user(name)
    assert user.admin is False


async def test_auth_admin_is_admin(app):
    """admin should be passed through for admin users"""
    # Admin user defined in MockPAMAuthenticator.
    name = 'admin'
    user = add_user(app.db, app, name=name, admin=False)
    assert user.admin is False
    cookies = await app.login_user(name)
    assert user.admin is True


async def test_auth_admin_retained_if_unset(app):
    """admin should be unchanged if authenticator doesn't return admin value"""
    name = 'kiwi'
    # Add user as admin.
    user = add_user(app.db, app, name=name, admin=True)
    assert user.admin is True
    # User should remain unchanged.
    cookies = await app.login_user(name)
    assert user.admin is True


@pytest.fixture
def auth_state_unavailable(auth_state_enabled):
    """auth_state enabled at the Authenticator level,

    but unavailable due to no crypto keys.
    """
    crypto.CryptKeeper.instance().keys = []
    yield


async def test_auth_state_disabled(app, auth_state_unavailable):
    name = 'driebus'
    user = add_user(app.db, app, name=name)
    assert user.encrypted_auth_state is None
    with pytest.raises(HTTPError):
        cookies = await app.login_user(name)
    auth_state = await user.get_auth_state()
    assert auth_state is None


async def test_normalize_names():
    a = MockPAMAuthenticator(allow_all=True)
    authorized = await a.get_authenticated_user(
        None, {'username': 'ZOE', 'password': 'ZOE'}
    )
    assert authorized['name'] == 'zoe'

    authorized = await a.get_authenticated_user(
        None, {'username': 'Glenn', 'password': 'Glenn'}
    )
    assert authorized['name'] == 'glenn'

    authorized = await a.get_authenticated_user(
        None, {'username': 'hExi', 'password': 'hExi'}
    )
    assert authorized['name'] == 'hexi'

    authorized = await a.get_authenticated_user(
        None, {'username': 'Test', 'password': 'Test'}
    )
    assert authorized['name'] == 'test'


async def test_username_map():
    a = MockPAMAuthenticator(username_map={'wash': 'alpha'}, allow_all=True)
    authorized = await a.get_authenticated_user(
        None, {'username': 'WASH', 'password': 'WASH'}
    )

    assert authorized['name'] == 'alpha'

    authorized = await a.get_authenticated_user(
        None, {'username': 'Inara', 'password': 'Inara'}
    )
    assert authorized['name'] == 'inara'


def test_validate_names():
    a = auth.PAMAuthenticator()
    assert a.validate_username('willow')
    assert a.validate_username('giles')
    assert a.validate_username('Test')
    assert a.validate_username('hExi')
    assert a.validate_username('Glenn#Smith!')
    a = auth.PAMAuthenticator(username_pattern='w.*')
    assert not a.validate_username('xander')
    assert a.validate_username('willow')


async def test_post_auth_hook():
    def test_auth_hook(authenticator, handler, authentication):
        authentication['testkey'] = 'testvalue'
        return authentication

    a = MockPAMAuthenticator(allow_all=True, post_auth_hook=test_auth_hook)

    authorized = await a.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'test_user'}
    )

    assert authorized['testkey'] == 'testvalue'


class MyAuthenticator(auth.Authenticator):
    def check_whitelist(self, username, authentication=None):
        return username == "subclass-allowed"


def test_deprecated_config(caplog):
    cfg = Config()
    cfg.Authenticator.whitelist = {'user'}
    log = logging.getLogger("testlog")
    authenticator = auth.Authenticator(config=cfg, log=log)
    assert caplog.record_tuples == [
        (
            log.name,
            logging.WARNING,
            'Authenticator.whitelist is deprecated in JupyterHub 1.2, use '
            'Authenticator.allowed_users instead',
        )
    ]
    assert authenticator.allowed_users == {'user'}


def test_deprecated_methods():
    cfg = Config()
    cfg.Authenticator.whitelist = {'user'}
    authenticator = auth.Authenticator(config=cfg)

    assert authenticator.check_allowed("user")
    with pytest.deprecated_call():
        assert authenticator.check_whitelist("user")
    assert not authenticator.check_allowed("otheruser")
    with pytest.deprecated_call():
        assert not authenticator.check_whitelist("otheruser")


def test_deprecated_config_subclass():
    cfg = Config()
    cfg.MyAuthenticator.whitelist = {'user'}
    with pytest.deprecated_call():
        authenticator = MyAuthenticator(config=cfg)
    assert authenticator.allowed_users == {'user'}


def test_deprecated_methods_subclass():
    with pytest.deprecated_call():
        authenticator = MyAuthenticator()

    assert authenticator.check_allowed("subclass-allowed")
    assert authenticator.check_whitelist("subclass-allowed")
    assert not authenticator.check_allowed("otheruser")
    assert not authenticator.check_whitelist("otheruser")


async def test_nullauthenticator(app):
    with mock.patch.dict(
        app.tornado_settings, {"authenticator": auth.NullAuthenticator(parent=app)}
    ):
        r = await async_requests.get(public_url(app))
    assert urlparse(r.url).path.endswith("/hub/login")
    assert r.status_code == 403


class MockGroupsAuthenticator(auth.Authenticator):
    authenticated_groups = Any()
    refresh_groups = Any()

    manage_groups = True

    def authenticate(self, handler, data):
        return {
            "name": data["username"],
            "groups": self.authenticated_groups,
        }

    async def refresh_user(self, user, handler):
        return {
            "name": user.name,
            "groups": self.refresh_groups,
        }


@pytest.mark.parametrize(
    "authenticated_groups, refresh_groups",
    [
        (None, None),
        (["auth1"], None),
        (None, ["auth1"]),
        (["auth1"], ["auth1", "auth2"]),
        (["auth1", "auth2"], ["auth1"]),
        (["auth1", "auth2"], ["auth3"]),
        (["auth1", "auth2"], ["auth3"]),
    ],
)
async def test_auth_managed_groups(
    app, user, group, authenticated_groups, refresh_groups
):
    authenticator = MockGroupsAuthenticator(
        parent=app,
        authenticated_groups=authenticated_groups,
        refresh_groups=refresh_groups,
        allow_all=True,
    )

    user.groups.append(group)
    app.db.commit()
    before_groups = [group.name]
    if authenticated_groups is None:
        expected_authenticated_groups = before_groups
    else:
        expected_authenticated_groups = authenticated_groups
    if refresh_groups is None:
        expected_refresh_groups = expected_authenticated_groups
    else:
        expected_refresh_groups = refresh_groups

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        cookies = await app.login_user(user.name)
        assert not app.db.dirty
        groups = sorted(g.name for g in user.groups)
        assert groups == expected_authenticated_groups

        # force refresh_user on next request
        user._auth_refreshed -= 10 + app.authenticator.auth_refresh_age
        r = await get_page('home', app, cookies=cookies, allow_redirects=False)
        assert r.status_code == 200
        assert not app.db.dirty
        groups = sorted(g.name for g in user.groups)
        assert groups == expected_refresh_groups


class MockRolesAuthenticator(auth.Authenticator):
    authenticated_roles = Any()
    refresh_roles = Any()
    initial_roles = Any()
    manage_roles = True

    def authenticate(self, handler, data):
        return {
            "name": data["username"],
            "roles": self.authenticated_roles,
        }

    async def refresh_user(self, user, handler):
        return {
            "name": user.name,
            "roles": self.refresh_roles,
        }

    async def load_managed_roles(self):
        return self.initial_roles


def role_to_dict(role):
    return {col: getattr(role, col) for col in role.__table__.columns.keys()}


@pytest.mark.parametrize(
    "initial_roles",
    [
        pytest.param(
            [{'name': 'test-role'}],
            id="should have the same effect as `load_roles` when creating a new role",
        ),
        pytest.param(
            [
                {
                    'name': 'server',
                    'users': ['test-user'],
                }
            ],
            id="should have the same effect as `load_roles` when assigning a role to a user",
        ),
        pytest.param(
            [
                {
                    'name': 'server',
                    'groups': ['test-group'],
                }
            ],
            id="should have the same effect as `load_roles` when assigning a role to a group",
        ),
    ],
)
async def test_auth_load_managed_roles(app, initial_roles):
    authenticator = MockRolesAuthenticator(
        parent=app,
        initial_roles=initial_roles,
    )

    # create the roles using `load_roles`
    hub = MockHub(load_roles=initial_roles)
    hub.init_db()
    await hub.init_role_creation()
    expected_roles = [role_to_dict(role) for role in hub.db.query(orm.Role)]

    # create the roles using authenticator's `load_managed_roles`
    hub = MockHub(load_roles=[], authenticator=authenticator)
    hub.init_db()
    await hub.init_role_creation()
    actual_roles = [role_to_dict(role) for role in hub.db.query(orm.Role)]

    # remove `managed_by_auth` from comparison as this is expected to differ
    for role in [*actual_roles, *expected_roles]:
        role.pop('managed_by_auth')

    # `load_managed_roles` should produce the same set of roles as `load_roles` does
    assert expected_roles == actual_roles


async def test_auth_load_managed_roles_handles_new_user(app):
    authenticator = MockRolesAuthenticator(
        parent=app,
        initial_roles=[
            {
                'name': 'new-role',
                'users': ['this-user-does-not-exist'],
            }
        ],
    )

    # create the roles using authenticator's `load_managed_roles`
    hub = MockHub(load_roles=[], authenticator=authenticator)
    hub.init_db()
    await hub.init_role_creation()
    roles = {role.name: role_to_dict(role) for role in hub.db.query(orm.Role)}

    assert roles['new-role']


@pytest.mark.parametrize(
    "roles_after_restart",
    [
        pytest.param(
            [{'name': 'role-a', 'scopes': ['admin:servers'], 'users': ['test-user']}],
            id="preserve role assignment if explicitly defined in `load_managed_roles()`",
        ),
        pytest.param(
            [{'name': 'role-a', 'scopes': ['admin:servers']}],
            id="preserve role assignment if `users` key is absent in `load_managed_roles()` result",
        ),
    ],
)
async def test_auth_load_managed_roles_preserves_assignments(
    app, caplog, roles_after_restart
):
    log = logging.getLogger("testlog")
    caplog.set_level(logging.INFO, logger=log.name)
    authenticator = MockRolesAuthenticator(
        parent=app,
        initial_roles=[
            {'name': 'role-a', 'scopes': ['admin:servers'], 'users': ['test-user']},
            {'name': 'role-b', 'scopes': ['admin:servers'], 'users': ['test-user']},
        ],
    )
    authenticator.reset_managed_roles_on_startup = True

    hub = MockHub(authenticator=authenticator, log=log)
    hub.init_db()

    # simulate hub startup, it should assign the roles to the user
    await hub.init_role_creation()
    await hub.init_role_assignment()
    user = orm.User.find(hub.db, 'test-user')

    user_role_names = {r.name for r in user.roles}
    assert 'role-a' in user_role_names
    assert 'role-b' in user_role_names

    message = (
        "Deleted %s stale %s role assignments previously added by an authenticator"
    )
    assert message not in {record.msg for record in caplog.records}

    # simulate hub restart after changing `load_managed_roles()` result
    authenticator.initial_roles = roles_after_restart

    await hub.init_role_assignment()
    hub.db.refresh(user)

    user_role_names = {r.name for r in user.roles}
    assert 'role-a' in user_role_names
    assert 'role-b' not in user_role_names

    record_map = {record.msg: record for record in caplog.records}
    assert message in record_map
    record = record_map[message]
    # should only delete the second assignment, hence the log should only say "1"
    assert record.getMessage().startswith('Deleted 1 stale user role assignments')


async def test_auth_load_managed_roles_preserves_roles(app, caplog):
    log = logging.getLogger("testlog")
    caplog.set_level(logging.INFO, logger=log.name)
    authenticator = MockRolesAuthenticator(
        parent=app,
        initial_roles=[
            {'name': 'role-a', 'scopes': ['admin:servers']},
            {'name': 'role-b', 'scopes': ['admin:servers']},
        ],
    )
    authenticator.reset_managed_roles_on_startup = True

    hub = MockHub(authenticator=authenticator, log=log)
    hub.init_db()

    def find_role(name):
        return hub.db.query(orm.Role).filter(orm.Role.name == name).first()

    # simulate hub startup, it should create both roles
    await hub.init_role_creation()
    await hub.init_role_assignment()
    assert find_role('role-a') and find_role('role-b')

    message = "Deleted %s stale roles previously added by an authenticator"
    assert message not in {record.msg for record in caplog.records}

    # simulate hub restart with only the first role preserved
    authenticator.initial_roles = authenticator.initial_roles[:1]

    await hub.init_role_creation()
    assert find_role('role-a') and not find_role('role-b')

    record_map = {record.msg: record for record in caplog.records}
    assert message in record_map
    record = record_map[message]
    # should only delete the second role, hence the log should only say "1"
    assert record.getMessage().startswith('Deleted 1 stale roles')


@pytest.mark.parametrize(
    "authenticated_roles",
    [
        (None),
        ([{"name": "role-1"}]),
        ([{"name": "role-2", "description": "test role 2"}]),
        ([{"name": "role-3", "scopes": ["admin:servers"]}]),
    ],
)
async def test_auth_managed_roles(app, user, role, authenticated_roles):
    authenticator = MockRolesAuthenticator(
        parent=app,
        authenticated_roles=authenticated_roles,
    )
    user.roles.append(role)
    app.db.commit()
    before_roles = [
        {
            'name': r.name,
            'description': r.description,
            'scopes': r.scopes,
            'users': r.users,
        }
        for r in user.roles
    ]

    if authenticated_roles is None:
        expected_roles = before_roles
    else:
        expected_roles = authenticated_roles

    # Check if user gets auth-managed roles
    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)
        assert not app.db.dirty

        assert len(user.roles) == len(expected_roles)

        for expected_role in expected_roles:
            role = orm.Role.find(app.db, expected_role['name'])
            assert role.description == expected_role.get('description', None)
            assert len(role.scopes) == len(expected_role.get('scopes', []))


@pytest.mark.parametrize(
    "role_spec,expected",
    [
        [
            {"name": "role-with-services", "services": ["missing-service"]},
            "Could not assign the role role-with-services to services: ['missing-service']",
        ],
        [
            {"name": "role-with-users", "users": ["missing-user"]},
            "Could not assign the role role-with-users to users: ['missing-user']",
        ],
        [
            {"name": "role-with-groups", "groups": ["missing-group"]},
            "Could not assign the role role-with-groups to groups: ['missing-group']",
        ],
    ],
)
async def test_auth_manage_roles_warns_about_unknown_entities(
    app, user, role_spec, expected
):
    # Add the current user to test that non-missing entities are not included in the warning
    role_spec['users'] = [*role_spec.get('users', []), user.name]
    # Add a scope to silence "Role will have no scopes" warning
    role_spec['scopes'] = ['admin:servers']

    authenticator = MockRolesAuthenticator(parent=app, authenticated_roles=[role_spec])

    logs = []

    def log_mock(template, *args):
        logs.append(template.format(args))

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        with mock.patch.object(user.log, 'warning', new=log_mock):
            await app.login_user(user.name)
            assert len(logs) == 1
            assert expected in logs[0]


async def test_auth_manage_roles_strips_user_of_old_roles(app, user, role):
    authenticator = MockRolesAuthenticator(parent=app, authenticated_roles=[])
    user.roles.append(role)
    app.db.commit()
    assert [role.name for role in user.roles] == ['user', role.name]

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)
        assert not app.db.dirty
        assert [role.name for role in user.roles] == []


async def test_auth_manage_roles_grants_new_roles(app, user, role):
    authenticator = MockRolesAuthenticator(
        parent=app, authenticated_roles=[{'name': 'user'}, role_to_dict(role)]
    )
    assert [role.name for role in user.roles] == ['user']

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)
        assert not app.db.dirty
        assert [role.name for role in user.roles] == ['user', role.name]


async def test_auth_manage_roles_removes_no_longer_used_roles(app, user):
    count_roles = (
        app.db.query(orm.Role).filter(orm.Role.name == 'new-managed-role').count
    )
    authenticator = MockRolesAuthenticator(
        parent=app, authenticated_roles=[{'name': 'new-managed-role'}]
    )
    # this role should not exist yet
    assert count_roles() == 0

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)
        assert count_roles() == 1

        authenticator.authenticated_roles = []

        await app.login_user(user.name)
        assert count_roles() == 0


async def test_auth_manage_roles_does_not_remove_stripped_roles_if_used(
    app, user, group
):
    find_role = app.db.query(orm.Role).filter(orm.Role.name == 'new-managed-role').first
    authenticator = MockRolesAuthenticator(
        parent=app, authenticated_roles=[{'name': 'new-managed-role'}]
    )
    # this role should not exist yet
    assert find_role() is None

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)
        role = find_role()
        assert role

        # assign a group to the role
        role.groups = [group]
        app.db.commit()

        authenticator.authenticated_roles = []

        await app.login_user(user.name)
        assert find_role()


async def test_auth_manage_roles_does_not_remove_non_managed_roles(app, user, role):
    count_roles = app.db.query(orm.Role).filter(orm.Role.name == role.name).count
    authenticator = MockRolesAuthenticator(
        parent=app, authenticated_roles=[role_to_dict(role)]
    )
    # this role is created by the fixture and should already exist
    assert count_roles() == 1

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)

        authenticator.authenticated_roles = []

        await app.login_user(user.name)
        # should not delete the role as this role was not created by the authenticator
        assert count_roles() == 1


async def test_auth_manage_roles_marks_new_role_as_managed(app, user):
    authenticator = MockRolesAuthenticator(
        parent=app, authenticated_roles=[{'name': 'new-role'}]
    )

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)
        assert not app.db.dirty
        assert user.roles[0].managed_by_auth


async def test_auth_manage_roles_marks_new_assignment_as_managed(app, user, role):
    authenticator = MockRolesAuthenticator(
        parent=app, authenticated_roles=[role_to_dict(role)]
    )

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)
        assert not app.db.dirty
        UserRoleMap = orm._role_associations['user']
        association = (
            app.db.query(UserRoleMap)
            .filter((UserRoleMap.role_id == role.id) & (UserRoleMap.user_id == user.id))
            .one()
        )
        assert association.managed_by_auth


@pytest.mark.parametrize(
    "role_spec,expected",
    [
        pytest.param(
            {'name': 'role-a'},
            'Test description',
            id="should keep the original role description",
        ),
        pytest.param(
            {'name': 'role-b', 'description': 'New description'},
            'New description',
            id="should update the role description",
        ),
    ],
)
async def test_auth_manage_roles_description_handling(app, user, role_spec, expected):
    authenticator = MockRolesAuthenticator(parent=app, authenticated_roles=[role_spec])
    name = role_spec['name']
    role = orm.Role(name=name, description='Test description')
    user.roles.append(role)
    app.db.commit()

    with mock.patch.dict(app.tornado_settings, {"authenticator": authenticator}):
        await app.login_user(user.name)
        assert not app.db.dirty
        roles = {role.name: role for role in user.roles}
        assert roles[name].description == expected


@pytest.mark.parametrize(
    "allowed_users,  allow_existing_users",
    [
        ('specified', True),
        ('', False),
    ],
)
async def test_allow_defaults(app, user, allowed_users, allow_existing_users):
    if allowed_users:
        allowed_users = set(allowed_users.split(','))
    else:
        allowed_users = set()
    authenticator = auth.Authenticator(allowed_users=allowed_users)
    authenticator.authenticate = lambda handler, data: data["username"]
    assert authenticator.allow_all is False
    assert authenticator.allow_existing_users == allow_existing_users

    # user was already in the database
    # this happens during hub startup
    authenticator.add_user(user)
    if allowed_users:
        assert user.name in authenticator.allowed_users
    else:
        authenticator.allowed_users == set()

    specified_allowed = await authenticator.get_authenticated_user(
        None, {"username": "specified"}
    )
    if "specified" in allowed_users:
        assert specified_allowed is not None
    else:
        assert specified_allowed is None

    existing_allowed = await authenticator.get_authenticated_user(
        None, {"username": user.name}
    )
    if allow_existing_users:
        assert existing_allowed is not None
    else:
        assert existing_allowed is None


@pytest.mark.parametrize("allow_all", [None, True, False])
@pytest.mark.parametrize("allow_existing_users", [None, True, False])
@pytest.mark.parametrize("allowed_users", ["existing", ""])
def test_allow_existing_users(
    app, user, allowed_users, allow_all, allow_existing_users
):
    if allowed_users:
        allowed_users = set(allowed_users.split(','))
    else:
        allowed_users = set()
    authenticator = auth.Authenticator(
        allowed_users=allowed_users,
    )
    if allow_all is None:
        # default allow_all
        allow_all = authenticator.allow_all
    else:
        authenticator.allow_all = allow_all
    if allow_existing_users is None:
        # default allow_all
        allow_existing_users = authenticator.allow_existing_users
    else:
        authenticator.allow_existing_users = allow_existing_users

    # first, nobody in the database
    assert authenticator.check_allowed("newuser") == allow_all

    # user was already in the database
    # this happens during hub startup
    authenticator.add_user(user)
    if allow_existing_users or allow_all:
        assert authenticator.check_allowed(user.name)
    else:
        assert not authenticator.check_allowed(user.name)
    for username in allowed_users:
        assert authenticator.check_allowed(username)

    assert authenticator.check_allowed("newuser") == allow_all


@pytest.mark.parametrize("allow_all", [True, False])
@pytest.mark.parametrize("allow_existing_users", [True, False])
def test_allow_existing_users_first_time(user, allow_all, allow_existing_users):
    # make sure that calling add_user doesn't change results
    authenticator = auth.Authenticator(
        allow_all=allow_all,
        allow_existing_users=allow_existing_users,
    )
    allowed_before_one = authenticator.check_allowed(user.name)
    allowed_before_two = authenticator.check_allowed("newuser")
    # add_user is called after successful login
    # it shouldn't change results (e.g. by switching .allowed_users from empty to non-empty)
    if allowed_before_one:
        authenticator.add_user(user)
    assert authenticator.check_allowed(user.name) == allowed_before_one
    assert authenticator.check_allowed("newuser") == allowed_before_two


class AllowAllIgnoringAuthenticator(auth.Authenticator):
    """Test authenticator with custom check_allowed

    not updated for allow_all, allow_existing_users

    Make sure new config doesn't break backward-compatibility
    or grant unintended access for Authenticators written before JupyterHub 5.
    """

    allowed_letters = Tuple(config=True, help="Initial letters to allow")

    def authenticate(self, handler, data):
        return {"name": data["username"]}

    def check_allowed(self, username, auth=None):
        if not self.allowed_users and not self.allowed_letters:
            # this subclass doesn't know about the JupyterHub 5 allow_all config
            # no allow config, allow all!
            return True
        if self.allowed_users and username in self.allowed_users:
            return True
        if self.allowed_letters and username.startswith(self.allowed_letters):
            return True
        return False


# allow_all is not recognized by Authenticator subclass
# make sure it doesn't make anything more permissive, at least
@pytest.mark.parametrize("allow_all", [True, False])
@pytest.mark.parametrize(
    "allowed_users, allowed_letters, allow_existing_users, allowed, not_allowed",
    [
        ("", "", None, "anyone,should-be,allowed,existing", ""),
        ("", "a,b", None, "alice,bebe", "existing,other"),
        ("", "a,b", False, "alice,bebe", "existing,other"),
        ("", "a,b", True, "alice,bebe,existing", "other"),
        ("specified", "a,b", None, "specified,alice,bebe,existing", "other"),
        ("specified", "a,b", False, "specified,alice,bebe", "existing,other"),
        ("specified", "a,b", True, "specified,alice,bebe,existing", "other"),
    ],
)
async def test_authenticator_without_allow_all(
    app,
    allowed_users,
    allowed_letters,
    allow_existing_users,
    allowed,
    not_allowed,
    allow_all,
):
    kwargs = {}
    if allow_all is not None:
        kwargs["allow_all"] = allow_all
    if allow_existing_users is not None:
        kwargs["allow_existing_users"] = allow_existing_users
    if allowed_users:
        kwargs["allowed_users"] = set(allowed_users.split(','))
    if allowed_letters:
        kwargs["allowed_letters"] = tuple(allowed_letters.split(','))

    authenticator = AllowAllIgnoringAuthenticator(**kwargs)

    # load one user from db
    existing_user = add_user(app.db, app, name="existing")
    authenticator.add_user(existing_user)

    if allowed:
        allowed = allowed.split(",")
    if not_allowed:
        not_allowed = not_allowed.split(",")

    expected_allowed = sorted(allowed)
    expected_not_allowed = sorted(not_allowed)
    to_check = list(chain(expected_allowed, expected_not_allowed))
    if allow_all:
        expected_allowed = to_check
        expected_not_allowed = []

    are_allowed = []
    are_not_allowed = []
    for username in to_check:
        if await authenticator.get_authenticated_user(None, {"username": username}):
            are_allowed.append(username)
        else:
            are_not_allowed.append(username)

    assert are_allowed == expected_allowed
    assert are_not_allowed == expected_not_allowed
