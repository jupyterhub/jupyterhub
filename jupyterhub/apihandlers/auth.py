"""Authorization handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json
from urllib.parse import quote

from tornado import web, gen
from .. import orm
from ..utils import token_authenticated
from .base import APIHandler


class TokenAPIHandler(APIHandler):
    @token_authenticated
    def get(self, token):
        orm_token = orm.APIToken.find(self.db, token)
        if orm_token is None:
            raise web.HTTPError(404)
        self.write(json.dumps(self.user_model(self.users[orm_token.user])))

    @gen.coroutine
    def post(self):
        if self.authenticator is not None:
          data = self.get_json_body()
          username = yield self.authenticator.authenticate(self, data)
          if username is None:
            raise web.HTTPError(403)
          user = self.find_user(username)
          api_token = user.new_api_token()
          self.write(json.dumps({"Authentication":api_token}))
        else:
          raise web.HTTPError(404)

class CookieAPIHandler(APIHandler):
    @token_authenticated
    def get(self, cookie_name, cookie_value=None):
        cookie_name = quote(cookie_name, safe='')
        if cookie_value is None:
            self.log.warning("Cookie values in request body is deprecated, use `/cookie_name/cookie_value`")
            cookie_value = self.request.body
        else:
            cookie_value = cookie_value.encode('utf8')
        user = self._user_for_cookie(cookie_name, cookie_value)
        if user is None:
            raise web.HTTPError(404)
        self.write(json.dumps(self.user_model(user)))


default_handlers = [
    (r"/api/authorizations/cookie/([^/]+)(?:/([^/]+))?", CookieAPIHandler),
    (r"/api/authorizations/token/([^/]+)", TokenAPIHandler),
    (r"/api/authorizations/token", TokenAPIHandler),
]
