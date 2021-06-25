"""Roles utils"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import re
from itertools import chain

from sqlalchemy import func
from tornado.log import app_log

from . import orm
from . import scopes


def get_default_roles():
    """Returns:
    default roles (list): default role definitions as dictionaries:
      {
        'name': role name,
        'description': role description,
        'scopes': list of scopes,
      }
    """
    default_roles = [
        {
            'name': 'user',
            'description': 'Standard user privileges',
            'scopes': [
                'self',
            ],
        },
        {
            'name': 'admin',
            'description': 'Elevated privileges (can do anything)',
            'scopes': [
                'admin:users',
                'admin:servers',
                'tokens',
                'admin:groups',
                'read:services',
                'read:hub',
                'proxy',
                'shutdown',
                'access:services',
                'access:servers',
                'read:roles',
            ],
        },
        {
            'name': 'server',
            'description': 'Post activity only',
            'scopes': [
                'users:activity!user',
                'access:servers!user',
            ],
        },
        {
            'name': 'token',
            'description': 'Token with same permissions as its owner',
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
    tokens
    servers
    access:servers


    Arguments:
      name (str): user name

    Returns:
      expanded scopes (set): set of expanded scopes covering standard user privileges
    """
    scope_list = [
        'users',
        'read:users',
        'read:users:name',
        'read:users:groups',
        'users:activity',
        'read:users:activity',
        'servers',
        'read:servers',
        'tokens',
        'read:tokens',
        'access:servers',
    ]
    return {"{}!user={}".format(scope, name) for scope in scope_list}


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
    """Returns a set of all subscopes
    Arguments:
      scopename (str): name of the scope to expand

    Returns:
      expanded scope (set): set of all scope's subscopes including the scope itself
    """
    expanded_scope = []

    def _add_subscopes(scopename):
        expanded_scope.append(scopename)
        if scopes.scope_definitions[scopename].get('subscopes'):
            for subscope in scopes.scope_definitions[scopename].get('subscopes'):
                _add_subscopes(subscope)

    _add_subscopes(scopename)

    return set(expanded_scope)


def expand_roles_to_scopes(orm_object):
    """Get the scopes listed in the roles of the User/Service/Group/Token
    If User, take into account the user's groups roles as well

    Arguments:
      orm_object: orm.User, orm.Service, orm.Group or orm.APIToken

    Returns:
      expanded scopes (set): set of all expanded scopes for the orm object
    """
    if not isinstance(orm_object, orm.Base):
        raise TypeError(f"Only orm objects allowed, got {orm_object}")

    pass_roles = []
    pass_roles.extend(orm_object.roles)

    if isinstance(orm_object, orm.User):
        for group in orm_object.groups:
            pass_roles.extend(group.roles)

    expanded_scopes = _get_subscopes(*pass_roles, owner=orm_object)

    return expanded_scopes


def _get_subscopes(*roles, owner=None):
    """Returns a set of all available subscopes for a specified role or list of roles

    Arguments:
      roles (obj): orm.Roles
      owner (obj, optional): orm.User or orm.Service as owner of orm.APIToken

    Returns:
      expanded scopes (set): set of all expanded scopes for the role(s)
    """
    scopes = set()

    for role in roles:
        scopes.update(role.scopes)

    expanded_scopes = set(chain.from_iterable(list(map(_expand_scope, scopes))))
    # transform !user filter to !user=ownername
    for scope in expanded_scopes.copy():
        base_scope, _, filter = scope.partition('!')
        if filter == 'user':
            expanded_scopes.remove(scope)
            if isinstance(owner, orm.APIToken):
                token_owner = owner.user
                if token_owner is None:
                    token_owner = owner.service
                name = token_owner.name
            else:
                name = owner.name
            trans_scope = f'{base_scope}!user={name}'
            expanded_scopes.add(trans_scope)
    if 'self' in expanded_scopes:
        expanded_scopes.remove('self')
        if owner and isinstance(owner, orm.User):
            expanded_scopes |= expand_self_scope(owner.name)

    return expanded_scopes


def _check_scopes(*args, rolename=None):
    """Check if provided scopes exist

    Arguments:
      scope (str): name of the scope to check
      or
      scopes (list): list of scopes to check

    Raises NameError if scope does not exist
    """

    allowed_scopes = set(scopes.scope_definitions.keys())
    allowed_filters = ['!user=', '!service=', '!group=', '!server=', '!user']

    if rolename:
        log_role = f"for role {rolename}"
    else:
        log_role = ""

    for scope in args:
        scopename, _, filter_ = scope.partition('!')
        if scopename not in allowed_scopes:
            raise NameError(f"Scope '{scope}' {log_role} does not exist")
        if filter_:
            full_filter = f"!{filter_}"
            if not any(f in scope for f in allowed_filters):
                raise NameError(
                    f"Scope filter '{full_filter}' in scope '{scope}' {log_role} does not exist"
                )


def _overwrite_role(role, role_dict):
    """Overwrites role's description and/or scopes with role_dict if role not 'admin'"""
    for attr in role_dict.keys():
        if attr == 'description' or attr == 'scopes':
            if role.name == 'admin':
                admin_role_spec = [
                    r for r in get_default_roles() if r['name'] == 'admin'
                ][0]
                if role_dict[attr] != admin_role_spec[attr]:
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
        _check_scopes(*scopes, rolename=role_dict['name'])

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
    """Adds a role for users, services, groups or tokens"""
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
    """Removes a role for users, services, groups or tokens"""
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
    """Checks if requested role for token does not grant the token
    higher permissions than the token's owner has

    Returns:
      True if requested permissions are within the owner's permissions, False otherwise
    """
    owner = token.user
    if owner is None:
        owner = token.service

    if owner is None:
        raise ValueError(f"Owner not found for {token}")

    expanded_scopes = _get_subscopes(role, owner=owner)

    implicit_permissions = {'all', 'read:all'}
    explicit_scopes = expanded_scopes - implicit_permissions
    # ignore horizontal filters
    no_filter_scopes = {
        scope.split('!', 1)[0] if '!' in scope else scope for scope in explicit_scopes
    }
    # find the owner's scopes
    expanded_owner_scopes = expand_roles_to_scopes(owner)
    # ignore horizontal filters
    no_filter_owner_scopes = {
        scope.split('!', 1)[0] if '!' in scope else scope
        for scope in expanded_owner_scopes
    }
    disallowed_scopes = no_filter_scopes.difference(no_filter_owner_scopes)
    if not disallowed_scopes:
        # no scopes requested outside owner's own scopes
        return True
    else:
        app_log.warning(
            f"Token requesting scopes exceeding owner {owner.name}: {disallowed_scopes}"
        )
        return False


def assign_default_roles(db, entity):
    """Assigns default role to an entity:
    users and services get 'user' role, or admin role if they have admin flag
    tokens get 'token' role
    """
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
        kind = type(entity).__name__
        app_log.debug(f'Assigning default roles to {kind} {entity.name}')
        _switch_default_role(db, entity, entity.admin)


def update_roles(db, entity, roles):
    """Updates object's roles checking for requested permissions
    if object is orm.APIToken
    """
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


def check_for_default_roles(db, bearer):
    """Checks that role bearers have at least one role (default if none).
    Groups can be without a role
    """
    Class = orm.get_class(bearer)
    if Class in {orm.Group, orm.Service}:
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
