"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from unittest import mock

import pytest
from .mocking import MockPAMAuthenticator

from jupyterhub import auth, orm

def test_pam_auth(io_loop):
    authenticator = MockPAMAuthenticator()
    authorized = io_loop.run_sync(lambda : authenticator.get_authenticated_user(None, {
        'username': 'match',
        'password': 'match',
    }))
    assert authorized == 'match'
    
    authorized = io_loop.run_sync(lambda : authenticator.get_authenticated_user(None, {
        'username': 'match',
        'password': 'nomatch',
    }))
    assert authorized is None

def test_pam_auth_whitelist(io_loop):
    authenticator = MockPAMAuthenticator(whitelist={'wash', 'kaylee'})
    authorized = io_loop.run_sync(lambda : authenticator.get_authenticated_user(None, {
        'username': 'kaylee',
        'password': 'kaylee',
    }))
    assert authorized == 'kaylee'
    
    authorized = io_loop.run_sync(lambda : authenticator.get_authenticated_user(None, {
        'username': 'wash',
        'password': 'nomatch',
    }))
    assert authorized is None
    
    authorized = io_loop.run_sync(lambda : authenticator.get_authenticated_user(None, {
        'username': 'mal',
        'password': 'mal',
    }))
    assert authorized is None


class MockGroup:
    def __init__(self, *names):
        self.gr_mem = names


def test_pam_auth_group_whitelist(io_loop):
    g = MockGroup('kaylee')
    def getgrnam(name):
        return g
    
    authenticator = MockPAMAuthenticator(group_whitelist={'group'})
    
    with mock.patch.object(auth, 'getgrnam', getgrnam):
        authorized = io_loop.run_sync(lambda : authenticator.get_authenticated_user(None, {
            'username': 'kaylee',
            'password': 'kaylee',
        }))
    assert authorized == 'kaylee'

    with mock.patch.object(auth, 'getgrnam', getgrnam):
        authorized = io_loop.run_sync(lambda : authenticator.get_authenticated_user(None, {
            'username': 'mal',
            'password': 'mal',
        }))
    assert authorized is None


def test_pam_auth_no_such_group(io_loop):
    authenticator = MockPAMAuthenticator(group_whitelist={'nosuchcrazygroup'})
    authorized = io_loop.run_sync(lambda : authenticator.get_authenticated_user(None, {
        'username': 'kaylee',
        'password': 'kaylee',
    }))
    assert authorized is None


def test_wont_add_system_user(io_loop):
    user = orm.User(name='lioness4321')
    authenticator = auth.PAMAuthenticator(whitelist={'mal'})
    authenticator.create_system_users = False
    with pytest.raises(KeyError):
        io_loop.run_sync(lambda : authenticator.add_user(user))


def test_cant_add_system_user(io_loop):
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
            io_loop.run_sync(lambda : authenticator.add_user(user))
        assert str(exc.value) == 'Failed to create system user lioness4321: dummy error'


def test_add_system_user(io_loop):
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
        io_loop.run_sync(lambda : authenticator.add_user(user))
    assert record['cmd'] == ['echo', '/home/lioness4321', 'lioness4321']


def test_delete_user(io_loop):
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


def test_normalize_names(io_loop):
    a = MockPAMAuthenticator()
    authorized = io_loop.run_sync(lambda : a.get_authenticated_user(None, {
        'username': 'ZOE',
        'password': 'ZOE',
    }))
    assert authorized == 'zoe'

    authorized = io_loop.run_sync(lambda: a.get_authenticated_user(None, {
        'username': 'Glenn',
        'password': 'Glenn',
    }))
    assert authorized == 'glenn'

    authorized = io_loop.run_sync(lambda: a.get_authenticated_user(None, {
        'username': 'hExi',
        'password': 'hExi',
    }))
    assert authorized == 'hexi'

    authorized = io_loop.run_sync(lambda: a.get_authenticated_user(None, {
        'username': 'Test',
        'password': 'Test',
    }))
    assert authorized == 'test'

def test_username_map(io_loop):
    a = MockPAMAuthenticator(username_map={'wash': 'alpha'})
    authorized = io_loop.run_sync(lambda : a.get_authenticated_user(None, {
        'username': 'WASH',
        'password': 'WASH',
    }))

    assert authorized == 'alpha'

    authorized = io_loop.run_sync(lambda : a.get_authenticated_user(None, {
        'username': 'Inara',
        'password': 'Inara',
    }))
    assert authorized == 'inara'


def test_validate_names(io_loop):
    a = auth.PAMAuthenticator()
    assert a.validate_username('willow')
    assert a.validate_username('giles')
    assert a.validate_username('Test')
    assert a.validate_username('hExi')
    assert a.validate_username('Glenn#Smith!')
    a = auth.PAMAuthenticator(username_pattern='w.*')
    assert not a.validate_username('xander')
    assert a.validate_username('willow')


