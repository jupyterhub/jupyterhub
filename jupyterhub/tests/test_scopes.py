"""Test scopes for API handlers"""
import pytest
from pytest import mark
from tornado import web

from ..utils import check_scope
from ..utils import needs_scope
from ..utils import parse_scopes


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


def test_scope_parse_server_name():
    scope_list = ['users:servers!server=maeby/server1', 'read:users!user=maeby']
    parsed_scopes = parse_scopes(scope_list)
    assert check_scope('users:servers', parsed_scopes, user='maeby', server='server1')


class Test:
    def __init__(self):
        self.scopes = ['users']

    @needs_scope('users')
    def user_thing(self, user_name):
        return True

    @needs_scope('users:servers')
    def server_thing(self, user_name, server_name):
        return True

    @needs_scope('read:groups')
    def group_thing(self, group_name):
        return True

    @needs_scope('services')
    def service_thing(self, service_name):
        return True

    @needs_scope('users')
    def other_thing(self, other_name):
        return True


@mark.parametrize(
    "scopes, method, arguments, is_allowed",
    [
        (['users'], 'user_thing', ('user',), True),
        (['users'], 'user_thing', ('michael',), True),
        ([''], 'user_thing', ('michael',), False),
        (['read:users'], 'user_thing', ('gob',), False),
        (['read:users'], 'user_thing', ('michael',), False),
        (['users!user=george'], 'user_thing', ('george',), True),
        (['users!user=george'], 'user_thing', ('oscar',), False),
        (['users!user=george', 'users!user=oscar'], 'user_thing', ('oscar',), True),
        (['users:servers'], 'server_thing', ('user1', 'server_1'), True),
        (['users:servers'], 'server_thing', ('user1', ''), True),
        (['users:servers'], 'server_thing', ('user1', None), True),
        (
            ['users:servers!server=maeby/bluth'],
            'server_thing',
            ('maeby', 'bluth'),
            True,
        ),
        (['users:servers!server=maeby/bluth'], 'server_thing', ('gob', 'bluth'), False),
        (
            ['users:servers!server=maeby/bluth'],
            'server_thing',
            ('maybe', 'bluth2'),
            False,
        ),
        (['services'], 'service_thing', ('service1',), True),
        (
            ['users!user=george', 'read:groups!group=bluths'],
            'group_thing',
            ('bluths',),
            True,
        ),
        (
            ['users!user=george', 'read:groups!group=bluths'],
            'group_thing',
            ('george',),
            False,
        ),
        (
            ['groups!group=george', 'read:groups!group=bluths'],
            'group_thing',
            ('george',),
            False,
        ),
        (['users'], 'other_thing', ('gob',), True),
        (['read:users'], 'other_thing', ('gob',), False),
        (['users!user=gob'], 'other_thing', ('gob',), False),
        (['users!user=gob'], 'other_thing', ('maeby',), False),
    ],
)
def test_scope_method_access(scopes, method, arguments, is_allowed):
    obj = Test()
    obj.scopes = scopes
    api_call = getattr(obj, method)
    if is_allowed:
        assert api_call(*arguments)
    else:
        with pytest.raises(web.HTTPError):
            api_call(*arguments)
