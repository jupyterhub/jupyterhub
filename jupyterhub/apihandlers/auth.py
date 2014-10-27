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
        orm_token = self.db.query(orm.APIToken).filter(orm.APIToken.token == token).first()
        if orm_token is None:
            raise web.HTTPError(404)
        self.write(json.dumps({
            'user' : orm_token.user.name,
        }))

class CookieAPIHandler(APIHandler):
    @token_authenticated
    def get(self, cookie_name):
        cookie_value = self.request.body
        btoken = self.get_secure_cookie(cookie_name, cookie_value)
        if not btoken:
            raise web.HTTPError(404)
        token = btoken.decode('utf8', 'replace')
        orm_token = self.db.query(orm.CookieToken).filter(orm.CookieToken.token == token).first()
        if orm_token is None:
            raise web.HTTPError(404)
        self.write(json.dumps({
            'user' : orm_token.user.name,
        }))

default_handlers = [
    (r"/api/authorizations/cookie/([^/]+)", CookieAPIHandler),
    (r"/api/authorizations/token/([^/]+)", TokenAPIHandler),
]
