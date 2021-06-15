"""Test scopes for API handlers"""
from unittest import mock

import pytest
from pytest import mark
from tornado import web
from tornado.httputil import HTTPServerRequest

from .. import orm
from .. import roles
from ..handlers import BaseHandler
from ..scopes import _check_scope_access
from ..scopes import _intersect_expanded_scopes
from ..scopes import get_scopes_for
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
    assert _check_scope_access(handler, 'read:users')
    assert _check_scope_access(handler, 'read:users', user='maeby')


def test_scope_check_not_present():
    handler = get_handler_with_scopes(['read:users!user=maeby'])
    assert _check_scope_access(handler, 'read:users')
    with pytest.raises(web.HTTPError):
        _check_scope_access(handler, 'read:users', user='gob')
    with pytest.raises(web.HTTPError):
        _check_scope_access(handler, 'read:users', user='gob', server='server')


def test_scope_filters():
    handler = get_handler_with_scopes(
        ['read:users', 'read:users!group=bluths', 'read:users!user=maeby']
    )
    assert _check_scope_access(handler, 'read:users', group='bluth')
    assert _check_scope_access(handler, 'read:users', user='maeby')


def test_scope_multiple_filters():
    handler = get_handler_with_scopes(['read:users!user=george_michael'])
    assert _check_scope_access(
        handler, 'read:users', user='george_michael', group='bluths'
    )


def test_scope_parse_server_name():
    handler = get_handler_with_scopes(
        ['servers!server=maeby/server1', 'read:users!user=maeby']
    )
    assert _check_scope_access(handler, 'servers', user='maeby', server='server1')


class MockAPIHandler:
    def __init__(self):
        self.expanded_scopes = {'users'}
        self.parsed_scopes = {}
        self.request = mock.Mock(spec=HTTPServerRequest)
        self.request.path = '/path'

    def set_scopes(self, *scopes):
        self.expanded_scopes = set(scopes)
        self.parsed_scopes = parse_scopes(self.expanded_scopes)

    @needs_scope('users')
    def user_thing(self, user_name):
        return True

    @needs_scope('servers')
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


@pytest.fixture
def mock_handler():
    obj = MockAPIHandler()
    return obj


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
        (['servers'], 'server_thing', ('user1', 'server_1'), True),
        (['servers'], 'server_thing', ('user1', ''), True),
        (['servers'], 'server_thing', ('user1', None), True),
        (
            ['servers!server=maeby/bluth'],
            'server_thing',
            ('maeby', 'bluth'),
            True,
        ),
        (['servers!server=maeby/bluth'], 'server_thing', ('gob', 'bluth'), False),
        (
            ['servers!server=maeby/bluth'],
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
def test_scope_method_access(mock_handler, scopes, method, arguments, is_allowed):
    mock_handler.current_user = mock.Mock(name=arguments[0])
    mock_handler.set_scopes(*scopes)
    api_call = getattr(mock_handler, method)
    if is_allowed:
        assert api_call(*arguments)
    else:
        with pytest.raises(web.HTTPError):
            api_call(*arguments)


def test_double_scoped_method_succeeds(mock_handler):
    mock_handler.current_user = mock.Mock(name='lucille')
    mock_handler.set_scopes('users', 'read:services')
    mock_handler.parsed_scopes = parse_scopes(mock_handler.expanded_scopes)
    assert mock_handler.secret_thing()


def test_double_scoped_method_denials(mock_handler):
    mock_handler.current_user = mock.Mock(name='lucille2')
    mock_handler.set_scopes('users', 'read:groups')
    with pytest.raises(web.HTTPError):
        mock_handler.secret_thing()


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
    roles.create_role(app.db, test_role)
    user = add_user(app.db, name=user_name)
    group_name = 'bluth'
    group = orm.Group.find(app.db, name=group_name)
    if not group:
        group = orm.Group(name=group_name)
        app.db.add(group)
    if in_group and user not in group.users:
        group.users.append(user)
    roles.update_roles(app.db, user, roles=['test'])
    roles.strip_role(app.db, user, 'user')
    app.db.commit()
    r = await api_request(
        app, 'users', user_name, headers=auth_header(app.db, user_name)
    )
    assert r.status_code == status_code
    app.db.delete(group)
    app.db.commit()


async def test_by_fake_user(app):
    user_name = 'shade'
    user = add_user(app.db, name=user_name)
    auth_ = auth_header(app.db, user_name)
    app.users.delete(user)
    app.db.commit()
    r = await api_request(app, 'users', headers=auth_)
    assert r.status_code == 403


err_message = "No access to resources or resources not found"


async def test_request_fake_user(app, create_user_with_scopes):
    fake_user = 'annyong'
    user = create_user_with_scopes('read:users!group=stuff')
    r = await api_request(
        app, 'users', fake_user, headers=auth_header(app.db, user.name)
    )
    assert r.status_code == 404
    # Consistency between no user and user not accessible
    assert r.json()['message'] == err_message


async def test_refuse_exceeding_token_permissions(
    app, create_user_with_scopes, create_temp_role
):
    user = create_user_with_scopes('self')
    user.new_api_token()
    create_temp_role(['admin:users'], 'exceeding_role')
    with pytest.raises(ValueError):
        roles.update_roles(app.db, entity=user.api_tokens[0], roles=['exceeding_role'])


async def test_exceeding_user_permissions(
    app, create_user_with_scopes, create_temp_role
):
    user = create_user_with_scopes('read:users:groups')
    api_token = user.new_api_token()
    orm_api_token = orm.APIToken.find(app.db, token=api_token)
    create_temp_role(['read:users'], 'reader_role')
    roles.grant_role(app.db, orm_api_token, rolename='reader_role')
    headers = {'Authorization': 'token %s' % api_token}
    r = await api_request(app, 'users', headers=headers)
    assert r.status_code == 200
    keys = {key for user in r.json() for key in user.keys()}
    assert 'groups' in keys
    assert 'last_activity' not in keys


async def test_user_service_separation(app, mockservice_url, create_temp_role):
    name = mockservice_url.name
    user = add_user(app.db, name=name)

    create_temp_role(['read:users'], 'reader_role')
    create_temp_role(['read:users:groups'], 'subreader_role')
    roles.update_roles(app.db, user, roles=['subreader_role'])
    roles.update_roles(app.db, mockservice_url.orm, roles=['reader_role'])
    user.roles.remove(orm.Role.find(app.db, name='user'))
    api_token = user.new_api_token()
    headers = {'Authorization': 'token %s' % api_token}
    r = await api_request(app, 'users', headers=headers)
    assert r.status_code == 200
    keys = {key for user in r.json() for key in user.keys()}
    assert 'groups' in keys
    assert 'last_activity' not in keys


async def test_request_user_outside_group(app, create_user_with_scopes):
    outside_user = 'hello'
    user = create_user_with_scopes('read:users!group=stuff')
    add_user(app.db, name=outside_user)
    r = await api_request(
        app, 'users', outside_user, headers=auth_header(app.db, user.name)
    )
    assert r.status_code == 404
    # Consistency between no user and user not accessible
    assert r.json()['message'] == err_message


async def test_user_filter(app, create_user_with_scopes):
    user = create_user_with_scopes(
        'read:users!user=lindsay', 'read:users!user=gob', 'read:users!user=oscar'
    )
    name_in_scope = {'lindsay', 'oscar', 'gob'}
    outside_scope = {'maeby', 'marta'}
    group_name = 'bluth'
    group = orm.Group.find(app.db, name=group_name)
    if not group:
        group = orm.Group(name=group_name)
        app.db.add(group)
    for name in name_in_scope | outside_scope:
        group_user = add_user(app.db, name=name)
        if name not in group.users:
            group.users.append(group_user)
    app.db.commit()
    r = await api_request(app, 'users', headers=auth_header(app.db, user.name))
    assert r.status_code == 200
    result_names = {user['name'] for user in r.json()}
    assert result_names == name_in_scope
    app.db.delete(group)
    app.db.commit()


async def test_service_filter(app, create_user_with_scopes):
    services = [
        {'name': 'cull_idle', 'api_token': 'some-token'},
        {'name': 'user_service', 'api_token': 'some-other-token'},
    ]
    for service in services:
        app.services.append(service)
    app.init_services()
    user = create_user_with_scopes('read:services!service=cull_idle')
    r = await api_request(app, 'services', headers=auth_header(app.db, user.name))
    assert r.status_code == 200
    service_names = set(r.json().keys())
    assert service_names == {'cull_idle'}


async def test_user_filter_with_group(app, create_user_with_scopes):
    group_name = 'sitwell'
    user1 = create_user_with_scopes(f'read:users!group={group_name}')
    user2 = create_user_with_scopes('self')
    external_user = create_user_with_scopes('self')
    name_set = {user1.name, user2.name}
    group = orm.Group.find(app.db, name=group_name)
    if not group:
        group = orm.Group(name=group_name)
        app.db.add(group)
    for user in {user1, user2}:
        group.users.append(user)
    app.db.commit()

    r = await api_request(app, 'users', headers=auth_header(app.db, user1.name))
    assert r.status_code == 200
    result_names = {user['name'] for user in r.json()}
    assert result_names == name_set
    assert external_user.name not in result_names
    app.db.delete(group)
    app.db.commit()


async def test_group_scope_filter(app, create_user_with_scopes):
    in_groups = {'sitwell', 'bluth'}
    out_groups = {'austero'}
    user = create_user_with_scopes(
        *(f'read:groups!group={group}' for group in in_groups)
    )
    for group_name in in_groups | out_groups:
        group = orm.Group.find(app.db, name=group_name)
        if not group:
            group = orm.Group(name=group_name)
            app.db.add(group)
    app.db.commit()
    r = await api_request(app, 'groups', headers=auth_header(app.db, user.name))
    assert r.status_code == 200
    result_names = {user['name'] for user in r.json()}
    assert result_names == in_groups
    for group_name in in_groups | out_groups:
        group = orm.Group.find(app.db, name=group_name)
        app.db.delete(group)
    app.db.commit()


async def test_vertical_filter(app, create_user_with_scopes):
    user = create_user_with_scopes('read:users:name')
    r = await api_request(app, 'users', headers=auth_header(app.db, user.name))
    assert r.status_code == 200
    allowed_keys = {'name', 'kind', 'admin'}
    assert set([key for user in r.json() for key in user.keys()]) == allowed_keys


async def test_stacked_vertical_filter(app, create_user_with_scopes):
    user = create_user_with_scopes('read:users:activity', 'read:users:groups')
    r = await api_request(app, 'users', headers=auth_header(app.db, user.name))
    assert r.status_code == 200
    allowed_keys = {'name', 'kind', 'groups', 'last_activity'}
    result_model = set([key for user in r.json() for key in user.keys()])
    assert result_model == allowed_keys


async def test_cross_filter(app, create_user_with_scopes):
    user = create_user_with_scopes('read:users:activity', 'self')
    new_users = {'britta', 'jeff', 'annie'}
    for new_user_name in new_users:
        add_user(app.db, name=new_user_name)
    app.db.commit()
    r = await api_request(app, 'users', headers=auth_header(app.db, user.name))
    assert r.status_code == 200
    restricted_keys = {'name', 'kind', 'last_activity'}
    key_in_full_model = 'created'
    for model_user in r.json():
        if model_user['name'] == user.name:
            assert key_in_full_model in model_user
        else:
            assert set(model_user.keys()) == restricted_keys


@mark.parametrize(
    "kind, has_user_scopes",
    [
        ('users', True),
        ('services', False),
    ],
)
async def test_metascope_self_expansion(
    app, kind, has_user_scopes, create_user_with_scopes, create_service_with_scopes
):
    if kind == 'users':
        orm_obj = create_user_with_scopes('self').orm_user
    else:
        orm_obj = create_service_with_scopes('self')
    # test expansion of user/service scopes
    scopes = roles.expand_roles_to_scopes(orm_obj)
    assert bool(scopes) == has_user_scopes

    # test expansion of token scopes
    orm_obj.new_api_token()
    token_scopes = get_scopes_for(orm_obj.api_tokens[0])
    assert bool(token_scopes) == has_user_scopes


async def test_metascope_all_expansion(app, create_user_with_scopes):
    user = create_user_with_scopes('self')
    user.new_api_token()
    token = user.api_tokens[0]
    # Check 'all' expansion
    token_scope_set = get_scopes_for(token)
    user_scope_set = get_scopes_for(user)
    assert user_scope_set == token_scope_set

    # Check no roles means no permissions
    token.roles.clear()
    app.db.commit()
    token_scope_set = get_scopes_for(token)
    assert not token_scope_set


@mark.parametrize(
    "scopes, can_stop ,num_servers, keys_in, keys_out",
    [
        (['read:servers!user=almond'], False, 2, {'name'}, {'state'}),
        (['admin:users', 'read:users'], False, 0, set(), set()),
        (
            ['read:servers!group=nuts', 'servers'],
            True,
            2,
            {'name'},
            {'state'},
        ),
        (
            ['admin:server_state', 'read:servers'],
            False,
            2,
            {'name', 'state'},
            set(),
        ),
        (
            [
                'read:servers!server=almond/bianca',
                'admin:server_state!server=almond/bianca',
            ],
            False,
            1,
            {'name', 'state'},
            set(),
        ),
    ],
)
async def test_server_state_access(
    app,
    create_user_with_scopes,
    create_service_with_scopes,
    scopes,
    can_stop,
    num_servers,
    keys_in,
    keys_out,
):
    with mock.patch.dict(
        app.tornado_settings,
        {'allow_named_servers': True, 'named_server_limit_per_user': 2},
    ):
        user = create_user_with_scopes('self', name='almond')
        group_name = 'nuts'
        group = orm.Group.find(app.db, name=group_name)
        if not group:
            group = orm.Group(name=group_name)
            app.db.add(group)
        group.users.append(user)
        app.db.commit()
        server_names = ['bianca', 'terry']
        for server_name in server_names:
            await api_request(
                app, 'users', user.name, 'servers', server_name, method='post'
            )
        service = create_service_with_scopes(*scopes)
        api_token = service.new_api_token()
        headers = {'Authorization': 'token %s' % api_token}
        r = await api_request(app, 'users', user.name, headers=headers)
        r.raise_for_status()
        user_model = r.json()
        if num_servers:
            assert 'servers' in user_model
            server_models = user_model['servers']
            assert len(server_models) == num_servers
            for server, server_model in server_models.items():
                assert keys_in.issubset(server_model)
                assert keys_out.isdisjoint(server_model)
        else:
            assert 'servers' not in user_model
        r = await api_request(
            app,
            'users',
            user.name,
            'servers',
            server_names[0],
            method='delete',
            headers=headers,
        )
        if can_stop:
            assert r.status_code == 204
        else:
            assert r.status_code == 403
        app.db.delete(group)
        app.db.commit()


@mark.parametrize(
    "name, user_scopes, token_scopes, intersection_scopes",
    [
        (
            'no_filter',
            ['users:activity'],
            ['users:activity'],
            {'users:activity', 'read:users:activity'},
        ),
        (
            'valid_own_filter',
            ['read:users:activity'],
            ['read:users:activity!user'],
            {'read:users:activity!user=temp_user_1'},
        ),
        (
            'valid_other_filter',
            ['read:users:activity'],
            ['read:users:activity!user=otheruser'],
            {'read:users:activity!user=otheruser'},
        ),
        (
            'no_filter_owner_filter',
            ['read:users:activity!user'],
            ['read:users:activity'],
            {'read:users:activity!user=temp_user_1'},
        ),
        (
            'valid_own_filter',
            ['read:users:activity!user'],
            ['read:users:activity!user'],
            {'read:users:activity!user=temp_user_1'},
        ),
        (
            'invalid_filter',
            ['read:users:activity!user'],
            ['read:users:activity!user=otheruser'],
            set(),
        ),
        (
            'subscopes_cross_filter',
            ['users!user=x'],
            ['read:users:name'],
            {'read:users:name!user=x'},
        ),
        (
            'multiple_user_filter',
            ['users!user=x', 'users!user=y'],
            ['read:users:name!user=x'],
            {'read:users:name!user=x'},
        ),
        (
            'no_intersection_group_user',
            ['users!group=y'],
            ['users!user=x'],
            set(),
        ),
        (
            'no_intersection_user_server',
            ['servers!user=y'],
            ['servers!server=x'],
            set(),
        ),
        (
            'users_and_groups_both',
            ['users!group=x', 'users!user=y'],
            ['read:users:name!group=x', 'read:users!user=y'],
            {
                'read:users:name!group=x',
                'read:users!user=y',
                'read:users:name!user=y',
                'read:users:groups!user=y',
                'read:users:activity!user=y',
            },
        ),
        (
            'users_and_groups_user_only',
            ['users!group=x', 'users!user=y'],
            ['read:users:name!group=z', 'read:users!user=y'],
            {
                'read:users!user=y',
                'read:users:name!user=y',
                'read:users:groups!user=y',
                'read:users:activity!user=y',
            },
        ),
    ],
)
async def test_resolve_token_permissions(
    app,
    create_user_with_scopes,
    create_temp_role,
    name,
    user_scopes,
    token_scopes,
    intersection_scopes,
):
    orm_user = create_user_with_scopes(*user_scopes).orm_user
    create_temp_role(token_scopes, 'active-posting')
    api_token = orm_user.new_api_token(roles=['active-posting'])
    orm_api_token = orm.APIToken.find(app.db, token=api_token)

    # get expanded !user filter scopes for check
    user_scopes = roles.expand_roles_to_scopes(orm_user)
    token_scopes = roles.expand_roles_to_scopes(orm_api_token)

    token_retained_scopes = get_scopes_for(orm_api_token)

    assert token_retained_scopes == intersection_scopes


@mark.parametrize(
    "scopes, model_keys",
    [
        (
            {'read:services'},
            {
                'command',
                'name',
                'kind',
                'info',
                'display',
                'pid',
                'admin',
                'prefix',
                'url',
            },
        ),
        (
            {'read:roles:services', 'read:services:name'},
            {'name', 'kind', 'roles', 'admin'},
        ),
        ({'read:services:name'}, {'name', 'kind', 'admin'}),
    ],
)
async def test_service_model_filtering(
    app, scopes, model_keys, create_user_with_scopes, create_service_with_scopes
):
    user = create_user_with_scopes(*scopes, name='teddy')
    service = create_service_with_scopes()
    r = await api_request(
        app, 'services', service.name, headers=auth_header(app.db, user.name)
    )
    assert r.status_code == 200
    assert model_keys == r.json().keys()


@mark.parametrize(
    "scopes, model_keys",
    [
        (
            {'read:groups'},
            {
                'name',
                'kind',
                'users',
            },
        ),
        (
            {'read:roles:groups', 'read:groups:name'},
            {'name', 'kind', 'roles'},
        ),
        ({'read:groups:name'}, {'name', 'kind'}),
    ],
)
async def test_group_model_filtering(
    app, scopes, model_keys, create_user_with_scopes, create_service_with_scopes
):
    user = create_user_with_scopes(*scopes, name='teddy')
    group_name = 'baker_street'
    group = orm.Group.find(app.db, name=group_name)
    if not group:
        group = orm.Group(name=group_name)
        app.db.add(group)
        app.db.commit()
    r = await api_request(
        app, 'groups', group_name, headers=auth_header(app.db, user.name)
    )
    assert r.status_code == 200
    assert model_keys == r.json().keys()
    app.db.delete(group)
    app.db.commit()


async def test_roles_access(app, create_service_with_scopes, create_user_with_scopes):
    user = add_user(app.db, name='miranda')
    read_user = create_user_with_scopes('read:roles:users')
    r = await api_request(
        app, 'users', user.name, headers=auth_header(app.db, read_user.name)
    )
    assert r.status_code == 200
    model_keys = {'kind', 'name', 'roles', 'admin'}
    assert model_keys == r.json().keys()


@pytest.mark.parametrize(
    "left, right, expected, should_warn",
    [
        (set(), set(), set(), False),
        (set(), set(["users"]), set(), False),
        # no warning if users and groups only on the same side
        (
            set(["users!user=x", "users!group=y"]),
            set([]),
            set([]),
            False,
        ),
        # no warning if users are on both sizes
        (
            set(["users!user=x", "users!user=y", "users!group=y"]),
            set(["users!user=x"]),
            set(["users!user=x"]),
            False,
        ),
        # no warning if users and groups are both defined
        # on both sides
        (
            set(["users!user=x", "users!group=y"]),
            set(["users!user=x", "users!group=y", "users!user=z"]),
            set(["users!user=x", "users!group=y"]),
            False,
        ),
        # warn if there's a user on one side and a group on the other
        # which *may* intersect
        (
            set(["users!group=y", "users!user=z"]),
            set(["users!user=x"]),
            set([]),
            True,
        ),
        # same for group->server
        (
            set(["users!group=y", "users!user=z"]),
            set(["users!server=x/y"]),
            set([]),
            True,
        ),
        # this one actually shouldn't warn because server=x/y is under user=x,
        # but we don't need to overcomplicate things just for a warning
        (
            set(["users!group=y", "users!user=x"]),
            set(["users!server=x/y"]),
            set(["users!server=x/y"]),
            True,
        ),
        # resolves server under user, without warning
        (
            set(["read:servers!user=abc"]),
            set(["read:servers!server=abc/xyz"]),
            set(["read:servers!server=abc/xyz"]),
            False,
        ),
        # user->server, no match
        (
            set(["read:servers!user=abc"]),
            set(["read:servers!server=abcd/xyz"]),
            set([]),
            False,
        ),
    ],
)
def test_intersect_expanded_scopes(left, right, expected, should_warn, recwarn):
    # run every test in both directions, to ensure symmetry of the inputs
    for a, b in [(left, right), (right, left)]:
        intersection = _intersect_expanded_scopes(set(left), set(right))
        assert intersection == set(expected)

    if should_warn:
        assert len(recwarn) == 1
    else:
        assert len(recwarn) == 0


@pytest.mark.parametrize(
    "left, right, expected, groups",
    [
        (
            ["users!group=gx"],
            ["users!user=ux"],
            ["users!user=ux"],
            {"gx": ["ux"]},
        ),
        (
            ["read:users!group=gx"],
            ["read:users!user=nosuchuser"],
            [],
            {},
        ),
        (
            ["read:users!group=gx"],
            ["read:users!server=nosuchuser/server"],
            [],
            {},
        ),
        (
            ["read:users!group=gx"],
            ["read:users!server=ux/server"],
            ["read:users!server=ux/server"],
            {"gx": ["ux"]},
        ),
        (
            ["read:users!group=gx"],
            ["read:users!server=ux/server", "read:users!user=uy"],
            ["read:users!server=ux/server"],
            {"gx": ["ux"], "gy": ["uy"]},
        ),
        (
            ["read:users!group=gy"],
            ["read:users!server=ux/server", "read:users!user=uy"],
            ["read:users!user=uy"],
            {"gx": ["ux"], "gy": ["uy"]},
        ),
    ],
)
def test_intersect_groups(request, db, left, right, expected, groups):
    if isinstance(left, str):
        left = set([left])
    if isinstance(right, str):
        right = set([right])

    # if we have a db connection, we can actually resolve
    created = []
    for groupname, members in groups.items():
        group = orm.Group.find(db, name=groupname)
        if not group:
            group = orm.Group(name=groupname)
            db.add(group)
            created.append(group)
            db.commit()
        for username in members:
            user = orm.User.find(db, name=username)
            if user is None:
                user = orm.User(name=username)
                db.add(user)
                created.append(user)
            user.groups.append(group)
    db.commit()

    def _cleanup():
        for obj in created:
            db.delete(obj)
        db.commit()

    request.addfinalizer(_cleanup)

    # run every test in both directions, to ensure symmetry of the inputs
    for a, b in [(left, right), (right, left)]:
        intersection = _intersect_expanded_scopes(set(left), set(right), db)
        assert intersection == set(expected)
