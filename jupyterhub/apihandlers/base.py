"""Base API handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import warnings
from functools import lru_cache
from http.client import responses
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.exc import SQLAlchemyError
from tornado import web

from .. import orm
from ..handlers import BaseHandler
from ..scopes import get_scopes_for
from ..utils import isoformat, url_escape_path, url_path_join

PAGINATION_MEDIA_TYPE = "application/jupyterhub-pagination+json"


class APIHandler(BaseHandler):
    """Base class for API endpoints

    Differences from page handlers:

    - JSON responses and errors
    - strict content-security-policy
    - methods for REST API models
    """

    # accept token-based authentication for API requests
    _accept_token_auth = True

    @property
    def content_security_policy(self):
        return '; '.join([super().content_security_policy, "default-src 'none'"])

    def get_content_type(self):
        return 'application/json'

    @property
    @lru_cache()
    def accepts_pagination(self):
        """Return whether the client accepts the pagination preview media type"""
        accept_header = self.request.headers.get("Accept", "")
        if not accept_header:
            return False
        accepts = {s.strip().lower() for s in accept_header.strip().split(",")}
        return PAGINATION_MEDIA_TYPE in accepts

    def check_referer(self):
        """DEPRECATED"""
        warnings.warn(
            "check_referer is deprecated in JupyterHub 3.2 and always returns True",
            DeprecationWarning,
            stacklevel=2,
        )
        return True

    def check_post_content_type(self):
        """Check request content-type, e.g. for cross-site POST requests

        Cross-site POST via form will include content-type
        """
        content_type = self.request.headers.get("Content-Type")
        if not content_type:
            # not specified, e.g. from a script
            return True

        # parse content type for application/json
        fields = content_type.lower().split(";")
        if not any(f.lstrip().startswith("application/json") for f in fields):
            self.log.warning(f"Not allowing POST with content-type: {content_type}")
            return False

        return True

    # we also check xsrf on GETs to API endpoints
    _xsrf_safe_methods = {"HEAD", "OPTIONS"}

    def check_xsrf_cookie(self):
        if not hasattr(self, '_jupyterhub_user'):
            # called too early to check if we're token-authenticated
            return
        if self._jupyterhub_user is None and 'Origin' not in self.request.headers:
            # don't raise xsrf if auth failed
            # don't apply this shortcut to actual cross-site requests, which have an 'Origin' header,
            # which would reveal if there are credentials present
            return
        if getattr(self, '_token_authenticated', False):
            # if token-authenticated, ignore XSRF
            return
        return super().check_xsrf_cookie()

    def get_current_user_cookie(self):
        """Extend get_user_cookie to add checks for CORS"""
        cookie_user = super().get_current_user_cookie()
        # CORS checks for cookie-authentication
        # check these only if there is a cookie user,
        # avoiding misleading "Blocking Cross Origin" messages
        # when there's no cookie set anyway.
        if cookie_user:
            if (
                self.request.method.upper() == 'POST'
                and not self.check_post_content_type()
            ):
                return None
        return cookie_user

    def get_json_body(self):
        """Return the body of the request as JSON data."""
        if not self.request.body:
            return None
        body = self.request.body.strip().decode('utf-8')
        try:
            model = json.loads(body)
        except Exception:
            self.log.debug("Bad JSON: %r", body)
            self.log.error("Couldn't parse JSON", exc_info=True)
            raise web.HTTPError(400, 'Invalid JSON in body of request')
        return model

    def write_error(self, status_code, **kwargs):
        """Write JSON errors instead of HTML"""
        exc_info = kwargs.get('exc_info')
        message = ''
        exception = None
        status_message = responses.get(status_code, 'Unknown Error')
        if exc_info:
            exception = exc_info[1]
            # get the custom message, if defined
            try:
                message = exception.log_message % exception.args
            except Exception:
                pass

            # construct the custom reason, if defined
            reason = getattr(exception, 'reason', '')
            if reason:
                status_message = reason

        if exception and isinstance(exception, SQLAlchemyError):
            try:
                exception_str = str(exception)
                self.log.warning(
                    "Rolling back session due to database error %s", exception_str
                )
            except Exception:
                self.log.warning(
                    "Rolling back session due to database error %s", type(exception)
                )
            self.db.rollback()

        self.set_header('Content-Type', 'application/json')
        if isinstance(exception, web.HTTPError):
            # allow setting headers from exceptions
            # since exception handler clears headers
            headers = getattr(exception, 'headers', None)
            if headers:
                for key, value in headers.items():
                    self.set_header(key, value)
            # Content-Length must be recalculated.
            self.clear_header('Content-Length')

        self.write(
            json.dumps({'status': status_code, 'message': message or status_message})
        )

    def server_model(self, spawner, *, user=None):
        """Get the JSON model for a Spawner
        Assume server permission already granted
        """
        if isinstance(spawner, orm.Spawner):
            # if an orm.Spawner is passed,
            # create a model for a stopped Spawner
            # not all info is available without the higher-level Spawner wrapper
            orm_spawner = spawner
            pending = None
            ready = False
            stopped = True
            user = user
            if user is None:
                raise RuntimeError("Must specify User with orm.Spawner")
            state = orm_spawner.state
        else:
            orm_spawner = spawner.orm_spawner
            pending = spawner.pending
            ready = spawner.ready
            user = spawner.user
            stopped = not spawner.active
            state = spawner.get_state()

        model = {
            'name': orm_spawner.name,
            'last_activity': isoformat(orm_spawner.last_activity),
            'started': isoformat(orm_spawner.started),
            'pending': pending,
            'ready': ready,
            'stopped': stopped,
            'url': url_path_join(user.url, url_escape_path(spawner.name), '/'),
            'user_options': spawner.user_options,
            'progress_url': user.progress_url(spawner.name),
        }
        scope_filter = self.get_scope_filter('admin:server_state')
        if scope_filter(spawner, kind='server'):
            model['state'] = state
        return model

    def token_model(self, token):
        """Get the JSON model for an APIToken"""

        if token.user:
            owner_key = 'user'
            owner = token.user.name

        else:
            owner_key = 'service'
            owner = token.service.name

        model = {
            owner_key: owner,
            'id': token.api_id,
            'kind': 'api_token',
            # deprecated field, but leave it present.
            'roles': [],
            'scopes': list(get_scopes_for(token)),
            'created': isoformat(token.created),
            'last_activity': isoformat(token.last_activity),
            'expires_at': isoformat(token.expires_at),
            'note': token.note,
            'session_id': token.session_id,
            'oauth_client': token.oauth_client.description
            or token.oauth_client.identifier,
        }
        return model

    def _filter_model(self, model, access_map, entity, kind, keys=None):
        """
        Filter the model based on the available scopes and the entity requested for.
        If keys is a dictionary, update it with the allowed keys for the model.
        """
        allowed_keys = set()
        for scope in access_map:
            scope_filter = self.get_scope_filter(scope)
            if scope_filter(entity, kind=kind):
                allowed_keys |= access_map[scope]
        model = {key: model[key] for key in allowed_keys if key in model}
        if isinstance(keys, set):
            keys.update(allowed_keys)
        return model

    _include_stopped_servers = None

    @property
    def include_stopped_servers(self):
        """Whether stopped servers should be included in user models"""
        if self._include_stopped_servers is None:
            self._include_stopped_servers = self.get_argument(
                "include_stopped_servers", "0"
            ).lower() not in {"0", "false"}
        return self._include_stopped_servers

    def user_model(self, user):
        """Get the JSON model for a User object"""
        if isinstance(user, orm.User):
            user = self.users[user.id]
        include_stopped_servers = self.include_stopped_servers
        model = {
            'kind': 'user',
            'name': user.name,
            'admin': user.admin,
            'roles': [r.name for r in user.roles],
            'groups': [g.name for g in user.groups],
            'server': user.url if user.running else None,
            'pending': None,
            'created': isoformat(user.created),
            'last_activity': isoformat(user.last_activity),
            'auth_state': None,  # placeholder, filled in later
        }
        access_map = {
            'read:users': {
                'kind',
                'name',
                'admin',
                'roles',
                'groups',
                'server',
                'pending',
                'created',
                'last_activity',
            },
            'read:users:name': {'kind', 'name', 'admin'},
            'read:users:groups': {'kind', 'name', 'groups'},
            'read:users:activity': {'kind', 'name', 'last_activity'},
            'read:servers': {'kind', 'name', 'servers'},
            'read:roles:users': {'kind', 'name', 'roles', 'admin'},
            'admin:auth_state': {'kind', 'name', 'auth_state'},
        }
        allowed_keys = set()
        model = self._filter_model(
            model, access_map, user, kind='user', keys=allowed_keys
        )
        if model:
            if '' in user.spawners and 'pending' in allowed_keys:
                model['pending'] = user.spawners[''].pending

            servers = {}
            scope_filter = self.get_scope_filter('read:servers')
            for name, spawner in user.spawners.items():
                # include 'active' servers, not just ready
                # (this includes pending events)
                if (spawner.active or include_stopped_servers) and scope_filter(
                    spawner, kind='server'
                ):
                    servers[name] = self.server_model(spawner)

            if include_stopped_servers:
                # add any stopped servers in the db
                seen = set(servers.keys())
                for name, orm_spawner in user.orm_spawners.items():
                    if name not in seen and scope_filter(orm_spawner, kind='server'):
                        servers[name] = self.server_model(orm_spawner, user=user)

            if "servers" in allowed_keys or servers:
                # omit servers if no access
                # leave present and empty
                # if request has access to read servers in general
                model["servers"] = servers

        return model

    def group_model(self, group):
        """Get the JSON model for a Group object"""
        model = {
            'kind': 'group',
            'name': group.name,
            'roles': [r.name for r in group.roles],
            'users': [u.name for u in group.users],
            'properties': group.properties,
        }
        access_map = {
            'read:groups': {'kind', 'name', 'properties', 'users'},
            'read:groups:name': {'kind', 'name'},
            'read:roles:groups': {'kind', 'name', 'roles'},
        }
        model = self._filter_model(model, access_map, group, 'group')
        return model

    def service_model(self, service):
        """Get the JSON model for a Service object"""
        model = {
            'kind': 'service',
            'name': service.name,
            'roles': [r.name for r in service.roles],
            'admin': service.admin,
            'url': getattr(service, 'url', ''),
            'prefix': service.server.base_url if getattr(service, 'server', '') else '',
            'command': getattr(service, 'command', ''),
            'pid': service.proc.pid if getattr(service, 'proc', '') else 0,
            'info': getattr(service, 'info', ''),
            'display': getattr(service, 'display', ''),
        }
        access_map = {
            'read:services': {
                'kind',
                'name',
                'admin',
                'url',
                'prefix',
                'command',
                'pid',
                'info',
                'display',
            },
            'read:services:name': {'kind', 'name', 'admin'},
            'read:roles:services': {'kind', 'name', 'roles', 'admin'},
        }
        model = self._filter_model(model, access_map, service, 'service')
        return model

    _user_model_types = {
        'name': str,
        'admin': bool,
        'groups': list,
        'roles': list,
        'auth_state': dict,
    }

    _group_model_types = {'name': str, 'users': list, 'roles': list}

    def _check_model(self, model, model_types, name):
        """Check a model provided by a REST API request

        Args:
            model (dict): user-provided model
            model_types (dict): dict of key:type used to validate types and keys
            name (str): name of the model, used in error messages
        """
        if not isinstance(model, dict):
            raise web.HTTPError(400, "Invalid JSON data: %r" % model)
        if not set(model).issubset(set(model_types)):
            raise web.HTTPError(400, "Invalid JSON keys: %r" % model)
        for key, value in model.items():
            if not isinstance(value, model_types[key]):
                raise web.HTTPError(
                    400,
                    "%s.%s must be %s, not: %r"
                    % (name, key, model_types[key], type(value)),
                )

    def _check_user_model(self, model):
        """Check a request-provided user model from a REST API"""
        self._check_model(model, self._user_model_types, 'user')
        for username in model.get('users', []):
            if not isinstance(username, str):
                raise web.HTTPError(
                    400, ("usernames must be str, not %r", type(username))
                )

    def _check_group_model(self, model):
        """Check a request-provided group model from a REST API"""
        self._check_model(model, self._group_model_types, 'group')
        for groupname in model.get('groups', []):
            if not isinstance(groupname, str):
                raise web.HTTPError(
                    400, ("group names must be str, not %r", type(groupname))
                )

    def get_api_pagination(self):
        default_limit = self.settings["api_page_default_limit"]
        max_limit = self.settings["api_page_max_limit"]
        if not self.accepts_pagination:
            # if new pagination Accept header is not used,
            # default to the higher max page limit to reduce likelihood
            # of missing users due to pagination in code that hasn't been updated
            default_limit = max_limit
        offset = self.get_argument("offset", None)
        limit = self.get_argument("limit", default_limit)
        try:
            offset = abs(int(offset)) if offset is not None else 0
            limit = abs(int(limit))
            if limit > max_limit:
                limit = max_limit
            if limit < 1:
                limit = 1
        except Exception as e:
            raise web.HTTPError(
                400, "Invalid argument type, offset and limit must be integers"
            )
        return offset, limit

    def paginated_model(self, items, offset, limit, total_count):
        """Return the paginated form of a collection (list or dict)

        A dict with { items: [], _pagination: {}}
        instead of a single list (or dict).

        pagination info includes the current offset and limit,
        the total number of results for the query,
        and information about how to build the next page request
        if there is one.
        """
        next_offset = offset + limit
        data = {
            "items": items,
            "_pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
                "next": None,
            },
        }
        if next_offset < total_count:
            # if there's a next page
            next_url_parsed = urlparse(self.request.full_url())
            query = parse_qs(next_url_parsed.query, keep_blank_values=True)
            query['offset'] = [next_offset]
            query['limit'] = [limit]
            next_url_parsed = next_url_parsed._replace(
                query=urlencode(query, doseq=True)
            )
            next_url = urlunparse(next_url_parsed)
            data["_pagination"]["next"] = {
                "offset": next_offset,
                "limit": limit,
                "url": next_url,
            }
        return data

    def options(self, *args, **kwargs):
        self.finish()


class API404(APIHandler):
    """404 for API requests

    Ensures JSON 404 errors for malformed URLs
    """

    def check_xsrf_cookie(self):
        pass

    async def prepare(self):
        await super().prepare()
        raise web.HTTPError(404)
