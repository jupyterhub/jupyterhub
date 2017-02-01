"""Base API handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from http.client import responses

from tornado import web

from ..handlers import BaseHandler
from ..utils import url_path_join

class APIHandler(BaseHandler):

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
        
        host_path = url_path_join(host, self.hub.server.base_url)
        referer_path = referer.split('://', 1)[-1]
        if not (referer_path + '/').startswith(host_path):
            self.log.warning("Blocking Cross Origin API request.  Referer: %s, Host: %s",
                referer, host_path)
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
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({
            'status': status_code,
            'message': message or status_message,
        }))

    def user_model(self, user):
        """Get the JSON model for a User object"""
        model = {
            'kind': 'user',
            'name': user.name,
            'admin': user.admin,
            'groups': [ g.name for g in user.groups ],
            'server': user.url if user.running else None,
            'pending': None,
            'last_activity': user.last_activity.isoformat(),
        }
        if user.spawn_pending:
            model['pending'] = 'spawn'
        elif user.stop_pending:
            model['pending'] = 'stop'
        return model

    def group_model(self, group):
        """Get the JSON model for a Group object"""
        return {
            'kind': 'group',
            'name': group.name,
            'users': [ u.name for u in group.users ],
        }

    def service_model(self, service):
        """Get the JSON model for a Service object"""
        return {
            'kind': 'service',
            'name': service.name,
            'admin': service.admin,
        }

    _user_model_types = {
        'name': str,
        'admin': bool,
        'groups': list,
    }

    _group_model_types = {
        'name': str,
        'users': list,
    }

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
                raise web.HTTPError(400, "%s.%s must be %s, not: %r" % (
                    name, key, model_types[key], type(value)
                ))

    def _check_user_model(self, model):
        """Check a request-provided user model from a REST API"""
        self._check_model(model, self._user_model_types, 'user')
        for username in model.get('users', []):
            if not isinstance(username, str):
                raise web.HTTPError(400, ("usernames must be str, not %r", type(username)))

    def _check_group_model(self, model):
        """Check a request-provided group model from a REST API"""
        self._check_model(model, self._group_model_types, 'group')
        for groupname in model.get('groups', []):
            if not isinstance(groupname, str):
                raise web.HTTPError(400, ("group names must be str, not %r", type(groupname)))


    def options(self, *args, **kwargs):
        self.set_header('Access-Control-Allow-Headers', 'accept, content-type')
        self.finish()
