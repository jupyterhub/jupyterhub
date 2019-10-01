"""Base API handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from datetime import datetime
from http.client import responses

from sqlalchemy.exc import SQLAlchemyError
from tornado import web

from .. import orm
from ..handlers import BaseHandler
from ..utils import isoformat
from ..utils import url_path_join


class APIHandler(BaseHandler):
    """Base class for API endpoints

    Differences from page handlers:

    - JSON responses and errors
    - strict referer checking for Cookie-authenticated requests
    - strict content-security-policy
    - methods for REST API models
    """

    @property
    def content_security_policy(self):
        return '; '.join([super().content_security_policy, "default-src 'none'"])

    def get_content_type(self):
        return 'application/json'

    def check_referer(self):
        """Check Origin for cross-site API requests.

        Copied from WebSocket with changes:

        - allow unspecified host/referer (e.g. scripts)
        """
        host = self.request.headers.get("Host")
        referer = self.request.headers.get("Referer")

        # If no header is provided, assume it comes from a script/curl.
        # We are only concerned with cross-site browser stuff here.
        if not host:
            self.log.warning("Blocking API request with no host")
            return False
        if not referer:
            self.log.warning("Blocking API request with no referer")
            return False

        host_path = url_path_join(host, self.hub.base_url)
        referer_path = referer.split('://', 1)[-1]
        if not (referer_path + '/').startswith(host_path):
            self.log.warning(
                "Blocking Cross Origin API request.  Referer: %s, Host: %s",
                referer,
                host_path,
            )
            return False
        return True

    def get_current_user_cookie(self):
        """Override get_user_cookie to check Referer header"""
        cookie_user = super().get_current_user_cookie()
        # check referer only if there is a cookie user,
        # avoiding misleading "Blocking Cross Origin" messages
        # when there's no cookie set anyway.
        if cookie_user and not self.check_referer():
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

    def server_model(self, spawner, include_state=False):
        """Get the JSON model for a Spawner"""
        return {
            'name': spawner.name,
            'last_activity': isoformat(spawner.orm_spawner.last_activity),
            'started': isoformat(spawner.orm_spawner.started),
            'pending': spawner.pending,
            'ready': spawner.ready,
            'state': spawner.get_state() if include_state else None,
            'url': url_path_join(spawner.user.url, spawner.name, '/'),
            'user_options': spawner.user_options,
            'progress_url': spawner._progress_url,
        }

    def token_model(self, token):
        """Get the JSON model for an APIToken"""
        expires_at = None
        if isinstance(token, orm.APIToken):
            kind = 'api_token'
            extra = {'note': token.note}
            expires_at = token.expires_at
        elif isinstance(token, orm.OAuthAccessToken):
            kind = 'oauth'
            extra = {'oauth_client': token.client.description or token.client.client_id}
            if token.expires_at:
                expires_at = datetime.fromtimestamp(token.expires_at)
        else:
            raise TypeError(
                "token must be an APIToken or OAuthAccessToken, not %s" % type(token)
            )

        if token.user:
            owner_key = 'user'
            owner = token.user.name

        else:
            owner_key = 'service'
            owner = token.service.name

        model = {
            owner_key: owner,
            'id': token.api_id,
            'kind': kind,
            'created': isoformat(token.created),
            'last_activity': isoformat(token.last_activity),
            'expires_at': isoformat(expires_at),
        }
        model.update(extra)
        return model

    def user_model(self, user, include_servers=False, include_state=False):
        """Get the JSON model for a User object"""
        if isinstance(user, orm.User):
            user = self.users[user.id]

        model = {
            'kind': 'user',
            'name': user.name,
            'admin': user.admin,
            'groups': [g.name for g in user.groups],
            'server': user.url if user.running else None,
            'pending': None,
            'created': isoformat(user.created),
            'last_activity': isoformat(user.last_activity),
        }
        if '' in user.spawners:
            model['pending'] = user.spawners[''].pending

        if not include_servers:
            model['servers'] = None
            return model

        servers = model['servers'] = {}
        for name, spawner in user.spawners.items():
            # include 'active' servers, not just ready
            # (this includes pending events)
            if spawner.active:
                servers[name] = self.server_model(spawner, include_state=include_state)
        return model

    def group_model(self, group):
        """Get the JSON model for a Group object"""
        return {
            'kind': 'group',
            'name': group.name,
            'users': [u.name for u in group.users],
        }

    def service_model(self, service):
        """Get the JSON model for a Service object"""
        return {'kind': 'service', 'name': service.name, 'admin': service.admin}

    _user_model_types = {'name': str, 'admin': bool, 'groups': list, 'auth_state': dict}

    _group_model_types = {'name': str, 'users': list}

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

    def options(self, *args, **kwargs):
        self.finish()


class API404(APIHandler):
    """404 for API requests

    Ensures JSON 404 errors for malformed URLs
    """

    async def prepare(self):
        await super().prepare()
        raise web.HTTPError(404)
