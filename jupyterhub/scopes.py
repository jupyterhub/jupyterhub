import functools
import inspect
from enum import Enum

from tornado import web
from tornado.log import app_log

from . import orm
from . import roles


class Scope(Enum):
    ALL = True


def _intersect_scopes(token_scopes, owner_scopes):
    """Compares the permissions of token and its owner including horizontal filters
    Returns the intersection of the two sets of scopes

    Note: Intersects correctly with ALL and exact filter matches
          (i.e. users!user=x & read:users:name -> read:users:name!user=x)

          Does not currently intersect with containing filters
          (i.e. users!group=x & users!user=y even if user y is in group x,
          same for users:servers!user=x & users:servers!server=y)
    """
    owner_parsed_scopes = parse_scopes(owner_scopes)
    token_parsed_scopes = parse_scopes(token_scopes)

    common_bases = owner_parsed_scopes.keys() & token_parsed_scopes.keys()

    common_filters = {}
    warn = False
    for base in common_bases:
        if owner_parsed_scopes[base] == Scope.ALL:
            common_filters[base] = token_parsed_scopes[base]
        elif token_parsed_scopes[base] == Scope.ALL:
            common_filters[base] = owner_parsed_scopes[base]
        else:
            common_entities = (
                owner_parsed_scopes[base].keys() & token_parsed_scopes[base].keys()
            )
            all_entities = (
                owner_parsed_scopes[base].keys() | token_parsed_scopes[base].keys()
            )
            if 'user' in all_entities and ('group' or 'server' in all_entities):
                warn = True

            common_filters[base] = {
                entity: set(owner_parsed_scopes[base][entity])
                & set(token_parsed_scopes[base][entity])
                for entity in common_entities
            }

    if warn:
        app_log.warning(
            "[!user=, !group=] or [!user=, !server=] combinations of filters present, intersection between not considered. May result in lower than intended permissions."
        )

    scopes = set()
    for base in common_filters:
        if common_filters[base] == Scope.ALL:
            scopes.add(base)
        else:
            for entity, names_list in common_filters[base].items():
                for name in names_list:
                    scopes.add(f'{base}!{entity}={name}')

    return scopes


def get_scopes_for(orm_object):
    """Find scopes for a given user or token and resolve permissions"""
    scopes = set()
    if orm_object is None:
        return scopes

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
        owner_scopes = roles.expand_roles_to_scopes(owner)
        if 'all' in token_scopes:
            token_scopes.remove('all')
            token_scopes |= owner_scopes

        scopes = _intersect_scopes(token_scopes, owner_scopes)
        discarded_token_scopes = token_scopes - scopes

        # Not taking symmetric difference here because token owner can naturally have more scopes than token
        if discarded_token_scopes:
            app_log.warning(
                "discarding scopes [%s], not present in owner roles"
                % ", ".join(discarded_token_scopes)
            )
    else:
        scopes = roles.expand_roles_to_scopes(orm_object)
    return scopes


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


def _check_scope(api_handler, req_scope, **kwargs):
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

    For instance, scope list ["users", "groups!group=foo", "users:servers!server=bar", "users:servers!server=baz"]
    would lead to scope model
    {
       "users":scope.ALL,
       "admin:users":{
          "user":[
             "alice"
          ]
       },
       "users:servers":{
          "server":[
             "bar",
             "baz"
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
            key, _, val = filter_.partition('=')
            if key not in parsed_scopes[base_scope]:
                parsed_scopes[base_scope][key] = []
            parsed_scopes[base_scope][key].append(val)
    return parsed_scopes


def needs_scope(*scopes):
    """Decorator to restrict access to users or services with the required scope"""

    def scope_decorator(func):
        @functools.wraps(func)
        def _auth_func(self, *args, **kwargs):
            sig = inspect.signature(func)
            bound_sig = sig.bind(self, *args, **kwargs)
            bound_sig.apply_defaults()
            # Load scopes in case they haven't been loaded yet
            if not hasattr(self, 'raw_scopes'):
                self.raw_scopes = {}
                self.parsed_scopes = {}

            s_kwargs = {}
            for resource in {'user', 'server', 'group', 'service'}:
                resource_name = resource + '_name'
                if resource_name in bound_sig.arguments:
                    resource_value = bound_sig.arguments[resource_name]
                    s_kwargs[resource] = resource_value
            for scope in scopes:
                app_log.debug("Checking access via scope %s", scope)
                has_access = _check_scope(self, scope, **s_kwargs)
                if has_access:
                    return func(self, *args, **kwargs)
            try:
                end_point = self.request.path
            except AttributeError:
                end_point = self.__name__
            app_log.warning(
                "Not authorizing access to {}. Requires any of [{}], not derived from scopes [{}]".format(
                    end_point, ", ".join(scopes), ", ".join(self.raw_scopes)
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
      scopes (set): set of scopes needed for 'identify' endpoints
    """
    if isinstance(obj, orm.User):
        return {
            f"read:users:{field}!user={obj.name}"
            for field in {"name", "admin", "groups"}
        }
    elif isinstance(obj, orm.Service):
        return {
            f"read:services:{field}!service={obj.name}" for field in {"name", "admin"}
        }
    else:
        raise TypeError(f"Expected orm.User or orm.Service, got {obj!r}")
