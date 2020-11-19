"""Roles utils"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from . import orm


def get_default_roles():

    """Returns a list of default role dictionaries"""

    default_roles = [
        {
            'name': 'user',
            'description': 'Everything the user can do',
            'scopes': ['all'],
        },
        {
            'name': 'admin',
            'description': 'Admin privileges (currently can do everything)',
            'scopes': [
                'all',
                'users',
                'users:tokens',
                'admin:users',
                'admin:users:servers',
                'groups',
                'admin:groups',
                'read:services',
                'proxy',
                'shutdown',
            ],
        },
        {
            'name': 'server',
            'description': 'Post activity only',
            'scopes': ['users:activity!user=username'],
        },
    ]
    return default_roles


def add_role(db, role_dict):

    """Adds a new role to database or modifies an existing one"""

    if 'name' not in role_dict.keys():
        raise ValueError('Role must have a name')
    else:
        name = role_dict['name']
        role = orm.Role.find(db, name)

    description = role_dict.get('description')
    scopes = role_dict.get('scopes')

    if role is None:
        role = orm.Role(name=name, description=description, scopes=scopes,)
        db.add(role)
    else:
        if description:
            role.description = description
        if scopes:
            role.scopes = scopes
    db.commit()


def get_orm_class(kind):
    if kind == 'users':
        Class = orm.User
    elif kind == 'services':
        Class = orm.Service
    elif kind == 'tokens':
        Class = orm.APIToken
    else:
        raise ValueError("kind must be users, services or tokens, not %r" % kind)

    return Class


def existing_only(func):

    """Decorator for checking if objects and roles exist"""

    def check_existence(db, objname, kind, rolename):

        Class = get_orm_class(kind)
        obj = Class.find(db, objname)
        role = orm.Role.find(db, rolename)

        if obj is None:
            raise ValueError("%r of kind %r does not exist" % (objname, kind))
        elif role is None:
            raise ValueError("Role %r does not exist" % rolename)
        else:
            func(db, obj, kind, role)

    return check_existence


@existing_only
def add_obj(db, objname, kind, rolename):

    """Adds a role for users, services or tokens"""

    if rolename not in objname.roles:
        objname.roles.append(rolename)
        db.commit()


@existing_only
def remove_obj(db, objname, kind, rolename):

    """Removes a role for users, services or tokens"""

    if rolename in objname.roles:
        objname.roles.remove(rolename)
        db.commit()


def switch_default_role(db, obj, kind, admin):

    """Switch between default user and admin roles for users/services"""

    user_role = orm.Role.find(db, 'user')
    admin_role = orm.Role.find(db, 'admin')

    def add_and_remove(db, obj, kind, current_role, new_role):

        if current_role in obj.roles:
            remove_obj(db, objname=obj.name, kind=kind, rolename=current_role.name)
        # only add new default role if the user has no other roles
        if len(obj.roles) < 1:
            add_obj(db, objname=obj.name, kind=kind, rolename=new_role.name)

    if admin:
        add_and_remove(db, obj, kind, user_role, admin_role)
    else:
        add_and_remove(db, obj, kind, admin_role, user_role)


def update_roles(db, obj, kind, roles=None):

    """Updates object's roles if specified,
       assigns default if no roles specified"""

    Class = get_orm_class(kind)
    user_role = orm.Role.find(db, 'user')

    if roles:
        for rolename in roles:
            if Class == orm.APIToken:
                # FIXME - check if specified roles do not add permissions
                # on top of the token owner's scopes
                role = orm.Role.find(db, rolename)
                if role:
                    role.tokens.append(obj)
                else:
                    raise ValueError('Role %r does not exist' % rolename)
            else:
                add_obj(db, objname=obj.name, kind=kind, rolename=rolename)
    else:
        # tokens can have only 'user' role as default
        # assign the default only for user tokens
        if Class == orm.APIToken:
            if len(obj.roles) < 1 and obj.user is not None:
                user_role.tokens.append(obj)
            db.commit()
        # users and services can have 'user' or 'admin' roles as default
        else:
            switch_default_role(db, obj, kind, obj.admin)
