"""Test roles"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from pytest import mark

from .. import orm
from .. import roles
from ..utils import maybe_future
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

    user = orm.User(name='falafel')
    db.add(user)
    db.commit()

    service = orm.Service(name='kebab')
    db.add(service)
    db.commit()

    assert user_role.users == []
    assert user_role.services == []
    assert service_role.users == []
    assert service_role.services == []
    assert user.roles == []
    assert service.roles == []

    user_role.users.append(user)
    service_role.services.append(service)
    db.commit()
    assert user_role.users == [user]
    assert user.roles == [user_role]
    assert service_role.services == [service]
    assert service.roles == [service_role]

    # check token creation without specifying its role
    # assigns it the default 'user' role
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
    # check deleting the 'service' role removes it from service roles
    db.delete(service_role)
    db.commit()
    assert service.roles == []

    db.delete(service)
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
            ['users'],
            {
                'users',
                'read:users',
                'users:activity',
                'users:servers',
                'read:users:name',
                'read:users:groups',
                'read:users:activity',
                'read:users:servers',
            },
        ),
        (
            ['read:users'],
            {
                'read:users',
                'read:users:name',
                'read:users:groups',
                'read:users:activity',
                'read:users:servers',
            },
        ),
        (['read:users:servers'], {'read:users:servers'}),
        (['admin:groups'], {'admin:groups'}),
    ],
)
def test_get_subscopes(db, scopes, subscopes):
    """Test role scopes expansion into their subscopes"""
    roles.add_role(db, {'name': 'testing_scopes', 'scopes': scopes})
    role = orm.Role.find(db, name='testing_scopes')
    response = roles.get_subscopes(role)
    assert response == subscopes
    db.delete(role)


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
    assert orm.Role.find(db, 'user') is not None
    assert orm.Role.find(db, 'admin') is not None
    assert orm.Role.find(db, 'server') is not None
    assert orm.Role.find(db, 'token') is not None
    assert orm.Role.find(db, 'service') is not None


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
        {
            'name': 'user',
            'description': 'Only read access',
            'scopes': ['read:all'],
            'users': ['bilbo'],
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

    # test if the 'user' role has been overwritten and assigned
    user_role = orm.Role.find(db, 'user')
    admin_role = orm.Role.find(db, 'admin')
    assert user_role is not None
    assert user_role.scopes == ['read:all']

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


@mark.role
async def test_load_roles_services(tmpdir, request):
    services = [
        {'name': 'cull_idle', 'api_token': 'some-token'},
        {'name': 'user_service', 'api_token': 'some-other-token'},
        {'name': 'admin_service', 'api_token': 'secret-token', 'admin': True},
    ]
    roles_to_load = [
        {
            'name': 'culler',
            'description': 'Cull idle servers',
            'scopes': ['users:servers', 'admin:servers'],
            'services': ['cull_idle'],
        },
    ]
    kwargs = {'load_roles': roles_to_load}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db
    # clean db of previous services and add testing ones
    for service in db.query(orm.Service):
        db.delete(service)
    db.commit()
    for service in services:
        orm_service = orm.Service.find(db, name=service['name'])
        if orm_service is None:
            # not found, create a new one
            orm_service = orm.Service(name=service['name'])
            db.add(orm_service)
            orm_service.admin = service.get('admin', False)
    db.commit()
    await hub.init_roles()

    # test if every service has a role (and no duplicates)
    admin_role = orm.Role.find(db, name='admin')
    user_role = orm.Role.find(db, name='user')
    service_role = orm.Role.find(db, name='service')

    # test if predefined roles loaded and assigned
    culler_role = orm.Role.find(db, name='culler')
    cull_idle = orm.Service.find(db, name='cull_idle')
    assert culler_role in cull_idle.roles
    assert service_role not in cull_idle.roles

    # test if every service has a role (and no duplicates)
    for service in db.query(orm.Service):
        assert len(service.roles) > 0
        assert len(service.roles) == len(set(service.roles))

        # test default role assignment
        if service.admin:
            assert admin_role in service.roles
            assert service_role not in service.roles
        elif culler_role not in service.roles:
            assert service_role in service.roles
            assert service_role.scopes == []
            assert admin_role not in service.roles
            # make sure 'user' role not assigned to service
            assert user_role not in service.roles

    # delete the test services
    for service in db.query(orm.Service):
        db.delete(service)
    db.commit()


@mark.role
async def test_load_roles_tokens(tmpdir, request):
    services = [
        {'name': 'cull_idle', 'admin': True, 'api_token': 'another-secret-token'}
    ]
    user_tokens = {
        'secret-token': 'cyclops',
        'super-secret-token': 'admin',
    }
    service_tokens = {
        'another-secret-token': 'cull_idle',
    }
    roles_to_load = [
        {
            'name': 'culler',
            'description': 'Cull idle servers',
            'scopes': ['users:servers', 'admin:servers'],
            'tokens': ['another-secret-token'],
        },
    ]
    kwargs = {
        'load_roles': roles_to_load,
        'services': services,
        'api_tokens': user_tokens,
        'service_tokens': service_tokens,
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

    # test if another-secret-token has culler role
    service = orm.Service.find(db, 'cull_idle')
    culler_role = orm.Role.find(db, 'culler')
    token = orm.APIToken.find(db, 'another-secret-token')
    assert len(token.roles) == 1
    assert culler_role in token.roles

    # test if all other tokens have default 'user' role
    token_role = orm.Role.find(db, 'token')
    sec_token = orm.APIToken.find(db, 'secret-token')
    assert token_role in sec_token.roles
    s_sec_token = orm.APIToken.find(db, 'super-secret-token')
    assert token_role in s_sec_token.roles


@mark.role
@mark.parametrize(
    "headers, role_list, status",
    [
        ({}, None, 200),
        ({}, ['reader'], 200),
        ({}, ['non-existing'], 404),
        ({}, ['user_creator'], 403),
    ],
)
async def test_get_new_token_via_api(app, headers, role_list, status):
    user = add_user(app.db, app, name='user')
    roles.add_role(app.db, {'name': 'reader', 'scopes': ['all']})
    roles.add_role(app.db, {'name': 'user_creator', 'scopes': ['admin:users']})
    if role_list:
        body = json.dumps({'roles': role_list})
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
    assert reply['user'] == 'user'
    if not role_list:
        assert reply['roles'] == ['token']
    else:
        assert reply['roles'] == ['reader']
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
    token_scopes = scopes.get_scopes_for(orm_obj.api_tokens[0])
    print(token_scopes)
    assert bool(token_scopes) == has_user_scopes
    app.db.delete(orm_obj)
    app.db.delete(test_role)
