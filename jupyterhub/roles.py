"""Roles utils"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from itertools import chain

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
                'read:hub',
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


def get_scopes():

    """
    Returns a dictionary of scopes:
    scopes.keys() = scopes of highest level and scopes that have their own subscopes
    scopes.values() = a list of first level subscopes or None
    """

    scopes = {
        'all': ['read:all'],
        'users': ['read:users', 'users:activity', 'users:servers'],
        'read:users': [
            'read:users:name',
            'read:users:groups',
            'read:users:activity',
            'read:users:servers',
        ],
        'users:tokens': ['read:users:tokens'],
        'admin:users': None,
        'admin:users:servers': None,
        'groups': ['read:groups'],
        'admin:groups': None,
        'read:services': None,
        'read:hub': None,
        'proxy': None,
        'shutdown': None,
    }

    return scopes


def expand_scope(scopename):

    """Returns a set of all subscopes"""

    scopes = get_scopes()
    subscopes = [scopename]

    def expand_subscopes(index):

        more_subscopes = list(
            filter(lambda scope: scope in scopes.keys(), subscopes[index:])
        )
        for scope in more_subscopes:
            subscopes.extend(scopes[scope])

    if scopename in scopes.keys() and scopes[scopename] is not None:
        subscopes.extend(scopes[scopename])
        # record the index from where it should check for "subscopes of sub-subscopes"
        index_for_sssc = len(subscopes)
        # check for "subscopes of subscopes"
        expand_subscopes(index=1)
        # check for "subscopes of sub-subscopes"
        expand_subscopes(index=index_for_sssc)

    expanded_scope = set(subscopes)

    return expanded_scope


def get_subscopes(*args):

    """Returns a set of all available subscopes for a specified role or list of roles"""

    scope_list = []

    for role in args:
        scope_list.extend(role.scopes)

    scopes = set(chain.from_iterable(list(map(expand_scope, scope_list))))

    return scopes


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
        role = orm.Role(name=name, description=description, scopes=scopes)
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
    elif kind == 'groups':
        Class = orm.Group
    else:
        raise ValueError(
            "kind must be users, services, tokens or groups, not %r" % kind
        )

    return Class


def get_rolenames(role_list):

    """Return a list of rolenames from a list of roles"""

    rolenames = []
    for role in role_list:
        rolenames.append(role.name)
    return rolenames


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

    """Adds a role for users, services, tokens or groups"""

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

                role = orm.Role.find(db, rolename)
                if role:
                    # compare the requested role permissions with the owner's permissions (scopes)
                    token_scopes = get_subscopes(role)
                    # find the owner and their roles
                    owner = None
                    if obj.user_id:
                        owner = db.query(orm.User).get(obj.user_id)
                    elif obj.service_id:
                        owner = db.query(orm.Service).get(obj.service_id)
                    if owner:
                        owner_scopes = get_subscopes(*owner.roles)
                        if token_scopes.issubset(owner_scopes):
                            role.tokens.append(obj)
                        else:
                            raise ValueError(
                                'Requested token role %r has higher permissions than the token owner'
                                % rolename
                            )
                else:
                    raise NameError('Role %r does not exist' % rolename)
            else:
                add_obj(db, objname=obj.name, kind=kind, rolename=rolename)
    else:
        # groups can be without a role
        if Class == orm.Group:
            pass
        # tokens can have only 'user' role as default
        # assign the default only for user tokens
        elif Class == orm.APIToken:
            if len(obj.roles) < 1 and obj.user is not None:
                user_role.tokens.append(obj)
            db.commit()
        # users and services can have 'user' or 'admin' roles as default
        else:
            switch_default_role(db, obj, kind, obj.admin)


def mock_roles(app, name, kind):

    """Loads and assigns default roles for mocked objects"""

    Class = get_orm_class(kind)

    obj = Class.find(app.db, name=name)
    default_roles = get_default_roles()
    for role in default_roles:
        add_role(app.db, role)
    update_roles(db=app.db, obj=obj, kind=kind)
