"""HTTP Handlers for the hub server"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from tornado.escape import url_escape
from tornado import gen
from tornado.httputil import url_concat
from tornado import web

from .base import BaseHandler


class LogoutHandler(BaseHandler):
    """Log a user out by clearing their login cookie."""
    def get(self):
        user = self.get_current_user()
        if user:
            self.log.info("User logged out: %s", user.name)
            self.clear_login_cookie()
            self.statsd.incr('logout')
        if self.authenticator.auto_login:
            html = self.render_template('logout.html')
            self.finish(html)
        else:
            self.redirect(self.settings['login_url'], permanent=False)


class LoginHandler(BaseHandler):
    """Render the login page."""

    def _render(self, login_error=None, username=None):
        return self.render_template('login.html',
                next=url_escape(self.get_argument('next', default='')),
                username=username,
                login_error=login_error,
                custom_html=self.authenticator.custom_html,
                login_url=self.settings['login_url'],
                authenticator_login_url=url_concat(
                    self.authenticator.login_url(self.hub.base_url),
                    {'next': self.get_argument('next', '')},
                ),
        )

    async def get(self):
        self.statsd.incr('login.request')
        user = self.get_current_user()
        if user:
            # set new login cookie
            # because single-user cookie may have been cleared or incorrect
            self.set_login_cookie(self.get_current_user())
            self.redirect(self.get_next_url(user), permanent=False)
        else:
            if self.authenticator.auto_login:
                auto_login_url = self.authenticator.login_url(self.hub.base_url)
                if auto_login_url == self.settings['login_url']:
                    # auto_login without a custom login handler
                    # means that auth info is already in the request
                    # (e.g. REMOTE_USER header)
                    user = await self.login_user()
                    if user is None:
                        # auto_login failed, just 403
                        raise web.HTTPError(403)
                    else:
                        self.redirect(self.get_next_url(user))
                else:
                    if self.get_argument('next', default=False):
                        auto_login_url = url_concat(auto_login_url, {'next': self.get_next_url()})
                    self.redirect(auto_login_url)
                return
            username = self.get_argument('username', default='')
            self.finish(self._render(username=username))

    async def post(self):
        # parse the arguments dict
        data = {}
        for arg in self.request.arguments:
            data[arg] = self.get_argument(arg, strip=False)

        auth_timer = self.statsd.timer('login.authenticate').start()
        user = await self.login_user(data)
        auth_timer.stop(send=False)

        if user:
            # register current user for subsequent requests to user (e.g. logging the request)
            self.get_current_user = lambda: user
            self.redirect(self.get_next_url(user))
        else:
            html = self._render(
                login_error='Invalid username or password',
                username=data['username'],
            )
            self.finish(html)


# /login renders the login page or the "Login with..." link,
# so it should always be registered.
# /logout clears cookies.
default_handlers = [
    (r"/login", LoginHandler),
    (r"/logout", LogoutHandler),
]
