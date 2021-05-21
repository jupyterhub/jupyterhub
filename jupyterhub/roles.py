"""Roles utils"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import re
from itertools import chain

from sqlalchemy import func
from tornado.log import app_log

from . import orm


def get_default_roles():
    """Returns a list of default role dictionaries"""

    default_roles = [
        {
            'name': 'user',
            'description': 'Standard user privileges',
            'scopes': ['self'],
        },
        {
            'name': 'admin',
            'description': 'Admin privileges (currently can do everything)',
            'scopes': [
                'admin:users',
                'admin:users:servers',
                'users:tokens',
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
            'scopes': [
                'users:activity!user'
            ],  # TO DO - fix scope to refer to only self once implemented
        },
        {
            'name': 'token',
            'description': 'Token with same rights as token owner',
            'scopes': ['all'],
        },
    ]
    return default_roles


def expand_self_scope(name):
    """
    Users have a metascope 'self' that should be expanded to standard user privileges.
    At the moment that is a user-filtered version (optional read) access to
    users
    users:name
    users:groups
    users:activity
    users:servers
    users:tokens
    """
    scope_list = [
        'users',
        'users:name',
        'users:groups',
        'users:activity',
        'users:servers',
        'users:tokens',
    ]
    read_scope_list = ['read:' + scope for scope in scope_list]
    scope_list.extend(read_scope_list)
    return {"{}!user={}".format(scope, name) for scope in scope_list}


def _get_scope_hierarchy():
    """
    Returns a dictionary of scopes:
    scopes.keys() = scopes of highest level and scopes that have their own subscopes
    scopes.values() = a list of first level subscopes or None
    """

    scopes = {
        'self': None,
        'all': None,
        'admin:users': ['admin:users:auth_state', 'users'],
        'users': ['read:users', 'users:activity'],
        'read:users': [
            'read:users:name',
            'read:users:groups',
            'read:users:activity',
        ],
        'users:activity': ['read:users:activity'],
        'users:tokens': ['read:users:tokens'],
        'admin:users:servers': ['admin:users:server_state', 'users:servers'],
        'users:servers': ['read:users:servers'],
        'read:users:servers': ['read:users:name'],
        'admin:groups': ['groups'],
        'groups': ['read:groups'],
        'read:services': None,
        'read:hub': None,
        'proxy': None,
        'shutdown': None,
    }

    return scopes


def horizontal_filter(func):
    """Decorator to account for horizontal filtering in scope syntax"""

    def expand_server_filter(hor_filter):
        resource, mark, value = hor_filter.partition('=')
        if resource == 'server':
            user, mark, server = value.partition('/')
            return f'read:users:name!user={user}'

    def ignore(scopename):
        # temporarily remove horizontal filtering if present
        scopename, mark, hor_filter = scopename.partition('!')
        expanded_scope = func(scopename)
        # add the filter back
        full_expanded_scope = {scope + mark + hor_filter for scope in expanded_scope}
        server_filter = expand_server_filter(hor_filter)
        if server_filter:
            full_expanded_scope.add(server_filter)
        return full_expanded_scope

    return ignore


@horizontal_filter
def _expand_scope(scopename):
    """Returns a set of all subscopes"""

    scopes = _get_scope_hierarchy()
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


def expand_roles_to_scopes(orm_object):
    """Get the scopes listed in the roles of the User/Service/Group/Token
    If User, take into account the user's groups roles as well"""
    if not isinstance(orm_object, orm.Base):
        raise TypeError(f"Only orm objects allowed, got {orm_object}")

    pass_roles = orm_object.roles

    if isinstance(orm_object, orm.User):
        groups_roles = []
        for group in orm_object.groups:
            groups_roles.extend(group.roles)
        pass_roles.extend(groups_roles)

    scopes = _get_subscopes(*pass_roles, owner=orm_object)

    return scopes


def _get_subscopes(*args, owner=None):
    """Returns a set of all available subscopes for a specified role or list of roles"""

    scope_list = []

    for role in args:
        scope_list.extend(role.scopes)

    scopes = set(chain.from_iterable(list(map(_expand_scope, scope_list))))

    # transform !user filter to !user=ownername
    for scope in scopes:
        base_scope, _, filter = scope.partition('!')
        if filter == 'user':
            scopes.remove(scope)
            if isinstance(owner, orm.APIToken):
                token_owner = owner.user
                if token_owner is None:
                    token_owner = owner.service
                name = token_owner.name
            else:
                name = owner.name
            trans_scope = f'{base_scope}!user={name}'
            scopes.add(trans_scope)

    if 'self' in scopes:
        scopes.remove('self')
        if owner and isinstance(owner, orm.User):
            scopes |= expand_self_scope(owner.name)

    return scopes


def _check_scopes(*args):
    """Check if provided scopes exist"""

    allowed_scopes = _get_scope_hierarchy()
    allowed_filters = ['!user=', '!service=', '!group=', '!server=', '!user']
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
                if role_dict[attr] != getattr(role, attr):
                    setattr(role, attr, role_dict[attr])
                    app_log.info(
                        'Role %r %r attribute has been changed', role.name, attr
                    )


_role_name_pattern = re.compile(r'^[a-z][a-z0-9\-_~\.]{1,253}[a-z0-9]$')


def _validate_role_name(name):
    """Ensure a role has a valid name

    Raises ValueError if role name is invalid
    """
    if not _role_name_pattern.match(name):
        raise ValueError(
            f"Invalid role name: {name!r}."
            " Role names must:\n"
            " - be 3-255 characters\n"
            " - contain only lowercase ascii letters, numbers, and URL unreserved special characters '-.~_'\n"
            " - start with a letter\n"
            " - end with letter or number\n"
        )
    return True


def create_role(db, role_dict):
    """Adds a new role to database or modifies an existing one"""

    default_roles = get_default_roles()

    if 'name' not in role_dict.keys():
        raise KeyError('Role definition must have a name')
    else:
        name = role_dict['name']
        _validate_role_name(name)
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
            app_log.info('Role %s added to database', name)
    else:
        _overwrite_role(role, role_dict)

    db.commit()


def delete_role(db, rolename):
    """Removes a role from database"""

    # default roles are not removable
    default_roles = get_default_roles()
    if any(role['name'] == rolename for role in default_roles):
        raise ValueError('Default role %r cannot be removed', rolename)

    role = orm.Role.find(db, rolename)
    if role:
        db.delete(role)
        db.commit()
        app_log.info('Role %s has been deleted', rolename)
    else:
        raise NameError('Cannot remove role %r that does not exist', rolename)


def existing_only(func):
    """Decorator for checking if objects and roles exist"""

    def _check_existence(db, entity, rolename):
        role = orm.Role.find(db, rolename)
        if entity is None:
            raise ValueError(
                "%r of kind %r does not exist" % (entity, type(entity).__name__)
            )
        elif role is None:
            raise ValueError("Role %r does not exist" % rolename)
        else:
            func(db, entity, role)

    return _check_existence


@existing_only
def grant_role(db, entity, rolename):
    """Adds a role for users, services or tokens"""
    if isinstance(entity, orm.APIToken):
        entity_repr = entity
    else:
        entity_repr = entity.name

    if rolename not in entity.roles:
        entity.roles.append(rolename)
        db.commit()
        app_log.info(
            'Adding role %s for %s: %s',
            rolename.name,
            type(entity).__name__,
            entity_repr,
        )


@existing_only
def strip_role(db, entity, rolename):
    """Removes a role for users, services or tokens"""
    if isinstance(entity, orm.APIToken):
        entity_repr = entity
    else:
        entity_repr = entity.name
    if rolename in entity.roles:
        entity.roles.remove(rolename)
        db.commit()
        app_log.info(
            'Removing role %s for %s: %s',
            rolename.name,
            type(entity).__name__,
            entity_repr,
        )


def _switch_default_role(db, obj, admin):
    """Switch between default user/service and admin roles for users/services"""
    user_role = orm.Role.find(db, 'user')
    admin_role = orm.Role.find(db, 'admin')

    def add_and_remove(db, obj, current_role, new_role):
        if current_role in obj.roles:
            strip_role(db, entity=obj, rolename=current_role.name)
        # only add new default role if the user has no other roles
        if len(obj.roles) < 1:
            grant_role(db, entity=obj, rolename=new_role.name)

    if admin:
        add_and_remove(db, obj, user_role, admin_role)
    else:
        add_and_remove(db, obj, admin_role, user_role)


def _token_allowed_role(db, token, role):

    """Returns True if token allowed to have requested role through
    comparing the requested scopes with the set of token's owner scopes"""

    owner = token.user
    if owner is None:
        owner = token.service

    if owner is None:
        raise ValueError(f"Owner not found for {token}")

    token_scopes = _get_subscopes(role, owner=owner)

    implicit_permissions = {'all', 'read:all'}
    explicit_scopes = token_scopes - implicit_permissions
    # ignore horizontal filters
    raw_scopes = {
        scope.split('!', 1)[0] if '!' in scope else scope for scope in explicit_scopes
    }
    # find the owner's scopes
    owner_scopes = expand_roles_to_scopes(owner)
    # ignore horizontal filters
    raw_owner_scopes = {
        scope.split('!', 1)[0] if '!' in scope else scope for scope in owner_scopes
    }
    disallowed_scopes = raw_scopes.difference(raw_owner_scopes)
    if not disallowed_scopes:
        # no scopes requested outside owner's own scopes
        return True
    else:
        app_log.warning(
            f"Token requesting scopes exceeding owner {owner.name}: {disallowed_scopes}"
        )
        return False


def assign_default_roles(db, entity):
    """Assigns the default roles to an entity:
    users and services get 'user' role, or admin role if they have admin flag
    Tokens get 'token' role"""
    if isinstance(entity, orm.Group):
        pass
    elif isinstance(entity, orm.APIToken):
        app_log.debug('Assigning default roles to tokens')
        default_token_role = orm.Role.find(db, 'token')
        if not entity.roles and (entity.user or entity.service) is not None:
            default_token_role.tokens.append(entity)
            app_log.info('Added role %s to token %s', default_token_role.name, entity)
        db.commit()
    # users and services can have 'user' or 'admin' roles as default
    else:
        # todo: when we deprecate admin flag: replace with role check
        app_log.debug('Assigning default roles to %s', type(entity).__name__)
        _switch_default_role(db, entity, entity.admin)


def update_roles(db, entity, roles):
    """Updates object's roles"""
    standard_permissions = {'all', 'read:all'}
    for rolename in roles:
        if isinstance(entity, orm.APIToken):
            role = orm.Role.find(db, rolename)
            if role:
                app_log.debug(
                    'Checking token permissions against requested role %s', rolename
                )
                if _token_allowed_role(db, entity, role):
                    role.tokens.append(entity)
                    app_log.info('Adding role %s to token: %s', role.name, entity)
                else:
                    raise ValueError(
                        f'Requested token role {rolename} of {entity} has more permissions than the token owner'
                    )
            else:
                raise NameError('Role %r does not exist' % rolename)
        else:
            app_log.debug('Assigning default roles to %s', type(entity).__name__)
            grant_role(db, entity=entity, rolename=rolename)


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
                    update_roles(db, token, roles=[token_role.name])


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
            assign_default_roles(db, obj)
    db.commit()


def mock_roles(app, name, kind):
    """Loads and assigns default roles for mocked objects"""
    Class = orm.get_class(kind)
    obj = Class.find(app.db, name=name)
    default_roles = get_default_roles()
    for role in default_roles:
        create_role(app.db, role)
    app_log.info('Assigning default roles to mocked %s: %s', kind[:-1], name)
    assign_default_roles(db=app.db, entity=obj)
