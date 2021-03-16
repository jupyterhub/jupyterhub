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


def horizontal_filter(func):
    """Decorator to account for horizontal filtering in scope syntax"""

    def ignore(scopename):
        # temporarily remove horizontal filtering if present
        scopename, mark, hor_filter = scopename.partition('!')
        expanded_scope = func(scopename)
        # add the filter back
        full_expanded_scope = {scope + mark + hor_filter for scope in expanded_scope}

        return full_expanded_scope

    return ignore


@horizontal_filter
def _expand_scope(scopename):
    """Returns a set of all subscopes"""

    scopes = get_scopes()
    subscopes = [scopename]

    def _expand_subscopes(index):

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
        _expand_subscopes(index=1)
        # check for "subscopes of sub-subscopes"
        _expand_subscopes(index=index_for_sssc)

    expanded_scope = set(subscopes)

    return expanded_scope


def get_subscopes(*args):
    """Returns a set of all available subscopes for a specified role or list of roles"""

    scope_list = []

    for role in args:
        scope_list.extend(role.scopes)

    scopes = set(chain.from_iterable(list(map(_expand_scope, scope_list))))

    return scopes


def _check_scopes(*args):
    """Check if provided scopes exist"""

    allowed_scopes = get_scopes()
    allowed_filters = ['!user=', '!service=', '!group=', '!server=']
    subscopes = set(
        chain.from_iterable([x for x in allowed_scopes.values() if x is not None])
    )

    for scope in args:
        # check the ! filters
        if '!' in scope:
            if any(filter in scope for filter in allowed_filters):
                scope = scope.split('!', 1)[0]
            else:
                raise NameError(
                    'Scope filter %r in scope %r does not exist',
                    scope.split('!', 1)[1],
                    scope,
                )
        # check if the actual scope syntax exists
        if scope not in allowed_scopes.keys() and scope not in subscopes:
            raise NameError('Scope %r does not exist', scope)


def _overwrite_role(role, role_dict):
    """Overwrites role's description and/or scopes with role_dict if role not 'admin'"""

    for attr in role_dict.keys():
        if attr == 'description' or attr == 'scopes':
            if role.name == 'admin' and role_dict[attr] != getattr(role, attr):
                raise ValueError(
                    'admin role description or scopes cannot be overwritten'
                )
            else:
                setattr(role, attr, role_dict[attr])
                app_log.info('Role %r %r attribute has been changed', role.name, attr)


def add_role(db, role_dict):
    """Adds a new role to database or modifies an existing one"""

    default_roles = get_default_roles()

    if 'name' not in role_dict.keys():
        raise KeyError('Role definition must have a name')
    else:
        name = role_dict['name']
        role = orm.Role.find(db, name)

    description = role_dict.get('description')
    scopes = role_dict.get('scopes')

    # check if the provided scopes exist
    if scopes:
        _check_scopes(*scopes)

    if role is None:
        if not scopes:
            app_log.warning('Warning: New defined role %s has no scopes', name)

        role = orm.Role(name=name, description=description, scopes=scopes)
        db.add(role)
        if role_dict not in default_roles:
            app_log.info('Adding role %s to database', name)
    else:
        _overwrite_role(role, role_dict)

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

    def _check_existence(db, objname, kind, rolename):

        Class = orm.get_class(kind)
        obj = Class.find(db, objname)
        role = orm.Role.find(db, rolename)

        if obj is None:
            raise ValueError("%r of kind %r does not exist" % (objname, kind))
        elif role is None:
            raise ValueError("Role %r does not exist" % rolename)
        else:
            func(db, obj, kind, role)

    return _check_existence


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


def _switch_default_role(db, obj, kind, admin):
    """Switch between default user and admin roles for users/services"""

    user_role = orm.Role.find(db, 'user')
    admin_role = orm.Role.find(db, 'admin')

    def _add_and_remove(db, obj, kind, current_role, new_role):

        if current_role in obj.roles:
            remove_obj(db, objname=obj.name, kind=kind, rolename=current_role.name)
        # only add new default role if the user has no other roles
        if len(obj.roles) < 1:
            add_obj(db, objname=obj.name, kind=kind, rolename=new_role.name)

    if admin:
        _add_and_remove(db, obj, kind, user_role, admin_role)
    else:
        _add_and_remove(db, obj, kind, admin_role, user_role)


def _token_allowed_role(db, token, role):

    """Returns True if token allowed to have requested role through
    comparing the requested scopes with the set of token's owner scopes
    from their roles and their group roles"""

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

    # ignore horizontal filters for comparison
    t_scopes = {
        scope.split('!', 1)[0] if '!' in scope else scope for scope in token_scopes
    }
    o_scopes = {
        scope.split('!', 1)[0] if '!' in scope else scope for scope in owner_scopes
    }

    if t_scopes.issubset(o_scopes):
        return True
    else:
        return False


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

                    if _token_allowed_role(db, obj, role):
                        role.tokens.append(obj)
                        app_log.info(
                            'Adding role %s for %s: %s', role.name, kind[:-1], obj
                        )
                    else:
                        raise ValueError(
                            'Requested token role %r of %r with scopes %r cannot grant more permissions than its owner scopes'
                            % (rolename, obj, role.scopes)
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
            _switch_default_role(db, obj, kind, obj.admin)


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
