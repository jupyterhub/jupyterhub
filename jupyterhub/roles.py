"""Roles utils"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from .orm import Role


def get_default_roles():

    """Returns a list of default roles dictionaries"""

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

    role = Role.find(db, role_dict['name'])

    if role is None:
        role = Role(
            name=role_dict['name'],
            description=role_dict['description'],
            scopes=role_dict['scopes'],
        )
        db.add(role)
    else:
        role.description = role_dict['description']
        role.scopes = role_dict['scopes']
    db.commit()


def add_user(db, user, role):
    if role is not None and role not in user.roles:
        user.roles.append(role)
        db.commit()


def remove_user(db, user, role):
    if role is not None and role in user.roles:
        user.roles.remove(role)
        db.commit()


def update_roles(db, user):

    """Updates roles if user has no role with default or when user admin status is changed"""

    user_role = Role.find(db, 'user')
    admin_role = Role.find(db, 'admin')

    if user.admin:
        if user_role in user.roles:
            remove_user(db, user, user_role)
        add_user(db, user, admin_role)
    else:
        if admin_role in user.roles:
            remove_user(db, user, admin_role)
        # only add user role if the user has no other roles
        if len(user.roles) < 1:
            add_user(db, user, user_role)
    db.commit()
