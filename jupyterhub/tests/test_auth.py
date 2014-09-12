"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

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
    
    with mock.patch('simplepam.authenticate', fake_auth):
        authorized = io_loop.run_sync(lambda : authenticator.authenticate(None, {
            u'username': u'match',
            u'password': u'nomatch',
        }))
    assert authorized is None
