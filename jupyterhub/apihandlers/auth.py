"""Authorization handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from tornado import web
from .. import orm
from ..utils import token_authenticated
from .base import APIHandler



class TokenAPIHandler(APIHandler):
    @token_authenticated
    def get(self, token):
        orm_token = orm.APIToken.find(self.db, token)
        if orm_token is None:
            raise web.HTTPError(404)
        self.write(json.dumps({
            'user' : orm_token.user.name,
        }))

class CookieAPIHandler(APIHandler):
    @token_authenticated
    def get(self, cookie_name):
        cookie_value = self.request.body
        user = self._user_for_cookie(cookie_name, cookie_value)
        if user is None:
            raise web.HTTPError(404)
        self.write(json.dumps({
            'user' : user.name,
        }))

default_handlers = [
    (r"/api/authorizations/cookie/([^/]+)", CookieAPIHandler),
    (r"/api/authorizations/token/([^/]+)", TokenAPIHandler),
]
