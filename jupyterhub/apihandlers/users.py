"""Authorization handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from ..handlers import BaseHandler
from .. import orm
from ..utils import admin_only


class UserListAPIHandler(BaseHandler):
    @admin_only
    def get(self):
        users = list(self.db.query(orm.User))

        data = []
        for user in users:
            data.append({
                'name': user.name,
                'server': user.server.base_url if user.server else None,
            })

        self.write(json.dumps(data))

default_handlers = [
    (r"/api/users", UserListAPIHandler),
]
