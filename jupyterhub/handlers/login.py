"""HTTP Handlers for the hub server"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from urllib.parse import urlparse

from tornado.escape import url_escape
from tornado import gen

from .base import BaseHandler


class LogoutHandler(BaseHandler):
    """Log a user out by clearing their login cookie."""
    def get(self):
        user = self.get_current_user()
        if user:
            self.log.info("User logged out: %s", user.name)
            self.clear_login_cookie()
            for name in user.other_user_cookies:
                self.clear_login_cookie(name)
            user.other_user_cookies = set([])
            self.statsd.incr('logout')
        self.redirect(self.hub.server.base_url, permanent=False)


class LoginHandler(BaseHandler):
    """Render the login page."""

    def _render(self, login_error=None, username=None):
        return self.render_template('login.html',
                next=url_escape(self.get_argument('next', default='')),
                username=username,
                login_error=login_error,
                custom_html=self.authenticator.custom_html,
                login_url=self.settings['login_url'],
        )

    def get(self):
        self.statsd.incr('login.request')
        next_url = self.get_argument('next', '')
        if (next_url + '/').startswith('%s://%s/' % (self.request.protocol, self.request.host)):
            # treat absolute URLs for our host as absolute paths:
            next_url = urlparse(next_url).path
        elif not next_url.startswith('/'):
            # disallow non-absolute next URLs (e.g. full URLs to other hosts)
            next_url = ''
        user = self.get_current_user()
        if user:
            if not next_url:
                if user.running:
                    next_url = user.url
                else:
                    next_url = self.hub.server.base_url
            # set new login cookie
            # because single-user cookie may have been cleared or incorrect
            self.set_login_cookie(self.get_current_user())
            self.redirect(next_url, permanent=False)
        else:
            username = self.get_argument('username', default='')
            self.finish(self._render(username=username))

    @gen.coroutine
    def post(self):
        # parse the arguments dict
        data = {}
        for arg in self.request.arguments:
            data[arg] = self.get_argument(arg)

        auth_timer = self.statsd.timer('login.authenticate').start()
        username = yield self.authenticate(data)
        auth_timer.stop(send=False)

        if username:
            self.statsd.incr('login.success')
            self.statsd.timing('login.authenticate.success', auth_timer.ms)
            user = self.user_from_username(username)
            already_running = False
            if user.spawner:
                status = yield user.spawner.poll()
                already_running = (status == None)
            if not already_running and not user.spawner.options_form:
                yield self.spawn_single_user(user)
            self.set_login_cookie(user)
            next_url = self.get_argument('next', default='')
            if not next_url.startswith('/'):
                next_url = ''
            next_url = next_url or self.hub.server.base_url
            self.redirect(next_url)
            self.log.info("User logged in: %s", username)
        else:
            self.statsd.incr('login.failure')
            self.statsd.timing('login.authenticate.failure', auth_timer.ms)
            self.log.debug("Failed login for %s", data.get('username', 'unknown user'))
            html = self._render(
                login_error='Invalid username or password',
                username=username,
            )
            self.finish(html)


# /login renders the login page or the "Login with..." link,
# so it should always be registered.
# /logout clears cookies.
default_handlers = [
    (r"/login", LoginHandler),
    (r"/logout", LogoutHandler),
]
