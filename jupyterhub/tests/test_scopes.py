"""Test scopes for API handlers"""
import json
from unittest import mock

import pytest
from pytest import mark
from tornado import web
from tornado.httputil import HTTPServerRequest

from .. import orm
from .. import roles
from ..scopes import _check_scope
from ..scopes import _parse_scopes
from ..scopes import needs_scope
from ..scopes import Scope
from .mocking import MockHub
from .utils import add_user
from .utils import api_request
from .utils import auth_header
from .utils import public_url


def test_scope_constructor():
    user1 = 'george'
    user2 = 'michael'
    scope_list = [
        'users',
        'read:users!user={}'.format(user1),
        'read:users!user={}'.format(user2),
    ]
    parsed_scopes = _parse_scopes(scope_list)

    assert 'read:users' in parsed_scopes
    assert parsed_scopes['users']
    assert set(parsed_scopes['read:users']['user']) == {user1, user2}


def test_scope_precendence():
    scope_list = ['read:users!user=maeby', 'read:users']
    parsed_scopes = _parse_scopes(scope_list)
    assert parsed_scopes['read:users'] == Scope.ALL


def test_scope_check_present():
    handler = None
    scope_list = ['read:users']
    parsed_scopes = _parse_scopes(scope_list)
    assert _check_scope(handler, 'read:users', parsed_scopes)
    assert _check_scope(handler, 'read:users', parsed_scopes, user='maeby')


def test_scope_check_not_present():
    handler = None
    scope_list = ['read:users!user=maeby']
    parsed_scopes = _parse_scopes(scope_list)
    assert not _check_scope(handler, 'read:users', parsed_scopes)
    assert not _check_scope(handler, 'read:users', parsed_scopes, user='gob')
    assert not _check_scope(
        handler, 'read:users', parsed_scopes, user='gob', server='server'
    )


def test_scope_filters():
    handler = None
    scope_list = ['read:users', 'read:users!group=bluths', 'read:users!user=maeby']
    parsed_scopes = _parse_scopes(scope_list)
    assert _check_scope(handler, 'read:users', parsed_scopes, group='bluth')
    assert _check_scope(handler, 'read:users', parsed_scopes, user='maeby')


def test_scope_multiple_filters():
    handler = None
    assert _check_scope(
        handler,
        'read:users',
        _parse_scopes(['read:users!user=george_michael']),
        user='george_michael',
        group='bluths',
    )


def test_scope_parse_server_name():
    handler = None
    scope_list = ['users:servers!server=maeby/server1', 'read:users!user=maeby']
    parsed_scopes = _parse_scopes(scope_list)
    assert _check_scope(
        handler, 'users:servers', parsed_scopes, user='maeby', server='server1'
    )


class MockAPIHandler:
    def __init__(self):
        self.scopes = {'users'}

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

    @needs_scope('users')
    @needs_scope('read:services')
    def secret_thing(self):
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
        (['users!user=george'], 'user_thing', ('fake_user',), False),
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
    obj.current_user = mock.Mock(name=arguments[0])
    obj.request = mock.Mock(spec=HTTPServerRequest)
    obj.scopes = set(scopes)
    api_call = getattr(obj, method)
    if is_allowed:
        assert api_call(*arguments)
    else:
        with pytest.raises(web.HTTPError):
            api_call(*arguments)


def test_double_scoped_method_succeeds():
    obj = MockAPIHandler()
    obj.current_user = mock.Mock(name='lucille')
    obj.request = mock.Mock(spec=HTTPServerRequest)
    obj.scopes = {'users', 'read:services'}
    assert obj.secret_thing()


def test_double_scoped_method_denials():
    obj = MockAPIHandler()
    obj.current_user = mock.Mock(name='lucille2')
    obj.request = mock.Mock(spec=HTTPServerRequest)
    obj.scopes = {'users', 'read:groups'}
    with pytest.raises(web.HTTPError):
        obj.secret_thing()


def generate_test_role(user_name, scopes, role_name='test'):
    role = {
        'name': role_name,
        'description': '',
        'users': [user_name],
        'scopes': scopes,
    }
    return role


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


async def test_non_existing_user(app):
    user_name = 'shade'
    user = add_user(app.db, name=user_name)
    auth_ = auth_header(app.db, user_name)
    app.users.delete(user)
    app.db.commit()
    r = await api_request(app, 'users', headers=auth_)
    assert r.status_code == 403


async def test_user_filter(app):
    user_name = 'rita'
    user = add_user(app.db, name=user_name)
    app.db.commit()
    scopes = ['read:users!user=lindsay', 'read:users!user=gob', 'read:users!user=oscar']
    test_role = generate_test_role(user, scopes)
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')
    roles.remove_obj(app.db, objname=user_name, kind='users', rolename='user')
    name_in_scope = {'lindsay', 'oscar', 'gob'}
    outside_scope = {'maeby', 'marta'}
    group_name = 'bluth'
    group = orm.Group.find(app.db, name=group_name)
    if not group:
        group = orm.Group(name=group_name)
        app.db.add(group)
    for name in name_in_scope | outside_scope:
        user = add_user(app.db, name=name)
        if name not in group.users:
            group.users.append(user)
    app.db.commit()
    r = await api_request(app, 'users', headers=auth_header(app.db, user_name))
    assert r.status_code == 200
    result_names = {user['name'] for user in r.json()}
    assert result_names == name_in_scope


async def test_service_filter(app):
    services = [
        {'name': 'cull_idle', 'api_token': 'some-token'},
        {'name': 'user_service', 'api_token': 'some-other-token'},
    ]
    for service in services:
        app.services.append(service)
    app.init_services()
    user_name = 'buster'
    user = add_user(app.db, name=user_name)
    app.db.commit()
    test_role = generate_test_role(user, ['read:services!service=cull_idle'])
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')
    r = await api_request(app, 'services', headers=auth_header(app.db, user_name))
    assert r.status_code == 200
    service_names = set(r.json().keys())
    assert service_names == {'cull_idle'}


async def test_user_filter_with_group(app):
    # Move role setup to setup method?
    user_name = 'sally'
    add_user(app.db, name=user_name)
    external_user_name = 'britta'
    add_user(app.db, name=external_user_name)
    test_role = generate_test_role(user_name, ['read:users!group=sitwell'])
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')

    name_set = {'sally', 'stan'}
    group_name = 'sitwell'
    group = orm.Group.find(app.db, name=group_name)
    if not group:
        group = orm.Group(name=group_name)
        app.db.add(group)
    for name in name_set:
        user = add_user(app.db, name=name)
        if name not in group.users:
            group.users.append(user)
    app.db.commit()

    r = await api_request(app, 'users', headers=auth_header(app.db, user_name))
    assert r.status_code == 200
    result_names = {user['name'] for user in r.json()}
    assert result_names == name_set
    assert external_user_name not in result_names


async def test_group_scope_filter(app):
    user_name = 'rollerblade'
    add_user(app.db, name=user_name)
    scopes = ['read:groups!group=sitwell', 'read:groups!group=bluth']
    test_role = generate_test_role(user_name, scopes)
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')

    group_set = {'sitwell', 'bluth', 'austero'}
    for group_name in group_set:
        group = orm.Group.find(app.db, name=group_name)
        if not group:
            group = orm.Group(name=group_name)
            app.db.add(group)
    app.db.commit()
    r = await api_request(app, 'groups', headers=auth_header(app.db, user_name))
    assert r.status_code == 200
    result_names = {user['name'] for user in r.json()}
    assert result_names == {'sitwell', 'bluth'}
