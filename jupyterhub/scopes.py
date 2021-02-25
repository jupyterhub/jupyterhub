import functools
import inspect
from enum import Enum

from tornado import web
from tornado.log import app_log

from . import roles


class Scope(Enum):
    ALL = True


def get_user_scopes(name, read_only=False):
    """
    Scopes have a metascope 'all' that should be expanded to everything a user can do.
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
    if read_only:
        scope_list = read_scope_list
    else:
        scope_list.extend(read_scope_list)
    return {"{}!user={}".format(scope, name) for scope in scope_list}


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
    Returns either True for unrestricted access, False for refused access or
    an iterable with a filter
    """
    # Parse user name and server name together
    try:
        api_name = api_handler.request.path
    except AttributeError:
        api_name = type(api_handler).__name__
    if 'user' in kwargs and 'server' in kwargs:
        kwargs['server'] = "{}/{}".format(kwargs['user'], kwargs['server'])
    if req_scope not in api_handler.parsed_scopes:
        app_log.debug("No scopes present to access %s" % api_name)
        return False
    if api_handler.parsed_scopes[req_scope] == Scope.ALL:
        app_log.debug("Unrestricted access to %s call", api_name)
        return True
    # Apply filters
    sub_scope = api_handler.parsed_scopes[req_scope]
    if not kwargs:
        app_log.debug(
            "Client has restricted access to %s. In-method filtering" % api_name
        )
        return True
    for (filter_, filter_value) in kwargs.items():
        if filter_ in sub_scope and filter_value in sub_scope[filter_]:
            app_log.debug(
                "Restricted client access supported by endpoint %s" % api_name
            )
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
            s_kwargs = {}
            for resource in {'user', 'server', 'group', 'service'}:
                resource_name = resource + '_name'
                if resource_name in bound_sig.arguments:
                    resource_value = bound_sig.arguments[resource_name]
                    s_kwargs[resource] = resource_value
            has_access = False
            for scope in scopes:
                has_access |= _check_scope(self, scope, **s_kwargs)
            if has_access:
                return func(self, *args, **kwargs)
            else:
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
