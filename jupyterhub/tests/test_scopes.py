"""Test scopes for API handlers"""
from unittest import mock

import pytest
import tornado
from pytest import mark
from tornado import web
from tornado.httputil import HTTPServerRequest

from .. import orm
from .. import roles
from ..utils import check_scope
from ..utils import needs_scope
from ..utils import parse_scopes
from ..utils import Scope
from .utils import add_user
from .utils import api_request
from .utils import auth_header


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
    assert parsed_scopes['read:users'] == Scope.ALL


def test_scope_check_present():
    handler = None
    scope_list = ['read:users']
    parsed_scopes = parse_scopes(scope_list)
    assert check_scope(handler, 'read:users', parsed_scopes)
    assert check_scope(handler, 'read:users', parsed_scopes, user='maeby')


def test_scope_check_not_present():
    handler = None
    scope_list = ['read:users!user=maeby']
    parsed_scopes = parse_scopes(scope_list)
    assert not check_scope(handler, 'read:users', parsed_scopes)
    assert not check_scope(handler, 'read:users', parsed_scopes, user='gob')
    assert not check_scope(
        handler, 'read:users', parsed_scopes, user='gob', server='server'
    )


def test_scope_filters():
    handler = None
    scope_list = ['read:users', 'read:users!group=bluths', 'read:users!user=maeby']
    parsed_scopes = parse_scopes(scope_list)
    assert check_scope(handler, 'read:users', parsed_scopes, group='bluth')
    assert check_scope(handler, 'read:users', parsed_scopes, user='maeby')


def test_scope_one_filter_only():
    handler = None
    with pytest.raises(AttributeError):
        check_scope(
            handler, 'all', parse_scopes(['all']), user='george_michael', group='bluths'
        )


def test_scope_parse_server_name():
    handler = None
    scope_list = ['users:servers!server=maeby/server1', 'read:users!user=maeby']
    parsed_scopes = parse_scopes(scope_list)
    assert check_scope(
        handler, 'users:servers', parsed_scopes, user='maeby', server='server1'
    )


class MockAPIHandler:
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

    @needs_scope('read:services')
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
        (['read:services'], 'service_thing', ('service1',), True),
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
    obj = MockAPIHandler()
    obj.request = mock.Mock(spec=HTTPServerRequest)
    obj.scopes = scopes
    api_call = getattr(obj, method)
    if is_allowed:
        assert api_call(*arguments)
    else:
        with pytest.raises(web.HTTPError):
            api_call(*arguments)


@mark.parametrize(
    "user_name, in_group, status_code",
    [
        ('martha', False, 200),
        ('michael', True, 200),
        ('gob', True, 200),
        ('tobias', False, 403),
        ('ann', False, 403),
    ],
)
async def test_expand_groups(app, user_name, in_group, status_code):
    test_role = {
        'name': 'test',
        'description': '',
        'users': [user_name],
        'scopes': [
            'read:users!user=martha',
            'read:users!group=bluth',
            'read:groups',
        ],
    }
    roles.add_role(app.db, test_role)
    user = add_user(app.db, name=user_name)
    group_name = 'bluth'
    group = orm.Group.find(app.db, name=group_name)
    if not group:
        group = orm.Group(name=group_name)
        app.db.add(group)
    if in_group and user not in group.users:
        group.users.append(user)
    kind = 'users'
    roles.update_roles(app.db, user, kind, roles=['test'])
    roles.remove_obj(app.db, user_name, kind, 'user')
    app.db.commit()
    r = await api_request(
        app, 'users', user_name, headers=auth_header(app.db, user_name)
    )
    assert r.status_code == status_code
