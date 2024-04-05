"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import logging
from unittest import mock
from urllib.parse import urlparse

import pytest
from requests import HTTPError
from traitlets import Any
from traitlets.config import Config

from jupyterhub import auth, crypto, orm

from .mocking import MockHub, MockPAMAuthenticator, MockStructGroup, MockStructPasswd
from .utils import add_user, async_requests, get_page, public_url


async def test_pam_auth():
    authenticator = MockPAMAuthenticator()
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
    authenticator = MockPAMAuthenticator(check_account=False)
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
        admin_groups={'jh_admins', 'wheel'}, admin_users={'override_admin'}
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
    authenticator = MockPAMAuthenticator(allowed_users={'wash', 'kaylee'})
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
    def getgrnam(name):
        return MockStructGroup('grp', ['kaylee'])

    authenticator = MockPAMAuthenticator(allowed_groups={'group'})

    with mock.patch.object(authenticator, '_getgrnam', getgrnam):
        authorized = await authenticator.get_authenticated_user(
            None, {'username': 'kaylee', 'password': 'kaylee'}
        )
    assert authorized['name'] == 'kaylee'

    with mock.patch.object(authenticator, '_getgrnam', getgrnam):
        authorized = await authenticator.get_authenticated_user(
            None, {'username': 'mal', 'password': 'mal'}
        )
    assert authorized is None


async def test_pam_auth_blocked():
    # Null case compared to next case
    authenticator = MockPAMAuthenticator()
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'wash', 'password': 'wash'}
    )
    assert authorized['name'] == 'wash'

    # Blacklist basics
    authenticator = MockPAMAuthenticator(blocked_users={'wash'})
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'wash', 'password': 'wash'}
    )
    assert authorized is None

    # User in both allowed and blocked: default deny.  Make error someday?
    authenticator = MockPAMAuthenticator(
        blocked_users={'wash'}, allowed_users={'wash', 'kaylee'}
    )
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'wash', 'password': 'wash'}
    )
    assert authorized is None

    # User not in blocked set can log in
    authenticator = MockPAMAuthenticator(
        blocked_users={'wash'}, allowed_users={'wash', 'kaylee'}
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
        blocked_users={'mal'}, allowed_users={'wash', 'kaylee'}
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
    authenticator = MockPAMAuthenticator(allowed_groups={'nosuchcrazygroup'})
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
    a = MockPAMAuthenticator()
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
    a = MockPAMAuthenticator(username_map={'wash': 'alpha'})
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

    a = MockPAMAuthenticator(post_auth_hook=test_auth_hook)

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
    expected_roles = [role_to_dict(role) for role in hub.db.query(orm.Role).all()]

    # create the roles using authenticator's `load_managed_roles`
    hub = MockHub(load_roles=[], authenticator=authenticator)
    hub.init_db()
    await hub.init_role_creation()
    actual_roles = [role_to_dict(role) for role in hub.db.query(orm.Role).all()]

    # `load_managed_roles` should produce the same set of roles as `load_roles` does
    assert expected_roles == actual_roles


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
        UserRoleMap = orm.role_associations['user']
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
