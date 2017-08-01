"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
from unittest import mock

import pytest
from requests import HTTPError

from jupyterhub import auth, crypto, orm

from .mocking import MockPAMAuthenticator
from .test_api import add_user

@pytest.mark.gen_test
def test_pam_auth():
    authenticator = MockPAMAuthenticator()
    authorized = yield authenticator.get_authenticated_user(None, {
        'username': 'match',
        'password': 'match',
    })
    assert authorized['name'] == 'match'
    
    authorized = yield authenticator.get_authenticated_user(None, {
        'username': 'match',
        'password': 'nomatch',
    })
    assert authorized is None


@pytest.mark.gen_test
def test_pam_auth_whitelist():
    authenticator = MockPAMAuthenticator(whitelist={'wash', 'kaylee'})
    authorized = yield authenticator.get_authenticated_user(None, {
        'username': 'kaylee',
        'password': 'kaylee',
    })
    assert authorized['name'] == 'kaylee'
    
    authorized = yield authenticator.get_authenticated_user(None, {
        'username': 'wash',
        'password': 'nomatch',
    })
    assert authorized is None
    
    authorized = yield authenticator.get_authenticated_user(None, {
        'username': 'mal',
        'password': 'mal',
    })
    assert authorized is None


class MockGroup:
    def __init__(self, *names):
        self.gr_mem = names


@pytest.mark.gen_test
def test_pam_auth_group_whitelist():
    g = MockGroup('kaylee')
    def getgrnam(name):
        return g
    
    authenticator = MockPAMAuthenticator(group_whitelist={'group'})
    
    with mock.patch.object(auth, 'getgrnam', getgrnam):
        authorized = yield authenticator.get_authenticated_user(None, {
            'username': 'kaylee',
            'password': 'kaylee',
        })
    assert authorized['name'] == 'kaylee'

    with mock.patch.object(auth, 'getgrnam', getgrnam):
        authorized = yield authenticator.get_authenticated_user(None, {
            'username': 'mal',
            'password': 'mal',
        })
    assert authorized is None


@pytest.mark.gen_test
def test_pam_auth_no_such_group():
    authenticator = MockPAMAuthenticator(group_whitelist={'nosuchcrazygroup'})
    authorized = yield authenticator.get_authenticated_user(None, {
        'username': 'kaylee',
        'password': 'kaylee',
    })
    assert authorized is None


@pytest.mark.gen_test
def test_wont_add_system_user():
    user = orm.User(name='lioness4321')
    authenticator = auth.PAMAuthenticator(whitelist={'mal'})
    authenticator.create_system_users = False
    with pytest.raises(KeyError):
        yield authenticator.add_user(user)


@pytest.mark.gen_test
def test_cant_add_system_user():
    user = orm.User(name='lioness4321')
    authenticator = auth.PAMAuthenticator(whitelist={'mal'})
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
            yield authenticator.add_user(user)
        assert str(exc.value) == 'Failed to create system user lioness4321: dummy error'


@pytest.mark.gen_test
def test_add_system_user():
    user = orm.User(name='lioness4321')
    authenticator = auth.PAMAuthenticator(whitelist={'mal'})
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
        yield authenticator.add_user(user)
    assert record['cmd'] == ['echo', '/home/lioness4321', 'lioness4321']


@pytest.mark.gen_test
def test_delete_user():
    user = orm.User(name='zoe')
    a = MockPAMAuthenticator(whitelist={'mal'})
    
    assert 'zoe' not in a.whitelist
    a.add_user(user)
    assert 'zoe' in a.whitelist
    a.delete_user(user)
    assert 'zoe' not in a.whitelist


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


@pytest.fixture
def auth_state_enabled(app):
    app.authenticator.auth_state = {
        'who': 'cares',
    }
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


@pytest.mark.gen_test
def test_auth_state(app, auth_state_enabled):
    """auth_state enabled and available"""
    name = 'kiwi'
    user = add_user(app.db, app, name=name)
    assert user.encrypted_auth_state is None
    cookies = yield app.login_user(name)
    auth_state = yield user.get_auth_state()
    assert auth_state == app.authenticator.auth_state


@pytest.fixture
def auth_state_unavailable(auth_state_enabled):
    """auth_state enabled at the Authenticator level,
    
    but unavailable due to no crypto keys.
    """
    crypto.CryptKeeper.instance().keys = []
    yield


@pytest.mark.gen_test
def test_auth_state_disabled(app, auth_state_unavailable):
    name = 'driebus'
    user = add_user(app.db, app, name=name)
    assert user.encrypted_auth_state is None
    with pytest.raises(HTTPError):
        cookies = yield app.login_user(name)
    auth_state = yield user.get_auth_state()
    assert auth_state is None


@pytest.mark.gen_test
def test_normalize_names():
    a = MockPAMAuthenticator()
    authorized = yield a.get_authenticated_user(None, {
        'username': 'ZOE',
        'password': 'ZOE',
    })
    assert authorized['name'] == 'zoe'

    authorized = yield a.get_authenticated_user(None, {
        'username': 'Glenn',
        'password': 'Glenn',
    })
    assert authorized['name'] == 'glenn'

    authorized = yield a.get_authenticated_user(None, {
        'username': 'hExi',
        'password': 'hExi',
    })
    assert authorized['name'] == 'hexi'

    authorized = yield a.get_authenticated_user(None, {
        'username': 'Test',
        'password': 'Test',
    })
    assert authorized['name'] == 'test'


@pytest.mark.gen_test
def test_username_map():
    a = MockPAMAuthenticator(username_map={'wash': 'alpha'})
    authorized = yield a.get_authenticated_user(None, {
        'username': 'WASH',
        'password': 'WASH',
    })

    assert authorized['name'] == 'alpha'

    authorized = yield a.get_authenticated_user(None, {
        'username': 'Inara',
        'password': 'Inara',
    })
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


