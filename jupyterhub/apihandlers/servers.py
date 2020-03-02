"""Server handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from .. import orm
from ..utils import admin_only
from .base import APIHandler


class ServerListAPIHandler(APIHandler):
    @admin_only
    def get(self):
        # TODO(mriedem): Should include_state be conditional on
        # `spawner.active` like how `user_model` works for
        # `GET /users`?
        include_state = True
        data = [
            self.server_model(
                spawner, include_state=include_state, include_user_and_id=True
            )
            for spawner in self.db.query(orm.Spawner)
        ]
        self.write(json.dumps(data))


default_handlers = [
    (r"/api/servers", ServerListAPIHandler),
]
