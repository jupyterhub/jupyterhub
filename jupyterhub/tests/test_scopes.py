"""
test scopes as used in rbac
"""
from unittest import mock

import pytest
from tornado import web

from ..utils import check_scope
from ..utils import needs_scope
from ..utils import parse_scopes
from .utils import get_scopes


def test_scope_constructor():
    user1 = 'george'
    user2 = 'michael'
    scope_list = [
        'users',
        'read:users!user={}'.format(user1),
        'read:users!user={}'.format(user2),
    ]
    parsed_scopes = parse_scopes(scope_list)

    assert 'read:users' in parsed_scopes
    assert parsed_scopes['users']
    assert set(parsed_scopes['read:users']['user']) == {user1, user2}


def test_scope_precendence():
    scope_list = ['read:users!user=maeby', 'read:users']
    parsed_scopes = parse_scopes(scope_list)
    assert parsed_scopes['read:users'] == True


def test_scope_check_present():
    scope_list = ['read:users']
    parsed_scopes = parse_scopes(scope_list)
    assert check_scope('read:users', parsed_scopes)
    assert check_scope('read:users!user=maeby', parsed_scopes)


def test_scope_check_not_present():  # What should this return when the broad scope is asked and a small one satisfied?
    scope_list = ['read:users!user=maeby']
    parsed_scopes = parse_scopes(scope_list)
    assert not check_scope('read:users', parsed_scopes)
    assert not check_scope('read:users', parsed_scopes, user='gob')
    assert not check_scope('read:users', parsed_scopes, server='gob/server')


def test_scope_filters():
    scope_list = ['read:users', 'read:users!group=bluths', 'read:users!user=maeby']
    parsed_scopes = parse_scopes(scope_list)
    assert check_scope('read:users!group=bluths', parsed_scopes)
    assert check_scope('read:users!user=maeby', parsed_scopes)


def test_scope_one_filter_only():
    with pytest.raises(AttributeError):
        check_scope('all', parse_scopes(['all']), user='george_michael', group='bluths')


class Test:
    def __init__(self):
        self.scopes = ['read:users']

    @needs_scope('read:users')
    def foo(self, user):
        return True


def test_scope_def():
    obj = Test()
    obj.scopes = ['read:users']
    assert obj.foo('user')
    assert obj.foo('user2')


def test_wrong_scope():
    obj = Test()
    obj.scopes = []
    with pytest.raises(web.HTTPError):
        obj.foo('user1')
