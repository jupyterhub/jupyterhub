"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

try:
    from unittest import mock # py3
except ImportError:
    import mock

import simplepam
from IPython.utils.py3compat import unicode_type

from ..auth import PAMAuthenticator


def fake_auth(username, password, service='login'):
    # mimic simplepam's failure to handle unicode
    if isinstance(username, unicode_type):
        return False
    if isinstance(password, unicode_type):
        return False
    
    # just use equality
    if password == username:
        return True


def test_pam_auth(io_loop):
    authenticator = PAMAuthenticator()
    with mock.patch('simplepam.authenticate', fake_auth):
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
    authenticator = PAMAuthenticator(whitelist={'wash', 'kaylee'})
    with mock.patch('simplepam.authenticate', fake_auth):
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
