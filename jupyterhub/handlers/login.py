"""HTTP Handlers for the hub server"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from tornado.escape import url_escape
from tornado import gen

from .base import BaseHandler


class LogoutHandler(BaseHandler):
    """Log a user out by clearing their login cookie."""
    def get(self):
        self.clear_login_cookie()
        html = self.render_template('logout.html')
        self.finish(html)


class LoginHandler(BaseHandler):
    """Render the login page."""

    def _render(self, message=None, username=None):
        return self.render_template('login.html',
                next=url_escape(self.get_argument('next', default='')),
                username=username,
                message=message,
        )

    def get(self):
        if self.get_argument('next', False) and self.get_current_user():
            self.redirect(self.get_argument('next'), permanent=False)
        else:
            username = self.get_argument('username', default='')
            self.finish(self._render(username=username))

    @gen.coroutine
    def post(self):
        # parse the arguments dict
        data = {}
        for arg in self.request.arguments:
            data[arg] = self.get_argument(arg)

        username = data['username']
        authorized = yield self.authenticate(data)
        if authorized:
            user = self.user_from_username(username)
            yield self.spawn_single_user(user)
            self.set_login_cookies(user)
            next_url = self.get_argument('next', default='') or self.hub.server.base_url
            self.redirect(next_url)
        else:
            self.log.debug("Failed login for %s", username)
            html = self._render(
                message={'error': 'Invalid username or password'},
                username=username,
            )
            self.finish(html)

default_handlers = [
    (r"/login", LoginHandler),
    (r"/logout", LogoutHandler),
]
