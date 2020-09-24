"""Roles utils"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from .orm import Role


# define default roles
class DefaultRoles:

    user = Role(name='user', description='Everything the user can do', scopes=['all'])
    admin = Role(
        name='admin',
        description='Admin privileges (currently can do everything)',
        scopes=[
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
    )
    server = Role(
        name='server',
        description='Post activity only',
        scopes=['users:activity!user=username'],
    )
    roles = (user, admin, server)

    def __init__(cls, roles=roles):
        cls.roles = roles

    @classmethod
    def get_user_role(cls, db):
        return Role.find(db, name=cls.user.name)

    @classmethod
    def get_admin_role(cls, db):
        return Role.find(db, name=cls.admin.name)

    @classmethod
    def get_server_role(cls, db):
        return Role.find(db, name=cls.server.name)

    @classmethod
    def load_to_database(cls, db):
        for role in cls.roles:
            db_role = Role.find(db, name=role.name)
            if db_role is None:
                new_role = Role(
                    name=role.name, description=role.description, scopes=role.scopes,
                )
                db.add(new_role)
        db.commit()

    @classmethod
    def add_default_role(cls, db, user):
        role = None
        if user.admin and cls.admin not in user.roles:
            role = cls.get_admin_role(db)
        if not user.admin and cls.user not in user.roles:
            role = cls.get_user_role(db)
        if role is not None:
            add_user(db, user, role)
            db.commit()

    @classmethod
    def change_admin(cls, db, user, admin):
        user_role = cls.get_user_role(db)
        admin_role = cls.get_admin_role(db)
        if admin:
            if user_role in user.roles:
                remove_user(db, user, user_role)
            add_user(db, user, admin_role)
        else:
            if admin_role in user.roles:
                remove_user(db, user, admin_role)
            add_user(db, user, user_role)
        db.commit()


def add_user(db, user, role):
    if role is not None and role not in user.roles:
        user.roles.append(role)
        db.commit()


def remove_user(db, user, role):
    if role is not None and role in user.roles:
        user.roles.remove(role)
        db.commit()


def add_predef_role(db, predef_role):
    """ 
        Returns either the role to write into db or updated role if already in db 
    """
    role = Role.find(db, predef_role['name'])
    # if a new role, add to db, if existing, rewrite its attributes apart from the name
    if role is None:
        role = Role(
            name=predef_role['name'],
            description=predef_role['description'],
            scopes=predef_role['scopes'],
        )
        db.add(role)
        db.commit()
    else:
        # check if it's not one of the default roles
        if not any(d.name == predef_role['name'] for d in DefaultRoles.roles):
            # if description and scopes specified, rewrite the old ones
            if 'description' in predef_role.keys():
                role.description = predef_role['description']
            if 'scopes' in predef_role.keys():
                role.scopes = predef_role['scopes']
            # FIXME - for now deletes old users and writes new ones
            role.users = []
        else:
            raise ValueError(
                "The role %r is a default role that cannot be overwritten, use a different role name"
                % predef_role['name']
            )
    return role
