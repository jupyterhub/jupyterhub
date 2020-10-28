"""Test roles"""
# import pytest
from pytest import mark

from .. import orm
from .. import roles
from ..utils import maybe_future
from .mocking import MockHub


@mark.role
def test_orm_roles(db):
    """Test orm roles setup"""
    user = orm.User(name='falafel')
    db.add(user)
    service = orm.Service(name='kebab')
    db.add(service)
    role = orm.Role(name='default')
    db.add(role)
    db.commit()
    assert role.users == []
    assert role.services == []
    assert user.roles == []
    assert service.roles == []

    role.users.append(user)
    role.services.append(service)
    db.commit()
    assert role.users == [user]
    assert user.roles == [role]
    assert role.services == [service]
    assert service.roles == [role]

    db.delete(user)
    db.commit()
    assert role.users == []
    db.delete(role)
    db.commit()
    assert service.roles == []
    db.delete(service)
    db.commit()


@mark.role
def test_orm_role_delete_cascade(db):
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
    for user in db.query(orm.User):
        print(user.name)
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
    hub = MockHub(test_clean_db=False, **kwargs)
    hub.init_db()
    db = hub.db
    # add test services to db
    services = [
        {'name': 'cull_idle', 'admin': False},
        {'name': 'user_service', 'admin': False},
        {'name': 'admin_service', 'admin': True},
    ]
    for service_specs in services:
        service = orm.Service.find(db, service_specs['name'])
        if service is None:
            service = orm.Service(
                name=service_specs['name'], admin=service_specs['admin']
            )
            db.add(service)
    db.commit()
    await hub.init_roles()

    # test if every service has a role (and no duplicates)
    admin_role = orm.Role.find(db, name='admin')
    user_role = orm.Role.find(db, name='user')
    for service in db.query(orm.Service):
        assert len(service.roles) > 0
        assert len(service.roles) == len(set(service.roles))
        if service.admin:
            assert admin_role in service.roles
            assert user_role not in service.roles

    # test if predefined roles loaded and assigned
    culler_role = orm.Role.find(db, name='culler')
    cull_idle = orm.Service.find(db, name='cull_idle')
    assert culler_role in cull_idle.roles
    assert user_role not in cull_idle.roles
