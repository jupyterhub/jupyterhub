"""HTTP Handlers for the hub server"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio

from jinja2 import Template
from tornado import web
from tornado.escape import url_escape
from tornado.httputil import url_concat

from .._xsrf_utils import _set_xsrf_cookie
from ..utils import maybe_future
from .base import BaseHandler


class LogoutHandler(BaseHandler):
    """Log a user out by clearing their login cookie."""

    @property
    def shutdown_on_logout(self):
        return self.settings.get('shutdown_on_logout', False)

    async def _shutdown_servers(self, user):
        """Shutdown servers for logout

        Get all active servers for the provided user, stop them.
        """
        active_servers = [
            name
            for (name, spawner) in user.spawners.items()
            if spawner.active and not spawner.pending
        ]
        if active_servers:
            self.log.info("Shutting down %s's servers", user.name)
            futures = []
            for server_name in active_servers:
                futures.append(maybe_future(self.stop_single_user(user, server_name)))
            await asyncio.gather(*futures)

    def _backend_logout_cleanup(self, name):
        """Default backend logout actions

        Send a log message, clear some cookies, increment the logout counter.
        """
        self.log.info("User logged out: %s", name)
        self.clear_login_cookie()
        self.statsd.incr('logout')

    async def default_handle_logout(self):
        """The default logout action

        Optionally cleans up servers, clears cookies, increments logout counter
        Cleaning up servers can be prevented by setting shutdown_on_logout to
        False.
        """
        user = self.current_user
        if user:
            if self.shutdown_on_logout:
                await self._shutdown_servers(user)

            self._backend_logout_cleanup(user.name)

    async def handle_logout(self):
        """Custom user action during logout

        By default a no-op, this function should be overridden in subclasses
        to have JupyterHub take a custom action on logout.
        """
        return

    async def render_logout_page(self):
        """Render the logout page, if any

        Override this function to set a custom logout page.
        """
        if self.authenticator.auto_login:
            html = await self.render_template('logout.html')
            self.finish(html)
        else:
            self.redirect(self.settings['login_url'], permanent=False)

    async def get(self):
        """Log the user out, call the custom action, forward the user
        to the logout page
        """
        await self.default_handle_logout()
        await self.handle_logout()
        # clear jupyterhub user before rendering logout page
        # ensures the login button is shown instead of logout
        self._jupyterhub_user = None
        await self.render_logout_page()


class LoginHandler(BaseHandler):
    """Render the login page."""

    def render_template(self, name, **ns):
        # intercept error page rendering for form submissions
        if (
            name == "error.html"
            and self.request.method.lower() == "post"
            and self.request.headers.get("Sec-Fetch-Mode", "navigate") == "navigate"
        ):
            # regular login form submission
            # render login form with error message
            ns["login_error"] = ns.get("message") or ns.get("status_message", "")
            ns["username"] = self.get_argument("username", strip=True, default="")
            return self._render(**ns)
        else:
            return super().render_template(name, **ns)

    def check_xsrf_cookie(self):
        try:
            return super().check_xsrf_cookie()
        except web.HTTPError as e:
            # rewrite xsrf error on login form for nicer message
            # suggest retry, which is likely to succeed
            # log the original error so admins can debug
            self.log.error("XSRF error on login form: %s", e)
            if self.request.headers.get("Sec-Fetch-Mode", "navigate") == "navigate":
                raise web.HTTPError(
                    e.status_code, "Login form invalid or expired. Try again."
                )
            else:
                raise

    def _render(self, login_error=None, username=None, **kwargs):
        context = {
            "next": url_escape(self.get_argument('next', default='')),
            "username": username,
            "login_error": login_error,
            "login_url": self.settings['login_url'],
            "authenticator_login_url": url_concat(
                self.authenticator.login_url(self.hub.base_url),
                {
                    'next': self.get_argument('next', ''),
                },
            ),
            "authenticator": self.authenticator,
            "xsrf": self.xsrf_token.decode('ascii'),
        }
        custom_html = Template(
            self.authenticator.get_custom_html(self.hub.base_url)
        ).render(**context)
        return self.render_template(
            'login.html',
            **context,
            custom_html=custom_html,
            **kwargs,
        )

    async def get(self):
        self.statsd.incr('login.request')
        user = self.current_user
        if user:
            # set new login cookie
            # because single-user cookie may have been cleared or incorrect
            self.set_login_cookie(user)
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
                        auto_login_url = url_concat(
                            auto_login_url, {'next': self.get_next_url()}
                        )
                    self.redirect(auto_login_url)
                return
            username = self.get_argument('username', default='')

            # always set a fresh xsrf cookie when the login page is rendered
            # ensures we are as far from expiration as possible
            # to restart the timer
            xsrf_token = self.xsrf_token
            if self.request.headers.get("Sec-Fetch-Mode", "navigate") == "navigate":
                _set_xsrf_cookie(
                    self,
                    self._xsrf_token_id,
                    cookie_path=self.hub.base_url,
                    xsrf_token=xsrf_token,
                )
            self.finish(await self._render(username=username))

    async def post(self):
        # parse the arguments dict
        data = {}
        for arg in self.request.body_arguments:
            if arg == "_xsrf":
                # don't include xsrf token in auth input
                continue
            # strip username, but not other fields like passwords,
            # which should be allowed to start or end with space
            data[arg] = self.get_argument(arg, strip=arg == "username")

        auth_timer = self.statsd.timer('login.authenticate').start()
        user = await self.login_user(data)
        auth_timer.stop(send=False)

        if user:
            # register current user for subsequent requests to user (e.g. logging the request)
            self._jupyterhub_user = user
            self.redirect(self.get_next_url(user))
        else:
            self.set_status(403)
            html = await self._render(
                login_error='Invalid username or password', username=data['username']
            )
            self.finish(html)


# /login renders the login page or the "Login with..." link,
# so it should always be registered.
# /logout clears cookies.
default_handlers = [(r"/login", LoginHandler), (r"/logout", LogoutHandler)]
