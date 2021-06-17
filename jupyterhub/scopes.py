"""
General scope definitions and utilities

Scope variable nomenclature
---------------------------
scopes: list of scopes with abbreviations (e.g., in role definition)
expanded scopes: set of expanded scopes without abbreviations (i.e., resolved metascopes, filters and subscopes)
parsed scopes: dictionary JSON like format of expanded scopes
intersection : set of expanded scopes as intersection of 2 expanded scope sets
identify scopes: set of expanded scopes needed for identify (whoami) endpoints
"""
import functools
import inspect
import warnings
from enum import Enum
from functools import lru_cache

import sqlalchemy as sa
from tornado import web
from tornado.log import app_log

from . import orm
from . import roles

"""when modifying the scope definitions, make sure that `docs/source/rbac/generate-scope-table.py` is run
   so that changes are reflected in the documentation and REST API description."""
scope_definitions = {
    '(no_scope)': {'description': 'Identify the owner of the requesting entity.'},
    'self': {
        'description': 'Your own resources',
        'doc_description': 'The user’s own resources _(metascope for users, resolves to (no_scope) for services)_',
    },
    'all': {
        'description': 'Anything you have access to',
        'doc_description': 'Everything that the token-owning entity can access _(metascope for tokens)_',
    },
    'admin:users': {
        'description': 'Read, write, create and delete users and their authentication state, not including their servers or tokens.',
        'subscopes': ['admin:auth_state', 'users', 'read:roles:users'],
    },
    'admin:auth_state': {'description': 'Read a user’s authentication state.'},
    'users': {
        'description': 'Read and write permissions to user models (excluding servers, tokens and authentication state).',
        'subscopes': ['read:users', 'users:activity'],
    },
    'read:users': {
        'description': 'Read user models (excluding including servers, tokens and authentication state).',
        'subscopes': [
            'read:users:name',
            'read:users:groups',
            'read:users:activity',
        ],
    },
    'read:users:name': {'description': 'Read names of users.'},
    'read:users:groups': {'description': 'Read users’ group membership.'},
    'read:users:activity': {'description': 'Read time of last user activity.'},
    'read:roles': {
        'description': 'Read role assignments.',
        'subscopes': ['read:roles:users', 'read:roles:services', 'read:roles:groups'],
    },
    'read:roles:users': {'description': 'Read user role assignments.'},
    'read:roles:services': {'description': 'Read service role assignments.'},
    'read:roles:groups': {'description': 'Read group role assignments.'},
    'users:activity': {
        'description': 'Update time of last user activity.',
        'subscopes': ['read:users:activity'],
    },
    'admin:servers': {
        'description': 'Read, start, stop, create and delete user servers and their state.',
        'subscopes': ['admin:server_state', 'servers'],
    },
    'admin:server_state': {'description': 'Read and write users’ server state.'},
    'servers': {
        'description': 'Start and stop user servers.',
        'subscopes': ['read:servers'],
    },
    'read:servers': {
        'description': 'Read users’ names and their server models (excluding the server state).',
        'subscopes': ['read:users:name'],
    },
    'tokens': {
        'description': 'Read, write, create and delete user tokens.',
        'subscopes': ['read:tokens'],
    },
    'read:tokens': {'description': 'Read user tokens.'},
    'admin:groups': {
        'description': 'Read and write group information, create and delete groups.',
        'subscopes': ['groups', 'read:roles:groups'],
    },
    'groups': {
        'description': 'Read and write group information, including adding/removing users to/from groups.',
        'subscopes': ['read:groups'],
    },
    'read:groups': {
        'description': 'Read group models.',
        'subscopes': ['read:groups:name'],
    },
    'read:groups:name': {'description': 'Read group names.'},
    'read:services': {
        'description': 'Read service models.',
        'subscopes': ['read:services:name'],
    },
    'read:services:name': {'description': 'Read service names.'},
    'read:hub': {'description': 'Read detailed information about the Hub.'},
    'access:servers': {
        'description': 'Access user servers via API or browser.',
    },
    'access:services': {
        'description': 'Access services via API or browser.',
    },
    'proxy': {
        'description': 'Read information about the proxy’s routing table, sync the Hub with the proxy and notify the Hub about a new proxy.'
    },
    'shutdown': {'description': 'Shutdown the hub.'},
}


class Scope(Enum):
    ALL = True


def _intersect_expanded_scopes(scopes_a, scopes_b, db=None):
    """Intersect two sets of scopes by comparing their permissions

    Arguments:
      scopes_a, scopes_b: sets of expanded scopes
      db (optional): db connection for resolving group membership

    Returns:
      intersection: set of expanded scopes as intersection of the arguments

    If db is given, group membership will be accounted for in intersections,
    Otherwise, it can result in lower than intended permissions,
          (i.e. users!group=x & users!user=y will be empty, even if user y is in group x.)
    """
    empty_set = frozenset()

    # cached lookups for group membership of users and servers
    @lru_cache()
    def groups_for_user(username):
        """Get set of group names for a given username"""
        user = db.query(orm.User).filter_by(name=username).first()
        if user is None:
            return empty_set
        else:
            return {group.name for group in user.groups}

    @lru_cache()
    def groups_for_server(server):
        """Get set of group names for a given server"""
        username, _, servername = server.partition("/")
        return groups_for_user(username)

    parsed_scopes_a = parse_scopes(scopes_a)
    parsed_scopes_b = parse_scopes(scopes_b)

    common_bases = parsed_scopes_a.keys() & parsed_scopes_b.keys()

    common_filters = {}
    warned = False
    for base in common_bases:
        filters_a = parsed_scopes_a[base]
        filters_b = parsed_scopes_b[base]
        if filters_a == Scope.ALL:
            common_filters[base] = filters_b
        elif filters_b == Scope.ALL:
            common_filters[base] = filters_a
        else:
            common_entities = filters_a.keys() & filters_b.keys()
            all_entities = filters_a.keys() | filters_b.keys()

            # if we don't have a db session, we can't check group membership
            # warn *if* there are non-overlapping user= and group= filters that we can't check
            if (
                db is None
                and not warned
                and 'group' in all_entities
                and ('user' in all_entities or 'server' in all_entities)
            ):
                # this could resolve wrong if there's a user or server only on one side and a group only on the other
                # check both directions: A has group X not in B group list AND B has user Y not in A user list
                for a, b in [(filters_a, filters_b), (filters_b, filters_a)]:
                    for b_key in ('user', 'server'):
                        if (
                            not warned
                            and "group" in a
                            and b_key in b
                            and a["group"].difference(b.get("group", []))
                            and b[b_key].difference(a.get(b_key, []))
                        ):
                            warnings.warn(
                                f"{base}[!{b_key}={b[b_key]}, !group={a['group']}] combinations of filters present,"
                                " without db access. Intersection between not considered."
                                " May result in lower than intended permissions.",
                                UserWarning,
                            )
                            warned = True

            common_filters[base] = {
                entity: filters_a[entity] & filters_b[entity]
                for entity in common_entities
            }

            # resolve hierarchies (group/user/server) in both directions
            common_servers = common_filters[base].get("server", set())
            common_users = common_filters[base].get("user", set())

            for a, b in [(filters_a, filters_b), (filters_b, filters_a)]:
                if 'server' in a and b.get('server') != a['server']:
                    # skip already-added servers (includes overlapping servers)
                    servers = a['server'].difference(common_servers)

                    # resolve user/server hierarchy
                    if servers and 'user' in b:
                        for server in servers:
                            username, _, servername = server.partition("/")
                            if username in b['user']:
                                common_servers.add(server)

                    # resolve group/server hierarchy if db available
                    servers = servers.difference(common_servers)
                    if db is not None and servers and 'group' in b:
                        for server in servers:
                            server_groups = groups_for_server(server)
                            if server_groups & b['group']:
                                common_servers.add(server)

                # resolve group/user hierarchy if db available and user sets aren't identical
                if (
                    db is not None
                    and 'user' in a
                    and 'group' in b
                    and b.get('user') != a['user']
                ):
                    # skip already-added users (includes overlapping users)
                    users = a['user'].difference(common_users)
                    for username in users:
                        groups = groups_for_user(username)
                        if groups & b["group"]:
                            common_users.add(username)

            # add server filter if there wasn't one before
            if common_servers and "server" not in common_filters[base]:
                common_filters[base]["server"] = common_servers

            # add user filter if it's non-empty and there wasn't one before
            if common_users and "user" not in common_filters[base]:
                common_filters[base]["user"] = common_users

    return unparse_scopes(common_filters)


def get_scopes_for(orm_object):
    """Find scopes for a given user or token from their roles and resolve permissions

    Arguments:
      orm_object: orm object or User wrapper

    Returns:
      expanded scopes (set) for the orm object
      or
      intersection (set) if orm_object == orm.APIToken
    """
    expanded_scopes = set()
    if orm_object is None:
        return expanded_scopes

    if not isinstance(orm_object, orm.Base):
        from .user import User

        if isinstance(orm_object, User):
            orm_object = orm_object.orm_user
        else:
            raise TypeError(
                f"Only allow orm objects or User wrappers, got {orm_object}"
            )

    if isinstance(orm_object, orm.APIToken):
        app_log.warning(f"Authenticated with token {orm_object}")
        owner = orm_object.user or orm_object.service
        token_scopes = roles.expand_roles_to_scopes(orm_object)
        if orm_object.client_id != "jupyterhub":
            # oauth tokens can be used to access the service issuing the token,
            # assuming the owner itself still has permission to do so
            spawner = orm_object.oauth_client.spawner
            if spawner:
                token_scopes.add(
                    f"access:servers!server={spawner.user.name}/{spawner.name}"
                )
            else:
                service = orm_object.oauth_client.service
                if service:
                    token_scopes.add(f"access:services!service={service.name}")
                else:
                    app_log.warning(
                        f"Token {orm_object} has no associated service or spawner!"
                    )

        owner_scopes = roles.expand_roles_to_scopes(owner)

        if token_scopes == {'all'}:
            # token_scopes is only 'all', return owner scopes as-is
            # short-circuit common case where we don't need to compute an intersection
            return owner_scopes

        if 'all' in token_scopes:
            token_scopes.remove('all')
            token_scopes |= owner_scopes

        intersection = _intersect_expanded_scopes(
            token_scopes,
            owner_scopes,
            db=sa.inspect(orm_object).session,
        )
        discarded_token_scopes = token_scopes - intersection

        # Not taking symmetric difference here because token owner can naturally have more scopes than token
        if discarded_token_scopes:
            app_log.warning(
                "discarding scopes [%s], not present in owner roles"
                % ", ".join(discarded_token_scopes)
            )
        expanded_scopes = intersection
    else:
        expanded_scopes = roles.expand_roles_to_scopes(orm_object)
    return expanded_scopes


def _needs_scope_expansion(filter_, filter_value, sub_scope):
    """
    Check if there is a requirements to expand the `group` scope to individual `user` scopes.
    Assumptions:
    filter_ != Scope.ALL
    """
    if not (filter_ == 'user' and 'group' in sub_scope):
        return False
    if 'user' in sub_scope:
        return filter_value not in sub_scope['user']
    else:
        return True


def _check_user_in_expanded_scope(handler, user_name, scope_group_names):
    """Check if username is present in set of allowed groups"""
    user = handler.find_user(user_name)
    if user is None:
        raise web.HTTPError(404, "No access to resources or resources not found")
    group_names = {group.name for group in user.groups}
    return bool(set(scope_group_names) & group_names)


def _check_scope_access(api_handler, req_scope, **kwargs):
    """Check if scopes satisfy requirements
    Returns True for (potentially restricted) access, False for refused access
    """
    # Parse user name and server name together
    try:
        api_name = api_handler.request.path
    except AttributeError:
        api_name = type(api_handler).__name__
    if 'user' in kwargs and 'server' in kwargs:
        kwargs['server'] = "{}/{}".format(kwargs['user'], kwargs['server'])
    if req_scope not in api_handler.parsed_scopes:
        app_log.debug("No access to %s via %s", api_name, req_scope)
        return False
    if api_handler.parsed_scopes[req_scope] == Scope.ALL:
        app_log.debug("Unrestricted access to %s via %s", api_name, req_scope)
        return True
    # Apply filters
    sub_scope = api_handler.parsed_scopes[req_scope]
    if not kwargs:
        app_log.debug(
            "Client has restricted access to %s via %s. Internal filtering may apply",
            api_name,
            req_scope,
        )
        return True
    for (filter_, filter_value) in kwargs.items():
        if filter_ in sub_scope and filter_value in sub_scope[filter_]:
            app_log.debug("Argument-based access to %s via %s", api_name, req_scope)
            return True
        if _needs_scope_expansion(filter_, filter_value, sub_scope):
            group_names = sub_scope['group']
            if _check_user_in_expanded_scope(api_handler, filter_value, group_names):
                app_log.debug("Restricted client access supported with group expansion")
                return True
    app_log.debug(
        "Client access refused; filters do not match API endpoint %s request" % api_name
    )
    raise web.HTTPError(404, "No access to resources or resources not found")


def parse_scopes(scope_list):
    """
    Parses scopes and filters in something akin to JSON style

    For instance, scope list ["users", "groups!group=foo", "servers!server=user/bar", "servers!server=user/baz"]
    would lead to scope model
    {
       "users":scope.ALL,
       "admin:users":{
          "user":[
             "alice"
          ]
       },
       "servers":{
          "server":[
             "user/bar",
             "user/baz"
          ]
       }
    }
    """
    parsed_scopes = {}
    for scope in scope_list:
        base_scope, _, filter_ = scope.partition('!')
        if not filter_:
            parsed_scopes[base_scope] = Scope.ALL
        elif base_scope not in parsed_scopes:
            parsed_scopes[base_scope] = {}

        if parsed_scopes[base_scope] != Scope.ALL:
            key, _, value = filter_.partition('=')
            if key not in parsed_scopes[base_scope]:
                parsed_scopes[base_scope][key] = set([value])
            else:
                parsed_scopes[base_scope][key].add(value)
    return parsed_scopes


def unparse_scopes(parsed_scopes):
    """Turn a parsed_scopes dictionary back into a expanded scopes set"""
    expanded_scopes = set()
    for base, filters in parsed_scopes.items():
        if filters == Scope.ALL:
            expanded_scopes.add(base)
        else:
            for entity, names_list in filters.items():
                for name in names_list:
                    expanded_scopes.add(f'{base}!{entity}={name}')
    return expanded_scopes


def needs_scope(*scopes):
    """Decorator to restrict access to users or services with the required scope"""

    for scope in scopes:
        if scope not in scope_definitions:
            raise ValueError(f"Scope {scope} is not a valid scope")

    def scope_decorator(func):
        @functools.wraps(func)
        def _auth_func(self, *args, **kwargs):
            sig = inspect.signature(func)
            bound_sig = sig.bind(self, *args, **kwargs)
            bound_sig.apply_defaults()
            # Load scopes in case they haven't been loaded yet
            if not hasattr(self, 'expanded_scopes'):
                self.expanded_scopes = {}
                self.parsed_scopes = {}

            s_kwargs = {}
            for resource in {'user', 'server', 'group', 'service'}:
                resource_name = resource + '_name'
                if resource_name in bound_sig.arguments:
                    resource_value = bound_sig.arguments[resource_name]
                    s_kwargs[resource] = resource_value
            for scope in scopes:
                app_log.debug("Checking access via scope %s", scope)
                has_access = _check_scope_access(self, scope, **s_kwargs)
                if has_access:
                    return func(self, *args, **kwargs)
            try:
                end_point = self.request.path
            except AttributeError:
                end_point = self.__name__
            app_log.warning(
                "Not authorizing access to {}. Requires any of [{}], not derived from scopes [{}]".format(
                    end_point, ", ".join(scopes), ", ".join(self.expanded_scopes)
                )
            )
            raise web.HTTPError(
                403,
                "Action is not authorized with current scopes; requires any of [{}]".format(
                    ", ".join(scopes)
                ),
            )

        return _auth_func

    return scope_decorator


def identify_scopes(obj):
    """Return 'identify' scopes for an orm object

    Arguments:
      obj: orm.User or orm.Service

    Returns:
      identify scopes (set): set of scopes needed for 'identify' endpoints
    """
    if isinstance(obj, orm.User):
        return {f"read:users:{field}!user={obj.name}" for field in {"name", "groups"}}
    elif isinstance(obj, orm.Service):
        return {f"read:services:{field}!service={obj.name}" for field in {"name"}}
    else:
        raise TypeError(f"Expected orm.User or orm.Service, got {obj!r}")


def check_scope_filter(sub_scope, orm_resource, kind):
    """Return whether a sub_scope filter applies to a given resource.

    param sub_scope: parsed_scopes filter (i.e. dict or Scope.ALL)
    param orm_resource: User or Service or Group or Spawner
    param kind: 'user' or 'service' or 'group' or 'server'.

    Returns True or False
    """
    if sub_scope is Scope.ALL:
        return True
    elif kind in sub_scope and orm_resource.name in sub_scope[kind]:
        return True

    if kind == 'server':
        server_format = f"{orm_resource.user.name}/{orm_resource.name}"
        if server_format in sub_scope.get(kind, []):
            return True
        # Fall back on checking if we have user access
        if 'user' in sub_scope and orm_resource.user.name in sub_scope['user']:
            return True
        # Fall back on checking if we have group access for this user
        orm_resource = orm_resource.user
        kind = 'user'

    if kind == 'user' and 'group' in sub_scope:
        group_names = {group.name for group in orm_resource.groups}
        user_in_group = bool(group_names & set(sub_scope['group']))
        if user_in_group:
            return True
    return False


def describe_parsed_scopes(parsed_scopes, username=None):
    """Return list of descriptions of parsed scopes

    Highly detailed, often redundant descriptions
    """
    descriptions = []
    for scope, filters in parsed_scopes.items():
        base_text = scope_definitions[scope]["description"]
        if filters == Scope.ALL:
            # no filter
            filter_text = ""
        else:
            filter_chunks = []
            for kind, names in filters.items():
                if kind == 'user' and names == {username}:
                    filter_chunks.append("only you")
                else:
                    kind_text = kind
                    if kind == 'group':
                        kind_text = "users in group"
                    if len(names) == 1:
                        filter_chunks.append(f"{kind}: {list(names)[0]}")
                    else:
                        filter_chunks.append(f"{kind}s: {', '.join(names)}")
            filter_text = "; or ".join(filter_chunks)
        descriptions.append(
            {
                "scope": scope,
                "description": scope_definitions[scope]["description"],
                "filter": filter_text,
            }
        )
    return descriptions


def describe_raw_scopes(raw_scopes, username=None):
    """Return list of descriptions of raw scopes

    A much shorter list than describe_parsed_scopes
    """
    descriptions = []
    for raw_scope in raw_scopes:
        scope, _, filter_ = raw_scope.partition("!")
        base_text = scope_definitions[scope]["description"]
        if not filter_:
            # no filter
            filter_text = ""
        elif filter_ == "user":
            filter_text = "only you"
        else:
            kind, _, name = filter_.partition("=")
            if kind == "user" and name == username:
                filter_text = "only you"
            else:
                kind_text = kind
                if kind == 'group':
                    kind_text = "users in group"
                filter_text = f"{kind_text} {name}"
        descriptions.append(
            {
                "scope": scope,
                "description": scope_definitions[scope]["description"],
                "filter": filter_text,
            }
        )
    return descriptions
