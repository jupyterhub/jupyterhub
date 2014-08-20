"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import mock
import simplepam
from tornado.testing import AsyncTestCase, gen_test
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

class TestPAM(AsyncTestCase):
    
    @gen_test
    def test_pam_auth(self):
        authenticator = PAMAuthenticator()
        with mock.patch('simplepam.authenticate', fake_auth):
            authorized = yield authenticator.authenticate(None, {
                u'username': u'match',
                u'password': u'match',
            })
        self.assertEqual(authorized, u'match')
        
        with mock.patch('simplepam.authenticate', fake_auth):
            authorized = yield authenticator.authenticate(None, {
                u'username': u'match',
                u'password': u'nomatch',
            })
        self.assertEqual(authorized, None)

