"""Tests for PAM authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from ..auth import DictionaryAuthenticator
from IPython.lib.security import passwd
from .mocking import MockPAMAuthenticator


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

def test_dictionary_auth(io_loop):
    authenticator = DictionaryAuthenticator(
        users={
            'test_user1': passwd('test_password1'),
            'test_user2': passwd('test_password2'),
        }
    )

    bad_pass = 'incorrect'
    for i in map(str, range(1, 3)):
        username = 'test_user' + i
        good_pass = 'test_password' + i

        authorized = io_loop.run_sync(
            lambda : authenticator.authenticate(
                None,
                {
                    'username': username,
                    'password': good_pass,
                }
            )
        )
        assert authorized == username

        authorized = io_loop.run_sync(
            lambda : authenticator.authenticate(
                None,
                {
                    'username': username,
                    'password': bad_pass,
                }
            )
        )
        assert authorized is None

    # Verify handling of a non-existent user.
    authorized = io_loop.run_sync(
        lambda : authenticator.authenticate(
            None,
            {
                'username': 'not_a_real_user',
                'password': 'test_password1',
            }
        )
    )
    assert authorized is None

