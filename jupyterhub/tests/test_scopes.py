"""Test scopes for API handlers"""
import json
from unittest import mock

import pytest
from pytest import mark
from tornado import web
from tornado.httputil import HTTPServerRequest

from .. import orm
from .. import roles
from ..handlers import BaseHandler
from ..scopes import _check_scope
from ..scopes import needs_scope
from ..scopes import parse_scopes
from ..scopes import Scope
from .utils import add_user
from .utils import api_request
from .utils import auth_header


def get_handler_with_scopes(scopes):
    handler = mock.Mock(spec=BaseHandler)
    handler.parsed_scopes = parse_scopes(scopes)
    return handler


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
    handler = get_handler_with_scopes(['read:users'])
    assert _check_scope(handler, 'read:users')
    assert _check_scope(handler, 'read:users', user='maeby')


def test_scope_check_not_present():
    handler = get_handler_with_scopes(['read:users!user=maeby'])
    assert _check_scope(handler, 'read:users')
    with pytest.raises(web.HTTPError):
        _check_scope(handler, 'read:users', user='gob')
    with pytest.raises(web.HTTPError):
        _check_scope(handler, 'read:users', user='gob', server='server')


def test_scope_filters():
    handler = get_handler_with_scopes(
        ['read:users', 'read:users!group=bluths', 'read:users!user=maeby']
    )
    assert _check_scope(handler, 'read:users', group='bluth')
    assert _check_scope(handler, 'read:users', user='maeby')


def test_scope_multiple_filters():
    handler = get_handler_with_scopes(['read:users!user=george_michael'])
    assert _check_scope(handler, 'read:users', user='george_michael', group='bluths')


def test_scope_parse_server_name():
    handler = get_handler_with_scopes(
        ['users:servers!server=maeby/server1', 'read:users!user=maeby']
    )
    assert _check_scope(handler, 'users:servers', user='maeby', server='server1')


class MockAPIHandler:
    def __init__(self):
        self.raw_scopes = {'users'}
        self.parsed_scopes = {}

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
    def other_thing(self, non_filter_argument):
        # Rely on inner vertical filtering
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
        (['users!user=gob'], 'other_thing', ('gob',), True),
        (['users!user=gob'], 'other_thing', ('maeby',), True),
    ],
)
def test_scope_method_access(scopes, method, arguments, is_allowed):
    obj = MockAPIHandler()
    obj.current_user = mock.Mock(name=arguments[0])
    obj.request = mock.Mock(spec=HTTPServerRequest)
    obj.raw_scopes = set(scopes)
    obj.parsed_scopes = parse_scopes(obj.raw_scopes)
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
    obj.raw_scopes = {'users', 'read:services'}
    obj.parsed_scopes = parse_scopes(obj.raw_scopes)
    assert obj.secret_thing()


def test_double_scoped_method_denials():
    obj = MockAPIHandler()
    obj.current_user = mock.Mock(name='lucille2')
    obj.request = mock.Mock(spec=HTTPServerRequest)
    obj.raw_scopes = {'users', 'read:groups'}
    obj.parsed_scopes = parse_scopes(obj.raw_scopes)
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
        ('tobias', False, 404),
        ('ann', False, 404),
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


async def test_by_fake_user(app):
    user_name = 'shade'
    user = add_user(app.db, name=user_name)
    auth_ = auth_header(app.db, user_name)
    app.users.delete(user)
    app.db.commit()
    r = await api_request(app, 'users', headers=auth_)
    assert r.status_code == 403


err_message = "No access to resources or resources not found"


async def test_request_fake_user(app):
    user_name = 'buster'
    fake_user = 'annyong'
    add_user(app.db, name=user_name)
    test_role = generate_test_role(user_name, ['read:users!group=stuff'])
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')
    app.db.commit()
    r = await api_request(
        app, 'users', fake_user, headers=auth_header(app.db, user_name)
    )
    assert r.status_code == 404
    # Consistency between no user and user not accessible
    assert r.json()['message'] == err_message


async def test_refuse_exceeding_token_permissions(app):
    user_name = 'abed'
    user = add_user(app.db, name=user_name)
    add_user(app.db, name='user')
    api_token = user.new_api_token()
    exceeding_role = generate_test_role(user_name, ['read:users'], 'exceeding_role')
    roles.add_role(app.db, exceeding_role)
    roles.add_obj(app.db, objname=api_token, kind='tokens', rolename='exceeding_role')
    app.db.commit()
    headers = {'Authorization': 'token %s' % api_token}
    r = await api_request(app, 'users', headers=headers)
    assert r.status_code == 200
    result_names = {user['name'] for user in r.json()}
    assert result_names == {user_name}


async def test_exceeding_user_permissions(app):
    user_name = 'abed'
    user = add_user(app.db, name=user_name)
    add_user(app.db, name='user')
    api_token = user.new_api_token()
    orm_api_token = orm.APIToken.find(app.db, token=api_token)
    reader_role = generate_test_role(user_name, ['read:users'], 'reader_role')
    subreader_role = generate_test_role(
        user_name, ['read:users:groups'], 'subreader_role'
    )
    roles.add_role(app.db, reader_role)
    roles.add_role(app.db, subreader_role)
    app.db.commit()
    roles.update_roles(app.db, user, kind='users', roles=['reader_role'])
    roles.update_roles(app.db, orm_api_token, kind='tokens', roles=['subreader_role'])
    orm_api_token.roles.remove(orm.Role.find(app.db, name='token'))
    app.db.commit()

    headers = {'Authorization': 'token %s' % api_token}
    r = await api_request(app, 'users', headers=headers)
    assert r.status_code == 200
    keys = {key for user in r.json() for key in user.keys()}
    assert 'groups' in keys
    assert 'last_activity' not in keys


async def test_user_service_separation(app, mockservice_url):
    name = mockservice_url.name
    user = add_user(app.db, name=name)

    reader_role = generate_test_role(name, ['read:users'], 'reader_role')
    subreader_role = generate_test_role(name, ['read:users:groups'], 'subreader_role')
    roles.add_role(app.db, reader_role)
    roles.add_role(app.db, subreader_role)
    app.db.commit()
    roles.update_roles(app.db, user, kind='users', roles=['subreader_role'])
    roles.update_roles(
        app.db, mockservice_url.orm, kind='services', roles=['reader_role']
    )
    user.roles.remove(orm.Role.find(app.db, name='user'))
    api_token = user.new_api_token()
    app.db.commit()
    headers = {'Authorization': 'token %s' % api_token}
    r = await api_request(app, 'users', headers=headers)
    assert r.status_code == 200
    keys = {key for user in r.json() for key in user.keys()}
    assert 'groups' in keys
    assert 'last_activity' not in keys


async def test_request_user_outside_group(app):
    user_name = 'buster'
    fake_user = 'hello'
    add_user(app.db, name=user_name)
    add_user(app.db, name=fake_user)
    test_role = generate_test_role(user_name, ['read:users!group=stuff'])
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')
    roles.remove_obj(app.db, objname=user_name, kind='users', rolename='user')
    app.db.commit()
    r = await api_request(
        app, 'users', fake_user, headers=auth_header(app.db, user_name)
    )
    assert r.status_code == 404
    # Consistency between no user and user not accessible
    assert r.json()['message'] == err_message


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


async def test_vertical_filter(app):
    user_name = 'lindsey'
    add_user(app.db, name=user_name)
    test_role = generate_test_role(user_name, ['read:users:name'])
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')
    roles.remove_obj(app.db, objname=user_name, kind='users', rolename='user')
    app.db.commit()

    r = await api_request(app, 'users', headers=auth_header(app.db, user_name))
    assert r.status_code == 200
    allowed_keys = {'name', 'kind'}
    assert set([key for user in r.json() for key in user.keys()]) == allowed_keys


async def test_stacked_vertical_filter(app):
    user_name = 'user'
    test_role = generate_test_role(
        user_name, ['read:users:activity', 'read:users:servers']
    )
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')
    roles.remove_obj(app.db, objname=user_name, kind='users', rolename='user')
    app.db.commit()

    r = await api_request(app, 'users', headers=auth_header(app.db, user_name))
    assert r.status_code == 200
    allowed_keys = {'name', 'kind', 'servers', 'last_activity'}
    result_model = set([key for user in r.json() for key in user.keys()])
    assert result_model == allowed_keys


async def test_cross_filter(app):
    user_name = 'abed'
    add_user(app.db, name=user_name)
    test_role = generate_test_role(
        user_name, ['read:users:activity', 'read:users!user=abed']
    )
    roles.add_role(app.db, test_role)
    roles.add_obj(app.db, objname=user_name, kind='users', rolename='test')
    roles.remove_obj(app.db, objname=user_name, kind='users', rolename='user')
    app.db.commit()
    new_users = {'britta', 'jeff', 'annie'}
    for new_user_name in new_users:
        add_user(app.db, name=new_user_name)
    app.db.commit()
    r = await api_request(app, 'users', headers=auth_header(app.db, user_name))
    assert r.status_code == 200
    restricted_keys = {'name', 'kind', 'last_activity'}
    key_in_full_model = 'created'
    for user in r.json():
        if user['name'] == user_name:
            assert key_in_full_model in user
        else:
            assert set(user.keys()) == restricted_keys
