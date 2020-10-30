"""Tests for PAM authentication"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import logging
from unittest import mock

import pytest
from requests import HTTPError
from traitlets.config import Config

from .mocking import MockPAMAuthenticator
from .mocking import MockStructGroup
from .mocking import MockStructPasswd
from .utils import add_user
from jupyterhub import auth
from jupyterhub import crypto
from jupyterhub import orm


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
            None, {'username': 'also_group_admin', 'password': 'also_group_admin'}
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
            None, {'username': 'override_admin', 'password': 'override_admin'}
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
