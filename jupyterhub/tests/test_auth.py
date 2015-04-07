"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from subprocess import CalledProcessError
from unittest import mock

import pytest
from .mocking import MockPAMAuthenticator

from jupyterhub import auth, orm

def test_pam_auth(io_loop):
    authenticator = MockPAMAuthenticator()
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        'username': 'match',
        'password': 'match',
    }))
    assert authorized == 'match'
    
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        'username': 'match',
        'password': 'nomatch',
    }))
    assert authorized is None

def test_pam_auth_whitelist(io_loop):
    authenticator = MockPAMAuthenticator(whitelist={'wash', 'kaylee'})
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        'username': 'kaylee',
        'password': 'kaylee',
    }))
    assert authorized == 'kaylee'
    
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        'username': 'wash',
        'password': 'nomatch',
    }))
    assert authorized is None
    
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
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
        authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
            'username': 'kaylee',
            'password': 'kaylee',
        }))
    assert authorized == 'kaylee'

    with mock.patch.object(auth, 'getgrnam', getgrnam):
        authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
            'username': 'mal',
            'password': 'mal',
        }))
    assert authorized is None


def test_pam_auth_no_such_group(io_loop):
    authenticator = MockPAMAuthenticator(group_whitelist={'nosuchcrazygroup'})
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
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
    authenticator.create_system_users = True
    
    def check_output(cmd, *a, **kw):
        raise CalledProcessError(1, cmd)
    
    with mock.patch.object(auth, 'check_output', check_output):
        with pytest.raises(RuntimeError):
            io_loop.run_sync(lambda : authenticator.add_user(user))


def test_add_system_user(io_loop):
    user = orm.User(name='lioness4321')
    authenticator = auth.PAMAuthenticator(whitelist={'mal'})
    authenticator.create_system_users = True
    
    def check_output(*a, **kw):
        return
    
    record = {}
    def check_call(cmd, *a, **kw):
        record['cmd'] = cmd
    
    with mock.patch.object(auth, 'check_output', check_output), \
             mock.patch.object(auth, 'check_call', check_call):
        io_loop.run_sync(lambda : authenticator.add_user(user))
    
    assert user.name in record['cmd']


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


