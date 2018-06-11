"""Basic html-rendering handlers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from collections import defaultdict
from datetime import datetime
from http.client import responses

from jinja2 import TemplateNotFound
from tornado import web, gen
from tornado.httputil import url_concat

from .. import orm
from ..utils import admin_only, url_path_join
from .base import BaseHandler

class NamedServerSpawnHandler(BaseHandler):
    """Instead of handling spawning of single-user servers via form,

    creates a new named server via a specifically different action.

    POST handles form submission.

    Only enabled when allow named servers is true.
    """
    async def _render_form(self, message='', for_user=None):
        # Note that 'user' is the authenticated user making the request and
        # 'for_user' is the user whose server is being spawned.
        user = for_user or self.get_current_user()
        spawner_options_form = await user.spawner.get_options_form()
        return self.render_template('spawn.html',
            for_user=for_user,
            spawner_options_form=spawner_options_form,
            error_message=message,
            url=self.request.uri,
            spawner=for_user.spawner
        )

    
    @web.authenticated
    async def post(self, for_user=None):
        """POST spawns with user-specified options"""
        user = current_user = self.get_current_user()
        if for_user is not None and for_user != user.name:
            if not user.admin:
                raise web.HTTPError(403, "Only admins can spawn on behalf of other users")
            user = self.find_user(for_user)
            if user is None:
                raise web.HTTPError(404, "No such user: %s" % for_user)
        if not self.allow_named_servers and user.running:
            url = user.url
            self.log.warning("User is already running: %s", url)
            self.redirect(url)
            return
        if user.spawner.pending:
            raise web.HTTPError(
                400, "%s is pending %s" % (user.spawner._log_name, user.spawner.pending)
            )
        form_options = {}
        for key, byte_list in self.request.body_arguments.items():
            form_options[key] = [ bs.decode('utf8') for bs in byte_list ]
        for key, byte_list in self.request.files.items():
            form_options["%s_file"%key] = byte_list
        try:
            options = user.spawner.options_from_form(form_options)
            await self.spawn_single_user(user, options=options)
        except Exception as e:
            self.log.error("Failed to spawn single-user server with form", exc_info=True)
            form = await self._render_form(message=str(e), for_user=user)
            self.finish(form)
            return
        if current_user is user:
            self.set_login_cookie(user)
        url = user.url

        next_url = self.get_argument('next', '')
        if next_url and not next_url.startswith('/'):
            self.log.warning("Disallowing redirect outside JupyterHub: %r", next_url)
        elif next_url:
            url = next_url

        self.redirect(url)
