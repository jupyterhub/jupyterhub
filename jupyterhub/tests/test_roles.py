"""Test roles"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from itertools import chain

import pytest
from pytest import mark
from tornado.log import app_log

from .. import orm
from .. import roles
from ..scopes import get_scopes_for
from ..utils import maybe_future
from ..utils import utcnow
from .mocking import MockHub
from .test_scopes import create_temp_role
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
                'admin:users:auth_state',
                'users',
                'read:users',
                'users:activity',
                'read:users:name',
                'read:users:groups',
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
        (['read:users:servers'], {'read:users:servers', 'read:users:name'}),
        (['admin:groups'], {'admin:groups', 'groups', 'read:groups'}),
        (
            ['users:tokens!group=hobbits'],
            {'users:tokens!group=hobbits', 'read:users:tokens!group=hobbits'},
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
    await hub.init_roles()
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
                    'read:users:tokens',
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
    await hub.init_users()
    await hub.init_roles()

    admin_role = orm.Role.find(db, 'admin')
    user_role = orm.Role.find(db, 'user')
    # test if every user has a role (and no duplicates)
    # and admins have admin role
    for user in db.query(orm.User):
        assert len(user.roles) > 0
        assert len(user.roles) == len(set(user.roles))
        if user.admin:
            assert admin_role in user.roles
            assert user_role not in user.roles

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
                'read:users:servers',
                'users:servers',
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
    await hub.init_api_tokens()
    # make 'admin_service' admin
    admin_service = orm.Service.find(db, 'admin_service')
    admin_service.admin = True
    db.commit()
    await hub.init_roles()

    # test if every service has a role (and no duplicates)
    admin_role = orm.Role.find(db, name='admin')
    user_role = orm.Role.find(db, name='user')

    # test if predefined roles loaded and assigned
    culler_role = orm.Role.find(db, name='idle-culler')
    culler_service = orm.Service.find(db, name='idle-culler')
    assert culler_role in culler_service.roles

    # test if every service has a role (and no duplicates)
    for service in db.query(orm.Service):
        assert len(service.roles) > 0
        assert len(service.roles) == len(set(service.roles))

        # test default role assignment
        if service.admin:
            assert admin_role in service.roles
            assert user_role not in service.roles
        elif culler_role not in service.roles:
            assert user_role in service.roles
            assert admin_role not in service.roles

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
    await hub.init_groups()
    await hub.init_roles()

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
            'tokens': ['super-secret-token'],
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
    await hub.init_users()
    await hub.init_api_tokens()
    await hub.init_roles()

    # test if gandalf's token has the 'reader' role
    reader_role = orm.Role.find(db, 'reader')
    token = orm.APIToken.find(db, 'super-secret-token')
    assert reader_role in token.roles

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
async def test_load_roles_user_tokens_not_allowed(tmpdir, request):
    user_tokens = {
        'secret-token': 'bilbo',
    }
    roles_to_load = [
        {
            'name': 'user-creator',
            'description': 'Creates/deletes any user',
            'scopes': ['admin:users'],
            'tokens': ['secret-token'],
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
    hub.authenticator.allowed_users = ['bilbo']
    await hub.init_users()
    await hub.init_api_tokens()

    response = 'allowed'
    # bilbo has only default 'user' role
    # while bilbo's token is requesting role with higher permissions
    with pytest.raises(ValueError):
        await hub.init_roles()

    # delete the test tokens
    for token in db.query(orm.APIToken):
        db.delete(token)
    db.commit()

    # delete the test roles
    for role in roles_to_load:
        roles.delete_role(db, role['name'])


@mark.role
async def test_load_roles_service_tokens(tmpdir, request):
    services = [
        {'name': 'idle-culler', 'api_token': 'another-secret-token'},
    ]
    service_tokens = {
        'another-secret-token': 'idle-culler',
    }
    roles_to_load = [
        {
            'name': 'idle-culler',
            'description': 'Cull idle servers',
            'scopes': [
                'read:users:name',
                'read:users:activity',
                'read:users:servers',
                'users:servers',
            ],
            'services': ['idle-culler'],
            'tokens': ['another-secret-token'],
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
    await hub.init_api_tokens()
    await hub.init_roles()

    # test if another-secret-token has idle-culler role
    service = orm.Service.find(db, 'idle-culler')
    culler_role = orm.Role.find(db, 'idle-culler')
    token = orm.APIToken.find(db, 'another-secret-token')
    assert len(token.roles) == 1
    assert culler_role in token.roles

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
async def test_load_roles_service_tokens_not_allowed(tmpdir, request):
    services = [{'name': 'some-service', 'api_token': 'secret-token'}]
    service_tokens = {
        'secret-token': 'some-service',
    }
    roles_to_load = [
        {
            'name': 'user-reader',
            'description': 'Read-only user models',
            'scopes': ['read:users'],
            'services': ['some-service'],
        },
        # 'idle-culler' role has higher permissions that the token's owner 'some-service'
        {
            'name': 'idle-culler',
            'description': 'Cull idle servers',
            'scopes': [
                'read:users:name',
                'read:users:activity',
                'read:users:servers',
                'users:servers',
            ],
            'tokens': ['secret-token'],
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
    await hub.init_api_tokens()
    with pytest.raises(ValueError):
        await hub.init_roles()

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
