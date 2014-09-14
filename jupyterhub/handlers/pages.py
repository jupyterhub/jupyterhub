"""Basic html-rendering handlers."""
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from tornado import web

from .. import orm
from ..utils import admin_only, url_path_join
from .base import BaseHandler


class RootHandler(BaseHandler):
    """Render the Hub root page.
    
    Currently redirects to home if logged in,
    shows big fat login button otherwise.
    """
    def get(self):
        if self.get_current_user():
            self.redirect(
                url_path_join(self.hub.server.base_url, 'home'),
                permanent=False,
            )
            return
        
        html = self.render_template('index.html',
            login_url=self.settings['login_url'],
        )
        self.finish(html)

class HomeHandler(BaseHandler):
    """Render the user's home page."""
    @web.authenticated
    def get(self):
        html = self.render_template('home.html',
            user=self.get_current_user(),
        )
        self.finish(html)


class AdminHandler(BaseHandler):
    """Render the admin page."""
    @admin_only
    def get(self):
        html = self.render_template('admin.html',
            user=self.get_current_user(),
            users=self.db.query(orm.User),
        )
        self.finish(html)

default_handlers = [
    (r'/', RootHandler),
    (r'/home', HomeHandler),
    (r'/admin', AdminHandler),
]