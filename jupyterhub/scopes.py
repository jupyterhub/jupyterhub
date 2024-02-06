"""
General scope definitions and utilities

Scope functions generally return _immutable_ collections,
such as `frozenset` to avoid mutating cached values.
If needed, mutable copies can be made, e.g. `set(frozen_scopes)`

Scope variable nomenclature
---------------------------
scopes or 'raw' scopes: collection of scopes that may contain abbreviations (e.g., in role definition)
expanded scopes: set of expanded scopes without abbreviations (i.e., resolved metascopes, filters, and subscopes)
parsed scopes: dictionary format of expanded scopes (`read:users!user=name` -> `{'read:users': {user: [name]}`)
intersection : set of expanded scopes as intersection of 2 expanded scope sets
identify scopes: set of expanded scopes needed for identify (whoami) endpoints
reduced scopes: expanded scopes that have been reduced
"""

import functools
import inspect
import re
import warnings
from enum import Enum
from functools import lru_cache
from itertools import chain
from textwrap import indent

import sqlalchemy as sa
from tornado import web
from tornado.log import app_log

from . import orm, roles
from ._memoize import DoNotCache, FrozenDict, lru_cache_key

"""when modifying the scope definitions, make sure that `docs/source/rbac/generate-scope-table.py` is run
   so that changes are reflected in the documentation and REST API description."""
scope_definitions = {
    '(no_scope)': {'description': 'Identify the owner of the requesting entity.'},
    'self': {
        'description': 'Your own resources',
        'doc_description': 'The user’s own resources _(metascope for users, resolves to (no_scope) for services)_',
    },
    'inherit': {
        'description': 'Anything you have access to',
        'doc_description': 'Everything that the token-owning entity can access _(metascope for tokens)_',
    },
    'admin-ui': {
        'description': 'Access the admin page.',
        'doc_description': 'Access the admin page. Permission to take actions via the admin page granted separately.',
    },
    'admin:users': {
        'description': 'Read, write, create and delete users and their authentication state, not including their servers or tokens.',
        'subscopes': ['admin:auth_state', 'users', 'read:roles:users', 'delete:users'],
    },
    'admin:auth_state': {'description': 'Read a user’s authentication state.'},
    'users': {
        'description': 'Read and write permissions to user models (excluding servers, tokens and authentication state).',
        'subscopes': ['read:users', 'list:users', 'users:activity'],
    },
    'delete:users': {
        'description': "Delete users.",
    },
    'list:users': {
        'description': 'List users, including at least their names.',
        'subscopes': ['read:users:name'],
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
        'subscopes': ['read:servers', 'delete:servers'],
    },
    'read:servers': {
        'description': 'Read users’ names and their server models (excluding the server state).',
        'subscopes': ['read:users:name'],
    },
    'delete:servers': {'description': "Stop and delete users' servers."},
    'tokens': {
        'description': 'Read, write, create and delete user tokens.',
        'subscopes': ['read:tokens'],
    },
    'read:tokens': {'description': 'Read user tokens.'},
    'admin:groups': {
        'description': 'Read and write group information, create and delete groups.',
        'subscopes': ['groups', 'read:roles:groups', 'delete:groups'],
    },
    'groups': {
        'description': 'Read and write group information, including adding/removing users to/from groups.',
        'subscopes': ['read:groups', 'list:groups'],
    },
    'list:groups': {
        'description': 'List groups, including at least their names.',
        'subscopes': ['read:groups:name'],
    },
    'read:groups': {
        'description': 'Read group models.',
        'subscopes': ['read:groups:name'],
    },
    'read:groups:name': {'description': 'Read group names.'},
    'delete:groups': {
        'description': "Delete groups.",
    },
    'list:services': {
        'description': 'List services, including at least their names.',
        'subscopes': ['read:services:name'],
    },
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
    'read:metrics': {
        'description': "Read prometheus metrics.",
    },
}


class Scope(Enum):
    ALL = True


def _intersection_cache_key(scopes_a, scopes_b, db=None):
    """Cache key function for scope intersections"""
    return (frozenset(scopes_a), frozenset(scopes_b))


@lru_cache_key(_intersection_cache_key)
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
    scopes_a = frozenset(scopes_a)
    scopes_b = frozenset(scopes_b)

    # cached lookups for group membership of users and servers
    @lru_cache()
    def groups_for_user(username):
        """Get set of group names for a given username"""
        # if we need a group lookup, the result is not cacheable
        nonlocal needs_db
        needs_db = True
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

    # track whether we need a db lookup (for groups)
    # because we can't cache the intersection if we do
    # if there are no group filters, this is cacheable
    needs_db = False

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
                            needs_db = True

            common_filters[base] = {
                entity: filters_a[entity] & filters_b[entity]
                for entity in common_entities
            }

            # resolve hierarchies (group/user/server) in both directions
            common_servers = initial_common_servers = common_filters[base].get(
                "server", frozenset()
            )
            common_users = initial_common_users = common_filters[base].get(
                "user", frozenset()
            )

            for a, b in [(filters_a, filters_b), (filters_b, filters_a)]:
                if 'server' in a and b.get('server') != a['server']:
                    # skip already-added servers (includes overlapping servers)
                    servers = a['server'].difference(common_servers)

                    # resolve user/server hierarchy
                    if servers and 'user' in b:
                        for server in servers:
                            username, _, servername = server.partition("/")
                            if username in b['user']:
                                common_servers = common_servers | {server}

                    # resolve group/server hierarchy if db available
                    servers = servers.difference(common_servers)
                    if db is not None and servers and 'group' in b:
                        needs_db = True
                        for server in servers:
                            server_groups = groups_for_server(server)
                            if server_groups & b['group']:
                                common_servers = common_servers | {server}

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
                            common_users = common_users | {username}

            # add server filter if it's non-empty
            # and it changed
            if common_servers and common_servers != initial_common_servers:
                common_filters[base]["server"] = common_servers

            # add user filter if it's non-empty
            # and it changed
            if common_users and common_users != initial_common_users:
                common_filters[base]["user"] = common_users

    intersection = unparse_scopes(common_filters)
    if needs_db:
        # return intersection, but don't cache it if it needed db lookups
        return DoNotCache(intersection)

    return intersection


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

    owner = None
    if isinstance(orm_object, orm.APIToken):
        owner = orm_object.user or orm_object.service
        owner_roles = roles.get_roles_for(owner)
        owner_scopes = roles.roles_to_expanded_scopes(owner_roles, owner)

        token_scopes = set(orm_object.scopes)
        if 'inherit' in token_scopes:
            # token_scopes includes 'inherit',
            # so we know the intersection is exactly the owner's scopes
            # only thing we miss by short-circuiting here: warning about excluded extra scopes
            return owner_scopes

        token_scopes = set(
            expand_scopes(
                token_scopes,
                owner=owner,
                oauth_client=orm_object.oauth_client,
            )
        )

        if orm_object.client_id != "jupyterhub":
            # oauth tokens can be used to access the service issuing the token,
            # assuming the owner itself still has permission to do so
            token_scopes.update(access_scopes(orm_object.oauth_client))

        # reduce to collapse multiple filters on the same scope
        # to avoid spurious logs about discarded scopes
        token_scopes.update(identify_scopes(owner))
        token_scopes = reduce_scopes(token_scopes)

        intersection = _intersect_expanded_scopes(
            token_scopes,
            owner_scopes,
            db=sa.inspect(orm_object).session,
        )
        discarded_token_scopes = token_scopes - intersection

        # Not taking symmetric difference here because token owner can naturally have more scopes than token
        if discarded_token_scopes:
            app_log.warning(
                f"discarding scopes [{discarded_token_scopes}],"
                f" not present in roles of owner {owner}"
            )
            app_log.debug(
                "Owner %s has scopes: %s\nToken has scopes: %s",
                owner,
                owner_scopes,
                token_scopes,
            )
        expanded_scopes = intersection
        # always include identify scopes
        expanded_scopes
    else:
        expanded_scopes = roles.roles_to_expanded_scopes(
            roles.get_roles_for(orm_object),
            owner=orm_object,
        )
        if isinstance(orm_object, (orm.User, orm.Service)):
            owner = orm_object

    return expanded_scopes


@lru_cache()
def _expand_self_scope(username):
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
      username (str): user name

    Returns:
      expanded scopes (set): set of expanded scopes covering standard user privileges
    """
    scope_list = [
        'read:users',
        'read:users:name',
        'read:users:groups',
        'users:activity',
        'read:users:activity',
        'servers',
        'delete:servers',
        'read:servers',
        'tokens',
        'read:tokens',
        'access:servers',
    ]
    # return immutable frozenset because the result is cached
    return frozenset(f"{scope}!user={username}" for scope in scope_list)


@lru_cache(maxsize=65535)
def _expand_scope(scope):
    """Returns a scope and all all subscopes

    Arguments:
      scope (str): the scope to expand

    Returns:
      expanded scope (set): set of all scope's subscopes including the scope itself
    """

    # remove filter, save for later
    scope_name, sep, filter_ = scope.partition('!')

    # expand scope and subscopes
    expanded_scope_names = set()

    def _add_subscopes(scope_name):
        expanded_scope_names.add(scope_name)
        if scope_definitions[scope_name].get('subscopes'):
            for subscope in scope_definitions[scope_name].get('subscopes'):
                _add_subscopes(subscope)

    _add_subscopes(scope_name)

    # reapply !filter
    if filter_:
        expanded_scopes = {
            f"{scope_name}!{filter_}"
            for scope_name in expanded_scope_names
            # server scopes have some cross-resource subscopes
            # where the !server filter doesn't make sense,
            # e.g. read:servers -> read:users:name
            if not (filter_.startswith("server") and scope_name.startswith("read:user"))
        }
    else:
        expanded_scopes = expanded_scope_names

    # return immutable frozenset because the result is cached
    return frozenset(expanded_scopes)


def _expand_scopes_key(scopes, owner=None, oauth_client=None):
    """Cache key function for expand_scopes

    scopes is usually a mutable list or set,
    which can be hashed as a frozenset

    For the owner, we only care about what kind they are,
    and their name.
    """
    # freeze scopes for hash
    frozen_scopes = frozenset(scopes)
    if owner is None:
        owner_key = None
    else:
        # owner key is the type and name
        owner_key = (type(owner).__name__, owner.name)
    if oauth_client is None:
        oauth_client_key = None
    else:
        oauth_client_key = oauth_client.identifier
    return (frozen_scopes, owner_key, oauth_client_key)


@lru_cache_key(_expand_scopes_key)
def expand_scopes(scopes, owner=None, oauth_client=None):
    """Returns a set of fully expanded scopes for a collection of raw scopes

    Arguments:
      scopes (collection(str)): collection of raw scopes
      owner (obj, optional): orm.User or orm.Service as owner of orm.APIToken
          Used for expansion of metascopes such as `self`
          and owner-based filters such as `!user`
      oauth_client (obj, optional): orm.OAuthClient
          The issuing OAuth client of an API token.

    Returns:
      expanded scopes (set): set of all expanded scopes, with filters applied for the owner
    """
    expanded_scopes = set(chain.from_iterable(map(_expand_scope, scopes)))

    filter_replacements = {
        "user": None,
        "service": None,
        "server": None,
    }
    user_name = None
    if isinstance(owner, orm.User):
        user_name = owner.name
        filter_replacements["user"] = f"user={user_name}"
    elif isinstance(owner, orm.Service):
        filter_replacements["service"] = f"service={owner.name}"

    if oauth_client is not None:
        if oauth_client.service is not None:
            filter_replacements["service"] = f"service={oauth_client.service.name}"
        elif oauth_client.spawner is not None:
            spawner = oauth_client.spawner
            filter_replacements["server"] = f"server={spawner.user.name}/{spawner.name}"

    for scope in expanded_scopes.copy():
        base_scope, _, filter = scope.partition('!')
        if filter in filter_replacements:
            # translate !user into !user={username}
            # and !service into !service={servicename}
            # and !server into !server={username}/{servername}
            expanded_scopes.remove(scope)
            expanded_filter = filter_replacements[filter]
            if expanded_filter:
                # translate
                expanded_scopes.add(f'{base_scope}!{expanded_filter}')
            else:
                warnings.warn(
                    f"Not expanding !{filter} filter without target {filter} in {scope}",
                    stacklevel=3,
                )

    if 'self' in expanded_scopes:
        expanded_scopes.remove('self')
        if user_name:
            expanded_scopes |= _expand_self_scope(user_name)
        else:
            warnings.warn(
                f"Not expanding 'self' scope for owner {owner} which is not a User",
                stacklevel=3,
            )

    # reduce to discard overlapping scopes
    # return immutable frozenset because the result is cached
    return frozenset(reduce_scopes(expanded_scopes))


def _resolve_requested_scopes(requested_scopes, have_scopes, user, client, db):
    """Resolve requested scopes for an OAuth token

    Intersects requested scopes with user scopes.

    First, at the raw scope level,
    then if some scopes remain, intersect expanded scopes.

    Args:
        requested_scopes (set):
            raw scopes being requested.
        have_scopes (set):
            raw scopes currently held, against which requested_scopes will be checked.
        user (orm.User):
            user for whom the scopes will be issued
        client (orm.OAuthClient):
            oauth client which will own the token
        db:
            database session, required to resolve user|group intersections

    Returns:
        (allowed_scopes, disallowed_scopes):
            sets of allowed and disallowed scopes from the request
    """

    allowed_scopes = requested_scopes.intersection(have_scopes)
    disallowed_scopes = requested_scopes.difference(have_scopes)

    if not disallowed_scopes:
        # simple intersection worked, all scopes granted
        return (allowed_scopes, disallowed_scopes)

    # if we got here, some scopes were disallowed.
    # resolve fully expanded scopes to make sure scope intersections are properly allowed.
    expanded_allowed = expand_scopes(allowed_scopes, user, client)
    expanded_have = expand_scopes(have_scopes, user, client)
    # compute one at a time so we can keep the abbreviated scopes
    # if they are a subset of user scopes (e.g. requested !server, have !user)
    for scope in list(disallowed_scopes):
        expanded_disallowed = expand_scopes({scope}, user, client)
        # don't check already-allowed scopes
        expanded_disallowed -= expanded_allowed
        if expanded_disallowed:
            allowed_intersection = _intersect_expanded_scopes(
                expanded_disallowed, expanded_have, db=db
            )
        else:
            allowed_intersection = set()

        if allowed_intersection == expanded_disallowed:
            # full scope allowed (requested scope is subset of user scopes)
            allowed_scopes.add(scope)
            disallowed_scopes.remove(scope)
            expanded_allowed = expand_scopes(allowed_scopes, user, client)

        elif allowed_intersection:
            # some scopes get through, but not all,
            # allow the subset
            allowed_scopes |= allowed_intersection
            expanded_allowed = expand_scopes(allowed_scopes, user, client)
            # choice: report that the requested scope wasn't _fully_ granted (current behavior)
            # or report the exact (likely too detailed) set of not granted scopes (below)
            # disallowed_scopes.remove(scope)
            # disallowed_scopes |= expanded_disallowed.difference(allowed_intersection)
        else:
            # no new scopes granted, original check was right
            pass
    return (allowed_scopes, disallowed_scopes)


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
    for filter_, filter_value in kwargs.items():
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


def _check_scopes_exist(scopes, who_for=None):
    """Check if provided scopes exist

    Arguments:
      scopes (list): list of scopes to check

    Raises KeyError if scope does not exist
    """

    allowed_scopes = set(scope_definitions.keys())
    filter_prefixes = ('!user=', '!service=', '!group=', '!server=')
    exact_filters = {"!user", "!service", "!server"}

    if who_for:
        log_for = f"for {who_for}"
    else:
        log_for = ""

    for scope in scopes:
        scopename, _, filter_ = scope.partition('!')
        if scopename not in allowed_scopes:
            if scopename == "all":
                raise KeyError("Draft scope 'all' is now called 'inherit'")
            raise KeyError(f"Scope '{scope}' {log_for} does not exist")
        if filter_:
            full_filter = f"!{filter_}"
            if full_filter not in exact_filters and not full_filter.startswith(
                filter_prefixes
            ):
                raise KeyError(
                    f"Scope filter {filter_} '{full_filter}' in scope '{scope}' {log_for} does not exist"
                )


def _check_token_scopes(scopes, owner, oauth_client):
    """Check that scopes to be assigned to a token
    are in fact

    Arguments:
      scopes: raw or expanded scopes
      owner: orm.User or orm.Service

    raises:
        ValueError: if requested scopes exceed owner's assigned scopes
    """
    scopes = set(scopes)
    if scopes.issubset({"inherit"}):
        # nothing to check for simple 'inherit' scopes
        return
    scopes.discard("inherit")
    # common short circuit
    token_scopes = expand_scopes(scopes, owner=owner, oauth_client=oauth_client)

    if not token_scopes:
        return

    owner_scopes = get_scopes_for(owner)
    intersection = _intersect_expanded_scopes(
        token_scopes,
        owner_scopes,
        db=sa.inspect(owner).session,
    )
    excess_scopes = token_scopes - intersection

    if excess_scopes:
        raise ValueError(
            f"Not assigning requested scopes {','.join(excess_scopes)} not held by {owner.__class__.__name__} {owner.name}"
        )


@lru_cache_key(frozenset)
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
                parsed_scopes[base_scope][key] = {value}
            else:
                parsed_scopes[base_scope][key].add(value)
    # return immutable FrozenDict because the result is cached
    return FrozenDict(parsed_scopes)


@lru_cache_key(FrozenDict)
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
    # return immutable frozenset because the result is cached
    return frozenset(expanded_scopes)


@lru_cache_key(frozenset)
def reduce_scopes(expanded_scopes):
    """Reduce expanded scopes to minimal set

    Eliminates overlapping scopes, such as access:services and access:services!service=x
    """
    # unparse_scopes already returns a frozenset
    return unparse_scopes(parse_scopes(expanded_scopes))


def needs_scope(*scopes):
    """Decorator to restrict access to users or services with the required scope"""

    for scope in scopes:
        if scope not in scope_definitions:
            raise ValueError(f"Scope {scope} is not a valid scope")

    def scope_decorator(func):
        @functools.wraps(func)
        def _auth_func(self, *args, **kwargs):
            if not self.current_user:
                # not authenticated at all, fail with more generic message
                # this is the most likely permission error - missing or mis-specified credentials,
                # don't indicate that they have insufficient permissions.
                raise web.HTTPError(
                    403,
                    "Missing or invalid credentials.",
                )

            sig = inspect.signature(func)
            bound_sig = sig.bind(self, *args, **kwargs)
            bound_sig.apply_defaults()
            # Load scopes in case they haven't been loaded yet
            if not hasattr(self, 'expanded_scopes'):
                self.expanded_scopes = {}
                self.parsed_scopes = {}

            try:
                end_point = self.request.path
            except AttributeError:
                end_point = self.__name__

            s_kwargs = {}
            for resource in {'user', 'server', 'group', 'service'}:
                resource_name = resource + '_name'
                if resource_name in bound_sig.arguments:
                    resource_value = bound_sig.arguments[resource_name]
                    s_kwargs[resource] = resource_value
            for scope in scopes:
                app_log.debug("Checking access to %s via scope %s", end_point, scope)
                has_access = _check_scope_access(self, scope, **s_kwargs)
                if has_access:
                    return func(self, *args, **kwargs)
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


def _identify_key(obj=None):
    if obj is None:
        return None
    else:
        return (type(obj).__name__, obj.name)


@lru_cache_key(_identify_key)
def identify_scopes(obj=None):
    """Return 'identify' scopes for an orm object

    Arguments:
      obj (optional): orm.User or orm.Service
          If not specified, 'raw' scopes for identifying the current user are returned,
          which may need to be expanded, later.

    Returns:
      identify scopes (set): set of scopes needed for 'identify' endpoints
    """
    if obj is None:
        return frozenset(f"read:users:{field}!user" for field in {"name", "groups"})
    elif isinstance(obj, orm.User):
        return frozenset(
            f"read:users:{field}!user={obj.name}" for field in {"name", "groups"}
        )
    elif isinstance(obj, orm.Service):
        return frozenset(
            f"read:services:{field}!service={obj.name}" for field in {"name"}
        )
    else:
        raise TypeError(f"Expected orm.User or orm.Service, got {obj!r}")


@lru_cache_key(lambda oauth_client: oauth_client.identifier)
def access_scopes(oauth_client):
    """Return scope(s) required to access an oauth client"""
    scopes = set()
    if oauth_client.identifier == "jupyterhub":
        return frozenset()
    spawner = oauth_client.spawner
    if spawner:
        scopes.add(f"access:servers!server={spawner.user.name}/{spawner.name}")
    else:
        service = oauth_client.service
        if service:
            scopes.add(f"access:services!service={service.name}")
        else:
            app_log.warning(
                f"OAuth client {oauth_client} has no associated service or spawner!"
            )
    return frozenset(scopes)


def _check_scope_key(sub_scope, orm_resource, kind):
    """Cache key function for check_scope_filter"""
    if kind == 'server':
        resource_key = (orm_resource.user.name, orm_resource.name)
    else:
        resource_key = orm_resource.name
    return (sub_scope, resource_key, kind)


@lru_cache_key(_check_scope_key)
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
        # cannot cache if we needed to lookup groups in db
        return DoNotCache(user_in_group)
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


@lru_cache_key(lambda raw_scopes, username=None: (frozenset(raw_scopes), username))
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
    # make sure we return immutable from a cached function
    return tuple(descriptions)


# regex for custom scope
# for-humans description below
# note: scope description duplicated in docs/source/rbac/scopes.md
# update docs when making changes here
_custom_scope_pattern = re.compile(r"^custom:[a-z0-9][a-z0-9_\-\*:]+[a-z0-9_\*]$")

# custom scope pattern description
# used in docstring below and error message when scopes don't match _custom_scope_pattern
_custom_scope_description = """
Custom scopes must start with `custom:`
and contain only lowercase ascii letters, numbers, hyphen, underscore, colon, and asterisk (-_:*).
The part after `custom:` must start with a letter or number.
Scopes may not end with a hyphen or colon.
"""


def define_custom_scopes(scopes):
    """Define custom scopes

    Adds custom scopes to the scope_definitions dict.

    Scopes must start with `custom:`.
    It is recommended to name custom scopes with a pattern like::

        custom:$your-project:$action:$resource

    e.g.::

        custom:jupyter_server:read:contents

    That makes them easy to parse and avoids collisions across projects.

    `scopes` must have at least one scope definition,
    and each scope definition must have a `description`,
    which will be displayed on the oauth authorization page,
    and _may_ have a `subscopes` list of other scopes if having one scope
    should imply having other, more specific scopes.

    Args:

    scopes: dict
        A dictionary of scope definitions.
        The keys are the scopes,
        while the values are dictionaries with at least a `description` field,
        and optional `subscopes` field.
        %s
    Examples::

        define_custom_scopes(
            {
                "custom:jupyter_server:read:contents": {
                    "description": "read-only access to files in a Jupyter server",
                },
                "custom:jupyter_server:read": {
                    "description": "read-only access to a Jupyter server",
                    "subscopes": [
                        "custom:jupyter_server:read:contents",
                        "custom:jupyter_server:read:kernels",
                        "...",
                },
            }
        )
    """ % indent(
        _custom_scope_description, " " * 8
    )
    for scope, scope_definition in scopes.items():
        if scope in scope_definitions and scope_definitions[scope] != scope_definition:
            raise ValueError(
                f"Cannot redefine scope {scope}={scope_definition}. Already have {scope}={scope_definitions[scope]}"
            )
        if not _custom_scope_pattern.match(scope):
            # note: keep this description in sync with docstring above
            raise ValueError(
                f"Invalid scope name: {scope!r}.\n{_custom_scope_description}"
                " and contain only lowercase ascii letters, numbers, hyphen, underscore, colon, and asterisk."
                " The part after `custom:` must start with a letter or number."
                " Scopes may not end with a hyphen or colon."
            )
        if "description" not in scope_definition:
            raise ValueError(
                f"scope {scope}={scope_definition} missing key 'description'"
            )
        if "subscopes" in scope_definition:
            subscopes = scope_definition["subscopes"]
            if not isinstance(subscopes, list) or not all(
                isinstance(s, str) for s in subscopes
            ):
                raise ValueError(
                    f"subscopes must be a list of scope strings, got {subscopes!r}"
                )
            for subscope in subscopes:
                if subscope not in scopes:
                    if subscope in scope_definitions:
                        raise ValueError(
                            f"non-custom subscope {subscope} in {scope}={scope_definition} is not allowed."
                            f" Custom scopes may only have custom subscopes."
                            f" Roles should be used to assign multiple scopes together."
                        )
                    raise ValueError(
                        f"subscope {subscope} in {scope}={scope_definition} not found. All scopes must be defined."
                    )

        extra_keys = set(scope_definition.keys()).difference(
            ["description", "subscopes"]
        )
        if extra_keys:
            warnings.warn(
                f"Ignoring unrecognized key(s) {', '.join(extra_keys)!r} in {scope}={scope_definition}",
                UserWarning,
                stacklevel=2,
            )
        app_log.info(f"Defining custom scope {scope}")
        # deferred evaluation for debug-logging
        app_log.debug("Defining custom scope %s=%s", scope, scope_definition)
        scope_definitions[scope] = scope_definition
