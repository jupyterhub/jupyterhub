"""Authorization handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from tornado import web
from ..handlers import BaseHandler
from .. import orm
from ..utils import token_authenticated


class AuthorizationsAPIHandler(BaseHandler):
    @token_authenticated
    def get(self, token):
        orm_token = self.db.query(orm.CookieToken).filter(orm.CookieToken.token == token).first()
        if orm_token is None:
            raise web.HTTPError(404)
        self.write(json.dumps({
            'user' : orm_token.user.name,
        }))
