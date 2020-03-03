"""Server handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from tornado import web

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


class ServerAPIHandler(APIHandler):
    @admin_only
    async def delete(self, id):
        spawner = self.find_spawner_by_id(id)
        if not spawner:
            raise web.HTTPError(404)

        # TODO(mriedem): Rather than provide a body to the DELETE /servers/{id} API
        # like DELETE /users/{name}/servers/{server_name} to toggle whether or not
        # to just stop the server or delete it, should we instead have a
        # POST /servers/{id}/stop API for stopping a server and leave
        # DELETE /servers/{id} to actually deleting (not stopping) a server/spawner?
        options = self.get_json_body() or {}
        remove = options.get('remove', True)
        server_name = spawner.name

        if remove and not server_name:
            raise web.HTTPError(400, "Cannot delete the default server")

        # TODO(mriedem): The rest of this below is copied from
        # UserServerAPIHandler.delete and we should figure out a way to make this
        # common code (a mixin, parent or utils method?).
        def _remove_spawner(f=None):
            """Removes the spawner from the database.

            :param f: When used as a callback this is a Future. If the Future failed
            with an exception then the spawner is not deleted.
            """
            if f and f.exception():
                return
            self.log.info("Deleting spawner %s", spawner._log_name)
            self.db.delete(spawner.orm_spawner)
            self.users[spawner.user_id].spawners.pop(server_name, None)
            self.db.commit()

        if spawner.pending == 'stop':
            self.log.debug("%s already stopping", spawner._log_name)
            self.set_header('Content-Type', 'text/plain')
            self.set_status(202)
            if remove:
                spawner._stop_future.add_done_callback(_remove_spawner)
            return

        if spawner.pending:
            raise web.HTTPError(
                400,  # TODO(mriedem): Seems this should be a 409.
                "%s is pending %s, please wait" % (spawner._log_name, spawner.pending),
            )

        stop_future = None
        if spawner.ready:
            # include notify, so that a server that died is noticed immediately
            status = await spawner.poll_and_notify()
            if status is None:
                stop_future = await self.stop_single_user(spawner.user, server_name)

        if remove:
            if stop_future:
                stop_future.add_done_callback(_remove_spawner)
            else:
                _remove_spawner()

        status = 202 if spawner._stop_pending else 204
        self.set_header('Content-Type', 'text/plain')
        self.set_status(status)


default_handlers = [
    (r"/api/servers", ServerListAPIHandler),
    (r"/api/servers/([^/]+)", ServerAPIHandler),
]
