"""Test roles"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import os

import pytest
from pytest import mark
from tornado.log import app_log

from .. import orm
from .. import roles
from ..scopes import get_scopes_for
from ..scopes import scope_definitions
from ..utils import utcnow
from .mocking import MockHub
from .utils import add_user
from .utils import api_request


@mark.role
def test_orm_roles(db):
    """Test orm roles setup"""
    user_role = orm.Role.find(db, name='user')
    token_role = orm.Role.find(db, name='token')
    service_role = orm.Role.find(db, name='service')
    if not user_role:
        user_role = orm.Role(name='user', scopes=['self'])
        db.add(user_role)
    if not token_role:
        token_role = orm.Role(name='token', scopes=['all'])
        db.add(token_role)
    if not service_role:
        service_role = orm.Role(name='service', scopes=[])
        db.add(service_role)
    db.commit()

    group_role = orm.Role(name='group', scopes=['read:users'])
    db.add(group_role)
    db.commit()

    user = orm.User(name='falafel')
    db.add(user)
    db.commit()

    service = orm.Service(name='kebab')
    db.add(service)
    db.commit()

    group = orm.Group(name='fast-food')
    db.add(group)
    db.commit()

    assert user_role.users == []
    assert user_role.services == []
    assert user_role.groups == []
    assert service_role.users == []
    assert service_role.services == []
    assert service_role.groups == []
    assert user.roles == []
    assert service.roles == []
    assert group.roles == []

    user_role.users.append(user)
    service_role.services.append(service)
    group_role.groups.append(group)
    db.commit()
    assert user_role.users == [user]
    assert user.roles == [user_role]
    assert service_role.services == [service]
    assert service.roles == [service_role]
    assert group_role.groups == [group]
    assert group.roles == [group_role]

    # check token creation without specifying its role
    # assigns it the default 'token' role
    token = user.new_api_token()
    user_token = orm.APIToken.find(db, token=token)
    assert user_token in token_role.tokens
    assert token_role in user_token.roles

    # check creating token with a specific role
    token = service.new_api_token(roles=['service'])
    service_token = orm.APIToken.find(db, token=token)
    assert service_token in service_role.tokens
    assert service_role in service_token.roles

    # check deleting user removes the user and the token from roles
    db.delete(user)
    db.commit()
    assert user_role.users == []
    assert user_token not in token_role.tokens
    # check deleting the service token removes it from 'service' role
    db.delete(service_token)
    db.commit()
    assert service_token not in service_role.tokens
    # check deleting the service_role removes it from service.roles
    db.delete(service_role)
    db.commit()
    assert service.roles == []
    # check deleting the group removes it from group_roles
    db.delete(group)
    db.commit()
    assert group_role.groups == []

    # clean up db
    db.delete(service)
    db.delete(group_role)
    db.commit()


@mark.role
def test_orm_roles_delete_cascade(db):
    """Orm roles cascade"""
    user1 = orm.User(name='user1')
    user2 = orm.User(name='user2')
    role1 = orm.Role(name='role1')
    role2 = orm.Role(name='role2')
    db.add(user1)
    db.add(user2)
    db.add(role1)
    db.add(role2)
    db.commit()
    # add user to role via user.roles
    user1.roles.append(role1)
    db.commit()
    assert user1 in role1.users
    assert role1 in user1.roles

    # add user to role via roles.users
    role1.users.append(user2)
    db.commit()
    assert user2 in role1.users
    assert role1 in user2.roles

    # fill role2 and check role1 again
    role2.users.append(user1)
    role2.users.append(user2)
    db.commit()
    assert user1 in role1.users
    assert user2 in role1.users
    assert user1 in role2.users
    assert user2 in role2.users
    assert role1 in user1.roles
    assert role1 in user2.roles
    assert role2 in user1.roles
    assert role2 in user2.roles

    # now start deleting
    # 1. remove role via user.roles
    user1.roles.remove(role2)
    db.commit()
    assert user1 not in role2.users
    assert role2 not in user1.roles

    # 2. remove user via role.users
    role1.users.remove(user2)
    db.commit()
    assert user2 not in role1.users
    assert role1 not in user2.roles

    # 3. delete role object
    db.delete(role2)
    db.commit()
    assert role2 not in user1.roles
    assert role2 not in user2.roles

    # 4. delete user object
    db.delete(user1)
    db.delete(user2)
    db.commit()
    assert user1 not in role1.users


@mark.role
@mark.parametrize(
    "scopes, subscopes",
    [
        (
            ['admin:users'],
            {
                'admin:users',
                'admin:auth_state',
                'users',
                'read:users',
                'users:activity',
                'read:users:name',
                'read:users:groups',
                'read:roles:users',
                'read:users:activity',
            },
        ),
        (
            ['users'],
            {
                'users',
                'read:users',
                'users:activity',
                'read:users:name',
                'read:users:groups',
                'read:users:activity',
            },
        ),
        (
            ['read:users'],
            {
                'read:users',
                'read:users:name',
                'read:users:groups',
                'read:users:activity',
            },
        ),
        (['read:servers'], {'read:servers', 'read:users:name'}),
        (
            ['admin:groups'],
            {
                'admin:groups',
                'groups',
                'read:groups',
                'read:roles:groups',
                'read:groups:name',
            },
        ),
        (
            ['admin:groups', 'read:servers'],
            {
                'admin:groups',
                'groups',
                'read:groups',
                'read:roles:groups',
                'read:groups:name',
                'read:servers',
                'read:users:name',
            },
        ),
        (
            ['tokens!group=hobbits'],
            {'tokens!group=hobbits', 'read:tokens!group=hobbits'},
        ),
    ],
)
def test_get_subscopes(db, scopes, subscopes):
    """Test role scopes expansion into their subscopes"""
    roles.create_role(db, {'name': 'testing_scopes', 'scopes': scopes})
    role = orm.Role.find(db, name='testing_scopes')
    response = roles._get_subscopes(role)
    assert response == subscopes
    db.delete(role)


@mark.role
async def test_load_default_roles(tmpdir, request):
    """Test loading default roles in app.py"""
    kwargs = {}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db
    await hub.init_role_creation()
    # test default roles loaded to database
    default_roles = roles.get_default_roles()
    for role in default_roles:
        assert orm.Role.find(db, role['name']) is not None


@mark.role
@mark.parametrize(
    "role, role_def, response_type, response",
    [
        (
            'new-role',
            {
                'name': 'new-role',
                'description': 'Some description',
                'scopes': ['groups'],
            },
            'info',
            app_log.info('Role new-role added to database'),
        ),
        (
            'the-same-role',
            {
                'name': 'new-role',
                'description': 'Some description',
                'scopes': ['groups'],
            },
            'no-log',
            None,
        ),
        ('no_name', {'scopes': ['users']}, 'error', KeyError),
        (
            'no_scopes',
            {'name': 'no-permissions'},
            'warning',
            app_log.warning('Warning: New defined role no-permissions has no scopes'),
        ),
        (
            'admin',
            {'name': 'admin', 'scopes': ['admin:users']},
            'error',
            ValueError,
        ),
        (
            'admin',
            {'name': 'admin', 'description': 'New description'},
            'error',
            ValueError,
        ),
        (
            'user',
            {'name': 'user', 'scopes': ['read:users:name']},
            'info',
            app_log.info('Role user scopes attribute has been changed'),
        ),
        # rewrite the user role back to 'default'
        (
            'user',
            {'name': 'user', 'scopes': ['self']},
            'info',
            app_log.info('Role user scopes attribute has been changed'),
        ),
    ],
)
async def test_creating_roles(app, role, role_def, response_type, response):
    """Test raising errors and warnings when creating/modifying roles"""

    db = app.db

    if response_type == 'error':
        with pytest.raises(response):
            roles.create_role(db, role_def)

    elif response_type == 'warning' or response_type == 'info':
        with pytest.warns(response):
            roles.create_role(db, role_def)
        # check the role has been created/modified
        role = orm.Role.find(db, role_def['name'])
        assert role is not None
        if 'description' in role_def.keys():
            assert role.description == role_def['description']
        if 'scopes' in role_def.keys():
            assert role.scopes == role_def['scopes']

    # make sure no warnings/info logged when the role exists and its definition hasn't been changed
    elif response_type == 'no-log':
        with pytest.warns(response) as record:
            roles.create_role(db, role_def)
        assert not record.list
        role = orm.Role.find(db, role_def['name'])
        assert role is not None


@mark.role
@mark.parametrize(
    "role_type, rolename, response_type, response",
    [
        (
            'existing',
            'test-role1',
            'info',
            app_log.info('Role user scopes attribute has been changed'),
        ),
        ('non-existing', 'test-role2', 'error', NameError),
        ('default', 'user', 'error', ValueError),
    ],
)
async def test_delete_roles(db, role_type, rolename, response_type, response):
    """Test raising errors and info when deleting roles"""

    if response_type == 'info':
        # add the role to db
        test_role = orm.Role(name=rolename)
        db.add(test_role)
        db.commit()
        check_role = orm.Role.find(db, rolename)
        assert check_role is not None
        # check the role is deleted and info raised
        with pytest.warns(response):
            roles.delete_role(db, rolename)
        check_role = orm.Role.find(db, rolename)
        assert check_role is None

    elif response_type == 'error':
        with pytest.raises(response):
            roles.delete_role(db, rolename)


@mark.role
@mark.parametrize(
    "role, response",
    [
        (
            {
                'name': 'test-scopes-1',
                'scopes': [
                    'users',
                    'users!user=charlie',
                    'admin:groups',
                    'read:tokens',
                ],
            },
            'existing',
        ),
        ({'name': 'test-scopes-2', 'scopes': ['uses']}, NameError),
        ({'name': 'test-scopes-3', 'scopes': ['users:activities']}, NameError),
        ({'name': 'test-scopes-4', 'scopes': ['groups!goup=class-A']}, NameError),
    ],
)
async def test_scope_existence(tmpdir, request, role, response):
    """Test checking of scopes provided in role definitions"""
    kwargs = {'load_roles': [role]}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db

    if response == 'existing':
        roles.create_role(db, role)
        added_role = orm.Role.find(db, role['name'])
        assert added_role is not None
        assert added_role.scopes == role['scopes']

    elif response == NameError:
        with pytest.raises(response):
            roles.create_role(db, role)
        added_role = orm.Role.find(db, role['name'])
        assert added_role is None

    # delete the tested roles
    if added_role:
        roles.delete_role(db, added_role.name)


@mark.role
async def test_load_roles_users(tmpdir, request):
    """Test loading predefined roles for users in app.py"""
    roles_to_load = [
        {
            'name': 'teacher',
            'description': 'Access users information, servers and groups without create/delete privileges',
            'scopes': ['users', 'groups'],
            'users': ['cyclops', 'gandalf'],
        },
    ]
    kwargs = {'load_roles': roles_to_load}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db
    hub.authenticator.admin_users = ['admin']
    hub.authenticator.allowed_users = ['cyclops', 'gandalf', 'bilbo', 'gargamel']
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    admin_role = orm.Role.find(db, 'admin')
    user_role = orm.Role.find(db, 'user')
    # test if every user has a role (and no duplicates)
    # and admins have admin role
    for user in db.query(orm.User):
        assert len(user.roles) > 0
        assert len(user.roles) == len(set(user.roles))
        if user.admin:
            assert admin_role in user.roles
            assert user_role in user.roles

    # test if predefined roles loaded and assigned
    teacher_role = orm.Role.find(db, name='teacher')
    assert teacher_role is not None
    gandalf_user = orm.User.find(db, name='gandalf')
    assert teacher_role in gandalf_user.roles
    cyclops_user = orm.User.find(db, name='cyclops')
    assert teacher_role in cyclops_user.roles

    # delete the test roles
    for role in roles_to_load:
        roles.delete_role(db, role['name'])


@mark.role
async def test_load_roles_services(tmpdir, request):
    services = [
        {'name': 'idle-culler', 'api_token': 'some-token'},
        {'name': 'user_service', 'api_token': 'some-other-token'},
        {'name': 'admin_service', 'api_token': 'secret-token'},
    ]
    service_tokens = {
        'some-token': 'idle-culler',
        'some-other-token': 'user_service',
        'secret-token': 'admin_service',
    }
    roles_to_load = [
        {
            'name': 'idle-culler',
            'description': 'Cull idle servers',
            'scopes': [
                'read:users:name',
                'read:users:activity',
                'read:servers',
                'servers',
            ],
            'services': ['idle-culler'],
        },
    ]
    kwargs = {
        'load_roles': roles_to_load,
        'services': services,
        'service_tokens': service_tokens,
    }
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db
    await hub.init_role_creation()
    await hub.init_api_tokens()
    # make 'admin_service' admin
    admin_service = orm.Service.find(db, 'admin_service')
    admin_service.admin = True
    db.commit()
    await hub.init_role_assignment()
    # test if every service has a role (and no duplicates)
    admin_role = orm.Role.find(db, name='admin')
    user_role = orm.Role.find(db, name='user')

    # test if predefined roles loaded and assigned
    culler_role = orm.Role.find(db, name='idle-culler')
    culler_service = orm.Service.find(db, name='idle-culler')
    assert culler_service.roles == [culler_role]
    user_service = orm.Service.find(db, name='user_service')
    assert not user_service.roles
    assert admin_service.roles == [admin_role]

    # delete the test services
    for service in db.query(orm.Service):
        db.delete(service)
    db.commit()

    # delete the test tokens
    for token in db.query(orm.APIToken):
        db.delete(token)
    db.commit()

    # delete the test roles
    for role in roles_to_load:
        roles.delete_role(db, role['name'])


@mark.role
async def test_load_roles_groups(tmpdir, request):
    """Test loading predefined roles for groups in app.py"""
    groups_to_load = {
        'group1': ['gandalf'],
        'group2': ['bilbo', 'gargamel'],
        'group3': ['cyclops'],
    }
    roles_to_load = [
        {
            'name': 'assistant',
            'description': 'Access users information only',
            'scopes': ['read:users'],
            'groups': ['group2'],
        },
        {
            'name': 'head',
            'description': 'Whole user access',
            'scopes': ['users', 'admin:users'],
            'groups': ['group3'],
        },
    ]
    kwargs = {'load_groups': groups_to_load, 'load_roles': roles_to_load}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db
    await hub.init_role_creation()
    await hub.init_groups()
    await hub.init_role_assignment()

    assist_role = orm.Role.find(db, name='assistant')
    head_role = orm.Role.find(db, name='head')

    group1 = orm.Group.find(db, name='group1')
    group2 = orm.Group.find(db, name='group2')
    group3 = orm.Group.find(db, name='group3')

    # test group roles
    assert group1.roles == []
    assert group2 in assist_role.groups
    assert group3 in head_role.groups

    # delete the test roles
    for role in roles_to_load:
        roles.delete_role(db, role['name'])


@mark.role
async def test_load_roles_user_tokens(tmpdir, request):
    user_tokens = {
        'secret-token': 'cyclops',
        'secrety-token': 'gandalf',
        'super-secret-token': 'admin',
    }
    roles_to_load = [
        {
            'name': 'reader',
            'description': 'Read all users models',
            'scopes': ['read:users'],
        },
    ]
    kwargs = {
        'load_roles': roles_to_load,
        'api_tokens': user_tokens,
    }
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db
    hub.authenticator.admin_users = ['admin']
    hub.authenticator.allowed_users = ['cyclops', 'gandalf']
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_api_tokens()
    await hub.init_role_assignment()
    # test if all other tokens have default 'user' role
    token_role = orm.Role.find(db, 'token')
    secret_token = orm.APIToken.find(db, 'secret-token')
    assert token_role in secret_token.roles
    secrety_token = orm.APIToken.find(db, 'secrety-token')
    assert token_role in secrety_token.roles

    # delete the test tokens
    for token in db.query(orm.APIToken):
        db.delete(token)
    db.commit()

    # delete the test roles
    for role in roles_to_load:
        roles.delete_role(db, role['name'])


@mark.role
@mark.parametrize(
    "headers, rolename, scopes, status",
    [
        # no role requested - gets default 'token' role
        ({}, None, None, 200),
        # role scopes within the user's default 'user' role
        ({}, 'self-reader', ['read:users'], 200),
        # role scopes outside of the user's role but within the group's role scopes of which the user is a member
        ({}, 'groups-reader', ['read:groups'], 200),
        # non-existing role request
        ({}, 'non-existing', [], 404),
        # role scopes outside of both user's role and group's role scopes
        ({}, 'users-creator', ['admin:users'], 403),
    ],
)
async def test_get_new_token_via_api(app, headers, rolename, scopes, status):
    """Test requesting a token via API with and without roles"""

    user = add_user(app.db, app, name='user')
    if rolename and rolename != 'non-existing':
        roles.create_role(app.db, {'name': rolename, 'scopes': scopes})
        if rolename == 'groups-reader':
            # add role for a group
            roles.create_role(app.db, {'name': 'group-role', 'scopes': ['groups']})
            # create a group and add the user and group_role
            group = orm.Group.find(app.db, 'test-group')
            if not group:
                group = orm.Group(name='test-group')
                app.db.add(group)
                group_role = orm.Role.find(app.db, 'group-role')
                group.roles.append(group_role)
                user.groups.append(group)
                app.db.commit()
    if rolename:
        body = json.dumps({'roles': [rolename]})
    else:
        body = ''
    # request a new token
    r = await api_request(
        app, 'users/user/tokens', method='post', headers=headers, data=body
    )
    assert r.status_code == status
    if status != 200:
        return
    # check the new-token reply for roles
    reply = r.json()
    assert 'token' in reply
    assert reply['user'] == user.name
    if not rolename:
        assert reply['roles'] == ['token']
    else:
        assert reply['roles'] == [rolename]
    token_id = reply['id']

    # delete the token
    r = await api_request(app, 'users/user/tokens', token_id, method='delete')
    assert r.status_code == 204
    # verify deletion
    r = await api_request(app, 'users/user/tokens', token_id)
    assert r.status_code == 404


@mark.role
@mark.parametrize(
    "kind, has_user_scopes",
    [
        ('users', True),
        ('services', False),
    ],
)
async def test_self_expansion(app, kind, has_user_scopes):
    Class = orm.get_class(kind)
    orm_obj = Class(name=f'test_{kind}')
    app.db.add(orm_obj)
    app.db.commit()
    test_role = orm.Role(name='test_role', scopes=['self'])
    orm_obj.roles.append(test_role)
    # test expansion of user/service scopes
    scopes = roles.expand_roles_to_scopes(orm_obj)
    assert bool(scopes) == has_user_scopes
    if kind == 'users':
        for scope in scopes:
            assert scope.endswith(f"!user={orm_obj.name}")
            base_scope = scope.split("!", 1)[0]
            assert base_scope in scope_definitions

    # test expansion of token scopes
    orm_obj.new_api_token()
    print(orm_obj.api_tokens[0])
    token_scopes = get_scopes_for(orm_obj.api_tokens[0])
    print(token_scopes)
    assert bool(token_scopes) == has_user_scopes
    app.db.delete(orm_obj)
    app.db.delete(test_role)


@mark.role
@mark.parametrize(
    "scope_list, kind, test_for_token",
    [
        (['users:activity!user'], 'users', False),
        (['users:activity!user', 'read:users'], 'users', False),
        (['users:activity!user=otheruser', 'read:users'], 'users', False),
        (['users:activity!user'], 'users', True),
        (['users:activity!user=otheruser', 'groups'], 'users', True),
    ],
)
async def test_user_filter_expansion(app, scope_list, kind, test_for_token):
    Class = orm.get_class(kind)
    orm_obj = Class(name=f'test_{kind}')
    app.db.add(orm_obj)
    app.db.commit()

    test_role = orm.Role(name='test_role', scopes=scope_list)
    orm_obj.roles.append(test_role)

    if test_for_token:
        token = orm_obj.new_api_token(roles=['test_role'])
        orm_token = orm.APIToken.find(app.db, token)
        expanded_scopes = roles.expand_roles_to_scopes(orm_token)
    else:
        expanded_scopes = roles.expand_roles_to_scopes(orm_obj)

    for scope in scope_list:
        base, _, filter = scope.partition('!')
        for ex_scope in expanded_scopes:
            ex_base, ex__, ex_filter = ex_scope.partition('!')
            # check that the filter has been expanded to include the username if '!user' filter
            if scope in ex_scope and filter == 'user':
                assert ex_filter == f'{filter}={orm_obj.name}'
            # make sure the filter has been left unchanged if other filter provided
            elif scope in ex_scope and '=' in filter:
                assert ex_filter == filter

    app.db.delete(orm_obj)
    app.db.delete(test_role)


async def test_large_filter_expansion(app, create_temp_role, create_user_with_scopes):
    scope_list = roles.expand_self_scope('==')
    # Mimic the role 'self' based on '!user' filter for tokens
    scope_list = [scope.rstrip("=") for scope in scope_list]
    filtered_role = create_temp_role(scope_list)
    user = create_user_with_scopes('self')
    user.new_api_token(roles=[filtered_role.name])
    user.new_api_token(roles=['token'])
    manual_scope_set = get_scopes_for(user.api_tokens[0])
    auto_scope_set = get_scopes_for(user.api_tokens[1])
    assert manual_scope_set == auto_scope_set


@mark.role
@mark.parametrize(
    "name, valid",
    [
        ('abc', True),
        ('group', True),
        ("a-pretty-long-name-with-123", True),
        ("0-abc", False),  # starts with number
        ("role-", False),  # ends with -
        ("has-Uppercase", False),  # Uppercase
        ("a" * 256, False),  # too long
        ("has space", False),  # space is illegal
    ],
)
async def test_valid_names(name, valid):
    if valid:
        assert roles._validate_role_name(name)
    else:
        with pytest.raises(ValueError):
            roles._validate_role_name(name)


@mark.role
async def test_server_token_role(app):
    user = add_user(app.db, app, name='test_user')
    assert user.api_tokens == []
    spawner = user.spawner
    spawner.cmd = ['jupyterhub-singleuser']
    await user.spawn()

    server_token = spawner.api_token
    orm_server_token = orm.APIToken.find(app.db, server_token)
    assert orm_server_token

    server_role = orm.Role.find(app.db, 'server')
    token_role = orm.Role.find(app.db, 'token')
    assert server_role in orm_server_token.roles
    assert token_role not in orm_server_token.roles

    assert orm_server_token.user.name == user.name
    assert user.api_tokens == [orm_server_token]

    await user.stop()


@mark.role
@mark.parametrize(
    "token_role, api_method, api_endpoint, for_user, response",
    [
        ('server', 'post', 'activity', 'same_user', 200),
        ('server', 'post', 'activity', 'other_user', 404),
        ('server', 'get', 'users', 'same_user', 200),
        ('token', 'post', 'activity', 'same_user', 200),
        ('no_role', 'post', 'activity', 'same_user', 403),
    ],
)
async def test_server_role_api_calls(
    app, token_role, api_method, api_endpoint, for_user, response
):
    user = add_user(app.db, app, name='test_user')
    roles.grant_role(app.db, user, 'user')
    app_log.debug(user.roles)
    app_log.debug(roles.expand_roles_to_scopes(user.orm_user))
    if token_role == 'no_role':
        api_token = user.new_api_token(roles=[])
    else:
        api_token = user.new_api_token(roles=[token_role])

    if for_user == 'same_user':
        username = user.name
    else:
        username = 'otheruser'

    if api_endpoint == 'activity':
        path = "users/{}/activity".format(username)
        data = json.dumps({"servers": {"": {"last_activity": utcnow().isoformat()}}})
    elif api_endpoint == 'users':
        path = "users"
        data = ""

    r = await api_request(
        app,
        path,
        headers={"Authorization": "token {}".format(api_token)},
        data=data,
        method=api_method,
    )
    assert r.status_code == response

    if api_endpoint == 'users' and token_role == 'server':
        reply = r.json()
        assert len(reply) == 1

        user_model = reply[0]
        assert user_model['name'] == username
        assert 'last_activity' in user_model.keys()
        assert (
            all(key for key in ['groups', 'roles', 'servers']) not in user_model.keys()
        )


async def test_oauth_allowed_roles(app, create_temp_role):
    allowed_roles = ['oracle', 'goose']
    service = {
        'name': 'oas1',
        'api_token': 'some-token',
        'oauth_roles': ['oracle', 'goose'],
    }
    for role in allowed_roles:
        create_temp_role('read:users', role_name=role)
    app.services.append(service)
    app.init_services()
    app_service = app.services[0]
    assert app_service['name'] == 'oas1'
    assert set(app_service['oauth_roles']) == set(allowed_roles)


async def test_user_group_roles(app, create_temp_role):
    user = add_user(app.db, app, name='jack')
    another_user = add_user(app.db, app, name='jill')

    group = orm.Group.find(app.db, name='A')
    if not group:
        group = orm.Group(name='A')
        app.db.add(group)
        app.db.commit()

    if group not in user.groups:
        user.groups.append(group)
        app.db.commit()

    if group not in another_user.groups:
        another_user.groups.append(group)
        app.db.commit()

    group_role = orm.Role.find(app.db, 'student-a')
    if not group_role:
        create_temp_role(['read:groups!group=A'], 'student-a')
        roles.grant_role(app.db, group, rolename='student-a')
        group_role = orm.Role.find(app.db, 'student-a')

    # repeat check to ensure group roles don't get added to the user at all
    # regression test for #3472
    roles_before = list(user.roles)
    for i in range(3):
        roles.expand_roles_to_scopes(user.orm_user)
        user_roles = list(user.roles)
        assert user_roles == roles_before

    # jack's API token
    token = user.new_api_token()

    headers = {'Authorization': 'token %s' % token}
    r = await api_request(app, 'users', method='get', headers=headers)
    assert r.status_code == 200
    r.raise_for_status()
    reply = r.json()

    print(reply)

    assert len(reply[0]['roles']) == 1
    assert reply[0]['name'] == 'jack'
    assert group_role.name not in reply[0]['roles']

    headers = {'Authorization': 'token %s' % token}
    r = await api_request(app, 'groups', method='get', headers=headers)
    assert r.status_code == 200
    r.raise_for_status()
    reply = r.json()

    print(reply)

    headers = {'Authorization': 'token %s' % token}
    r = await api_request(app, 'users', method='get', headers=headers)
    assert r.status_code == 200
    r.raise_for_status()
    reply = r.json()

    print(reply)

    assert len(reply[0]['roles']) == 1
    assert reply[0]['name'] == 'jack'
    assert group_role.name not in reply[0]['roles']


async def test_config_role_list():
    roles_to_load = [
        {
            'name': 'elephant',
            'description': 'pacing about',
            'scopes': ['read:hub'],
        },
        {
            'name': 'tiger',
            'description': 'pouncing stuff',
            'scopes': ['shutdown'],
        },
    ]
    hub = MockHub(load_roles=roles_to_load)
    hub.init_db()
    hub.authenticator.admin_users = ['admin']
    await hub.init_role_creation()
    for role_conf in roles_to_load:
        assert orm.Role.find(hub.db, name=role_conf['name'])
    # Now remove elephant from config and see if it is removed from database
    roles_to_load.pop(0)
    hub.load_roles = roles_to_load
    await hub.init_role_creation()
    assert orm.Role.find(hub.db, name='tiger')
    assert not orm.Role.find(hub.db, name='elephant')


async def test_config_role_users():
    role_name = 'painter'
    user_name = 'benny'
    user_names = ['agnetha', 'bjorn', 'anni-frid', user_name]
    roles_to_load = [
        {
            'name': role_name,
            'description': 'painting with colors',
            'scopes': ['users', 'groups'],
            'users': user_names,
        },
    ]
    hub = MockHub(load_roles=roles_to_load)
    hub.init_db()
    hub.authenticator.admin_users = ['admin']
    hub.authenticator.allowed_users = user_names
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    user = orm.User.find(hub.db, name=user_name)
    role = orm.Role.find(hub.db, name=role_name)
    assert role in user.roles
    # Now reload and see if user is removed from role list
    roles_to_load[0]['users'].remove(user_name)
    hub.load_roles = roles_to_load
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    user = orm.User.find(hub.db, name=user_name)
    role = orm.Role.find(hub.db, name=role_name)
    assert role not in user.roles


async def test_scope_expansion_revokes_tokens(app, mockservice_url):
    role_name = 'morpheus'
    roles_to_load = [
        {
            'name': role_name,
            'description': 'wears sunglasses',
            'scopes': ['users', 'groups'],
        },
    ]
    app.load_roles = roles_to_load
    await app.init_role_creation()
    user = add_user(app.db, name='laurence')
    for _ in range(2):
        user.new_api_token()
    red_token, blue_token = user.api_tokens
    roles.grant_role(app.db, red_token, role_name)
    service = mockservice_url
    red_token.client_id = service.oauth_client_id
    app.db.commit()
    # Restart hub and see if token is revoked
    app.load_roles[0]['scopes'].append('proxy')
    await app.init_role_creation()
    user = orm.User.find(app.db, name='laurence')
    assert red_token not in user.api_tokens
    assert blue_token in user.api_tokens


async def test_duplicate_role_users():
    role_name = 'painter'
    user_name = 'benny'
    user_names = ['agnetha', 'bjorn', 'anni-frid', user_name]
    roles_to_load = [
        {
            'name': role_name,
            'description': 'painting with colors',
            'scopes': ['users', 'groups'],
            'users': user_names,
        },
        {
            'name': role_name,
            'description': 'painting with colors',
            'scopes': ['users', 'groups'],
            'users': user_names,
        },
    ]
    hub = MockHub(load_roles=roles_to_load)
    hub.init_db()
    with pytest.raises(ValueError):
        await hub.init_role_creation()


async def test_admin_role_and_flag():
    admin_role_spec = [
        {
            'name': 'admin',
            'users': ['eddy'],
        }
    ]
    hub = MockHub(load_roles=admin_role_spec)
    hub.init_db()
    hub.authenticator.admin_users = ['admin']
    hub.authenticator.allowed_users = ['eddy']
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    admin_role = orm.Role.find(hub.db, name='admin')
    for user_name in ['eddy', 'admin']:
        user = orm.User.find(hub.db, name=user_name)
        assert user.admin
        assert admin_role in user.roles
    admin_role_spec[0]['users'].remove('eddy')
    hub.load_roles = admin_role_spec
    await hub.init_users()
    await hub.init_role_assignment()
    user = orm.User.find(hub.db, name='eddy')
    assert not user.admin
    assert admin_role not in user.roles


async def test_custom_role_reset():
    user_role_spec = [
        {
            'name': 'user',
            'scopes': ['self', 'shutdown'],
            'users': ['eddy'],
        }
    ]
    hub = MockHub(load_roles=user_role_spec)
    hub.init_db()
    hub.authenticator.allowed_users = ['eddy']
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    user_role = orm.Role.find(hub.db, name='user')
    user = orm.User.find(hub.db, name='eddy')
    assert user_role in user.roles
    assert 'shutdown' in user_role.scopes
    hub.load_roles = []
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    user_role = orm.Role.find(hub.db, name='user')
    user = orm.User.find(hub.db, name='eddy')
    assert user_role in user.roles
    assert 'shutdown' not in user_role.scopes


async def test_removal_config_to_db():
    role_spec = [
        {
            'name': 'user',
            'scopes': ['self', 'shutdown'],
        },
        {
            'name': 'wizard',
            'scopes': ['self', 'read:groups'],
        },
    ]
    hub = MockHub(load_roles=role_spec)
    hub.init_db()
    await hub.init_role_creation()
    assert orm.Role.find(hub.db, 'user')
    assert orm.Role.find(hub.db, 'wizard')
    hub.load_roles = []
    await hub.init_role_creation()
    assert orm.Role.find(hub.db, 'user')
    assert not orm.Role.find(hub.db, 'wizard')


async def test_no_admin_role_change():
    role_spec = [{'name': 'admin', 'scopes': ['shutdown']}]
    hub = MockHub(load_roles=role_spec)
    hub.init_db()
    with pytest.raises(ValueError):
        await hub.init_role_creation()


async def test_user_config_respects_memberships():
    role_spec = [
        {
            'name': 'user',
            'scopes': ['self', 'shutdown'],
        }
    ]
    user_names = ['eddy', 'carol']
    hub = MockHub(load_roles=role_spec)
    hub.init_db()
    hub.authenticator.allowed_users = user_names
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    user_role = orm.Role.find(hub.db, 'user')
    for user_name in user_names:
        user = orm.User.find(hub.db, user_name)
        assert user in user_role.users


async def test_admin_role_respects_config():
    role_spec = [
        {
            'name': 'admin',
        }
    ]
    admin_users = ['eddy', 'carol']
    hub = MockHub(load_roles=role_spec)
    hub.init_db()
    hub.authenticator.admin_users = admin_users
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    admin_role = orm.Role.find(hub.db, 'admin')
    for user_name in admin_users:
        user = orm.User.find(hub.db, user_name)
        assert user in admin_role.users


async def test_empty_admin_spec():
    role_spec = [{'name': 'admin', 'users': []}]
    hub = MockHub(load_roles=role_spec)
    hub.init_db()
    hub.authenticator.admin_users = []
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    admin_role = orm.Role.find(hub.db, 'admin')
    assert not admin_role.users


async def test_no_default_service_role():
    services = [
        {
            'name': 'minesweeper',
            'api_token': 'some-token',
        }
    ]
    hub = MockHub(services=services)
    await hub.initialize()
    service = orm.Service.find(hub.db, 'minesweeper')
    assert not service.roles


async def test_hub_upgrade_detection(tmpdir):
    db_url = f"sqlite:///{tmpdir.join('jupyterhub.sqlite')}"
    os.environ['JUPYTERHUB_TEST_DB_URL'] = db_url
    # Create hub with users and tokens
    hub = MockHub(db_url=db_url)
    await hub.initialize()
    user_names = ['patricia', 'quentin']
    user_role = orm.Role.find(hub.db, 'user')
    for name in user_names:
        user = add_user(hub.db, name=name)
        user.new_api_token()
        assert user_role in user.roles
    for role in hub.db.query(orm.Role):
        hub.db.delete(role)
    hub.db.commit()
    # Restart hub in emulated upgrade mode: default roles for all entities
    hub.test_clean_db = False
    await hub.initialize()
    assert getattr(hub, '_rbac_upgrade', False)
    user_role = orm.Role.find(hub.db, 'user')
    token_role = orm.Role.find(hub.db, 'token')
    for name in user_names:
        user = orm.User.find(hub.db, name)
        assert user_role in user.roles
        assert token_role in user.api_tokens[0].roles
    # Strip all roles and see if it sticks
    user_role.users = []
    token_role.tokens = []
    hub.db.commit()

    hub.init_db()
    hub.init_hub()
    await hub.init_role_creation()
    await hub.init_users()
    hub.authenticator.allowed_users = ['patricia']
    await hub.init_api_tokens()
    await hub.init_role_assignment()
    assert not getattr(hub, '_rbac_upgrade', False)
    user_role = orm.Role.find(hub.db, 'user')
    token_role = orm.Role.find(hub.db, 'token')
    allowed_user = orm.User.find(hub.db, 'patricia')
    rem_user = orm.User.find(hub.db, 'quentin')
    assert user_role in allowed_user.roles
    assert token_role not in allowed_user.api_tokens[0].roles
    assert user_role not in rem_user.roles
    assert token_role not in rem_user.roles


async def test_token_keep_roles_on_restart():
    role_spec = [
        {
            'name': 'bloop',
            'scopes': ['read:users'],
        }
    ]
    hub = MockHub(load_roles=role_spec)
    hub.init_db()
    hub.authenticator.admin_users = ['ben']
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_role_assignment()
    user = orm.User.find(hub.db, name='ben')
    for _ in range(3):
        user.new_api_token()
    happy_token, content_token, sad_token = user.api_tokens
    roles.grant_role(hub.db, happy_token, 'bloop')
    roles.strip_role(hub.db, sad_token, 'token')
    assert len(happy_token.roles) == 2
    assert len(content_token.roles) == 1
    assert len(sad_token.roles) == 0
    # Restart hub and see if roles are as expected
    hub.load_roles = []
    await hub.init_role_creation()
    await hub.init_users()
    await hub.init_api_tokens()
    await hub.init_role_assignment()
    user = orm.User.find(hub.db, name='ben')
    happy_token, content_token, sad_token = user.api_tokens
    assert len(happy_token.roles) == 1
    assert len(content_token.roles) == 1
    print(sad_token.roles)
    assert len(sad_token.roles) == 0
    for token in user.api_tokens:
        hub.db.delete(token)
    hub.db.commit()
