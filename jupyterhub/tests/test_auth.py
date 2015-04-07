"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from .mocking import MockPAMAuthenticator
from unittest import mock

from jupyterhub import auth

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

