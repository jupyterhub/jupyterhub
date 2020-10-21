"""Test roles"""
# import pytest
from pytest import mark

from .. import orm
from .. import roles
from .mocking import MockHub


@mark.role
def test_roles(db):
    """Test orm roles setup"""
    user = orm.User(name='falafel')
    db.add(user)
    role = orm.Role(name='default')
    db.add(role)
    db.commit()
    assert role.users == []
    assert user.roles == []

    role.users.append(user)
    db.commit()
    assert role.users == [user]
    assert user.roles == [role]

    db.delete(user)
    db.commit()
    assert role.users == []
    db.delete(role)


@mark.role
def test_role_delete_cascade(db):
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
async def test_load_roles(tmpdir, request):
    """Test loading default and predefined roles in app.py"""
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
            'users': ['test_user'],
        },
    ]
    kwargs = {'load_roles': roles_to_load}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    db = hub.db
    await hub.init_users()
    await hub.init_roles()
    # test if the 'user' role has been overwritten
    user_role = orm.Role.find(db, 'user')
    assert user_role is not None
    assert user_role.scopes == ['read:all']
    # test other default roles loaded to database
    assert orm.Role.find(db, 'user') is not None
    assert orm.Role.find(db, 'admin') is not None
    assert orm.Role.find(db, 'server') is not None
    # test if every existing user has a role (and no duplicates)
    for user in db.query(orm.User):
        assert len(user.roles) > 0
        assert len(user.roles) == len(set(user.roles))
    # test if predefined roles loaded and assigned
    teacher_role = orm.Role.find(db, name='teacher')
    assert teacher_role is not None
    gandalf_user = orm.User.find(db, name='gandalf')
    assert teacher_role in gandalf_user.roles
    cyclops_user = orm.User.find(db, name='cyclops')
    assert teacher_role in cyclops_user.roles
