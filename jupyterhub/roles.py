"""Roles utils"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from itertools import chain

from sqlalchemy import func
from tornado.log import app_log

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
            'scopes': ['users:activity'],
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

    default_roles = get_default_roles()

    if 'name' not in role_dict.keys():
        raise ValueError('Role definition in config file must have a name!')
    else:
        name = role_dict['name']
        role = orm.Role.find(db, name)

    description = role_dict.get('description')
    scopes = role_dict.get('scopes')

    if role is None:
        role = orm.Role(name=name, description=description, scopes=scopes)
        db.add(role)
        if role_dict not in default_roles:
            app_log.info('Adding role %s to database', name)
    else:
        if description:
            if role.description != description:
                app_log.info('Changing role %s description to %s', name, description)
                role.description = description
        if scopes:
            if role.scopes != scopes:
                app_log.info('Changing role %s scopes to %s', name, scopes)
                role.scopes = scopes
    db.commit()


def remove_role(db, rolename):
    """Removes a role from database"""

    role = orm.Role.find(db, rolename)
    if role:
        db.delete(role)
        db.commit()
    else:
        raise NameError('Cannot remove role %r that does not exist', rolename)


def existing_only(func):
    """Decorator for checking if objects and roles exist"""

    def check_existence(db, objname, kind, rolename):

        Class = orm.get_class(kind)
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

    if kind == 'tokens':
        log_objname = objname
    else:
        log_objname = objname.name

    if rolename not in objname.roles:
        objname.roles.append(rolename)
        db.commit()
        app_log.info('Adding role %s for %s: %s', rolename.name, kind[:-1], log_objname)


@existing_only
def remove_obj(db, objname, kind, rolename):
    """Removes a role for users, services or tokens"""

    if kind == 'tokens':
        log_objname = objname
    else:
        log_objname = objname.name

    if rolename in objname.roles:
        objname.roles.remove(rolename)
        db.commit()
        app_log.info(
            'Removing role %s for %s: %s', rolename.name, kind[:-1], log_objname
        )


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


def check_token_roles(db, token, role):

    """Returns a set of token scopes from its roles and a set of
    token's owner scopes from their roles and their group roles"""

    token_scopes = get_subscopes(role)
    owner = None
    roles_to_check = []

    # find the owner and their roles
    if token.user_id:
        owner = db.query(orm.User).get(token.user_id)
        roles_to_check.extend(owner.roles)
        # if user is a member of any groups, include the groups' roles as well
        for group in owner.groups:
            roles_to_check.extend(group.roles)

    elif token.service_id:
        owner = db.query(orm.Service).get(token.service_id)
        roles_to_check = owner.roles

    owner_scopes = get_subscopes(*roles_to_check)

    return token_scopes, owner_scopes


def update_roles(db, obj, kind, roles=None):
    """Updates object's roles if specified,
    assigns default if no roles specified"""

    Class = orm.get_class(kind)
    user_role = orm.Role.find(db, 'user')
    admin_role = orm.Role.find(db, 'admin')

    if roles:
        for rolename in roles:
            if Class == orm.APIToken:
                role = orm.Role.find(db, rolename)
                if role:
                    app_log.debug(
                        'Checking token permissions against requested role %s', rolename
                    )
                    token_scopes, owner_scopes = check_token_roles(db, obj, role)
                    if token_scopes.issubset(owner_scopes):
                        role.tokens.append(obj)
                        app_log.info(
                            'Adding role %s for %s: %s', role.name, kind[:-1], obj
                        )
                    else:
                        raise ValueError(
                            'Requested token role %r of %r with scopes %r has higher permissions than the owner scopes %r'
                            % (rolename, obj, token_scopes, owner_scopes)
                        )
                else:
                    raise NameError('Role %r does not exist' % rolename)
            else:
                add_obj(db, objname=obj.name, kind=kind, rolename=rolename)
    else:
        # CHECK ME - Does the default role assignment here make sense?

        # groups can be without a role
        if Class == orm.Group:
            pass
        # tokens can have only 'user' role as default
        # assign the default only for user tokens
        # service tokens with no specified role remain without any role (no default)
        elif Class == orm.APIToken:
            app_log.debug('Assigning default roles to tokens')
            if len(obj.roles) < 1 and obj.user is not None:
                user_role.tokens.append(obj)
                db.commit()
                app_log.info('Adding role %s to token %s', 'user', obj)
        # users and services can have 'user' or 'admin' roles as default
        else:
            app_log.debug('Assigning default roles to %s', kind)
            switch_default_role(db, obj, kind, obj.admin)


def add_predef_roles_tokens(db, predef_roles):

    """Adds tokens to predefined roles in config file
    if their permissions allow"""

    for predef_role in predef_roles:
        if 'tokens' in predef_role.keys():
            token_role = orm.Role.find(db, name=predef_role['name'])
            for token_name in predef_role['tokens']:
                token = orm.APIToken.find(db, token_name)
                if token is None:
                    raise ValueError(
                        "Token %r does not exist and cannot assign it to role %r"
                        % (token_name, token_role.name)
                    )
                else:
                    update_roles(db, obj=token, kind='tokens', roles=[token_role.name])


def check_for_default_roles(db, bearer):

    """Checks that role bearers have at least one role (default if none).
    Groups can be without a role"""

    Class = orm.get_class(bearer)
    if Class == orm.Group:
        pass
    else:
        for obj in (
            db.query(Class)
            .outerjoin(orm.Role, Class.roles)
            .group_by(Class.id)
            .having(func.count(orm.Role.id) == 0)
        ):
            update_roles(db, obj=obj, kind=bearer)
    db.commit()


def mock_roles(app, name, kind):
    """Loads and assigns default roles for mocked objects"""
    Class = orm.get_class(kind)
    obj = Class.find(app.db, name=name)
    default_roles = get_default_roles()
    for role in default_roles:
        add_role(app.db, role)
    app_log.info('Assigning default roles to mocked %s: %s', kind[:-1], name)
    update_roles(db=app.db, obj=obj, kind=kind)
