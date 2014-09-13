"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from .mocking import MockPAMAuthenticator


def test_pam_auth(io_loop):
    authenticator = MockPAMAuthenticator()
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        u'username': u'match',
        u'password': u'match',
    }))
    assert authorized == u'match'
    
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        u'username': u'match',
        u'password': u'nomatch',
    }))
    assert authorized is None

def test_pam_auth_whitelist(io_loop):
    authenticator = MockPAMAuthenticator(whitelist={'wash', 'kaylee'})
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        u'username': u'kaylee',
        u'password': u'kaylee',
    }))
    assert authorized == u'kaylee'
    
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        u'username': u'wash',
        u'password': u'nomatch',
    }))
    assert authorized is None
    
    authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
        u'username': u'mal',
        u'password': u'mal',
    }))
    assert authorized is None
