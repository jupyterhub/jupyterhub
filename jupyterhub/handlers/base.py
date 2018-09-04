"""HTTP Handlers for the hub server"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import copy
from datetime import datetime, timedelta
from http.client import responses
import json
import math
import random
import re
import time
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import uuid

from jinja2 import TemplateNotFound

from sqlalchemy.exc import SQLAlchemyError
from tornado.log import app_log
from tornado.httputil import url_concat, HTTPHeaders
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler
from tornado import gen, web

from .. import __version__
from .. import orm
from ..objects import Server
from ..spawner import LocalProcessSpawner
from ..utils import maybe_future, url_path_join
from ..metrics import (
    SERVER_SPAWN_DURATION_SECONDS, ServerSpawnStatus,
    PROXY_ADD_DURATION_SECONDS, ProxyAddStatus,
)

# pattern for the authentication token header
auth_header_pat = re.compile(r'^(?:token|bearer)\s+([^\s]+)$', flags=re.IGNORECASE)

# mapping of reason: reason_message
reasons = {
    'timeout': "Failed to reach your server."
        "  Please try again later."
        "  Contact admin if the issue persists.",
    'error': "Failed to start your server on the last attempt.  "
        "  Please contact admin if the issue persists.",
}

# constant, not configurable
SESSION_COOKIE_NAME = 'jupyterhub-session-id'

class BaseHandler(RequestHandler):
    """Base Handler class with access to common methods and properties."""

    @property
    def log(self):
        """I can't seem to avoid typing self.log"""
        return self.settings.get('log', app_log)

    @property
    def config(self):
        return self.settings.get('config', None)

    @property
    def base_url(self):
        return self.settings.get('base_url', '/')

    @property
    def default_url(self):
        return self.settings.get('default_url', '')

    @property
    def version_hash(self):
        return self.settings.get('version_hash', '')

    @property
    def subdomain_host(self):
        return self.settings.get('subdomain_host', '')

    @property
    def allow_named_servers(self):
        return self.settings.get('allow_named_servers', False)

    @property
    def domain(self):
        return self.settings['domain']

    @property
    def db(self):
        return self.settings['db']

    @property
    def users(self):
        return self.settings.setdefault('users', {})

    @property
    def services(self):
        return self.settings.setdefault('services', {})

    @property
    def hub(self):
        return self.settings['hub']

    @property
    def proxy(self):
        return self.settings['proxy']

    @property
    def statsd(self):
        return self.settings['statsd']

    @property
    def authenticator(self):
        return self.settings.get('authenticator', None)

    @property
    def oauth_provider(self):
        return self.settings['oauth_provider']

    def finish(self, *args, **kwargs):
        """Roll back any uncommitted transactions from the handler."""
        if self.db.dirty:
            self.log.warning("Rolling back dirty objects %s", self.db.dirty)
            self.db.rollback()
        super().finish(*args, **kwargs)

    #---------------------------------------------------------------
    # Security policies
    #---------------------------------------------------------------

    @property
    def csp_report_uri(self):
        return self.settings.get('csp_report_uri',
            url_path_join(self.hub.base_url, 'security/csp-report')
        )

    @property
    def content_security_policy(self):
        """The default Content-Security-Policy header

        Can be overridden by defining Content-Security-Policy in settings['headers']
        """
        return '; '.join([
            "frame-ancestors 'self'",
            "report-uri " + self.csp_report_uri,
        ])

    def get_content_type(self):
        return 'text/html'

    def set_default_headers(self):
        """
        Set any headers passed as tornado_settings['headers'].

        By default sets Content-Security-Policy of frame-ancestors 'self'.
        Also responsible for setting content-type header
        """
        # wrap in HTTPHeaders for case-insensitivity
        headers = HTTPHeaders(self.settings.get('headers', {}))
        headers.setdefault("X-JupyterHub-Version", __version__)

        for header_name, header_content in headers.items():
            self.set_header(header_name, header_content)

        if 'Access-Control-Allow-Headers' not in headers:
            self.set_header('Access-Control-Allow-Headers', 'accept, content-type, authorization')
        if 'Content-Security-Policy' not in headers:
            self.set_header('Content-Security-Policy', self.content_security_policy)
        self.set_header('Content-Type', self.get_content_type())

    #---------------------------------------------------------------
    # Login and cookie-related
    #---------------------------------------------------------------

    @property
    def admin_users(self):
        return self.settings.setdefault('admin_users', set())

    @property
    def cookie_max_age_days(self):
        return self.settings.get('cookie_max_age_days', None)

    @property
    def redirect_to_server(self):
        return self.settings.get('redirect_to_server', True)

    def get_auth_token(self):
        """Get the authorization token from Authorization header"""
        auth_header = self.request.headers.get('Authorization', '')
        match = auth_header_pat.match(auth_header)
        if not match:
            return None
        return match.group(1)

    def get_current_user_oauth_token(self):
        """Get the current user identified by OAuth access token

        Separate from API token because OAuth access tokens
        can only be used for identifying users,
        not using the API.
        """
        token = self.get_auth_token()
        if token is None:
            return None
        orm_token = orm.OAuthAccessToken.find(self.db, token)
        if orm_token is None:
            return None
        orm_token.last_activity = \
            orm_token.user.last_activity = datetime.utcnow()
        self.db.commit()
        return self._user_from_orm(orm_token.user)

    def get_current_user_token(self):
        """get_current_user from Authorization header token"""
        token = self.get_auth_token()
        if token is None:
            return None
        orm_token = orm.APIToken.find(self.db, token)
        if orm_token is None:
            return None
        else:
            # record token activity
            now = datetime.utcnow()
            orm_token.last_activity = now
            if orm_token.user:
                orm_token.user.last_activity = now

            self.db.commit()
            return orm_token.service or self._user_from_orm(orm_token.user)

    def _user_for_cookie(self, cookie_name, cookie_value=None):
        """Get the User for a given cookie, if there is one"""
        cookie_id = self.get_secure_cookie(
            cookie_name,
            cookie_value,
            max_age_days=self.cookie_max_age_days,
        )
        def clear():
            self.clear_cookie(cookie_name, path=self.hub.base_url)

        if cookie_id is None:
            if self.get_cookie(cookie_name):
                self.log.warning("Invalid or expired cookie token")
                clear()
            return
        cookie_id = cookie_id.decode('utf8', 'replace')
        u = self.db.query(orm.User).filter(orm.User.cookie_id==cookie_id).first()
        user = self._user_from_orm(u)
        if user is None:
            self.log.warning("Invalid cookie token")
            # have cookie, but it's not valid. Clear it and start over.
            clear()
            return
        # update user activity
        user.last_activity = datetime.utcnow()
        self.db.commit()
        return user

    def _user_from_orm(self, orm_user):
        """return User wrapper from orm.User object"""
        if orm_user is None:
            return
        return self.users[orm_user]

    def get_current_user_cookie(self):
        """get_current_user from a cookie token"""
        return self._user_for_cookie(self.hub.cookie_name)

    def get_current_user(self):
        """get current username"""
        if not hasattr(self, '_jupyterhub_user'):
            try:
                user = self.get_current_user_token()
                if user is None:
                    user = self.get_current_user_cookie()
                self._jupyterhub_user = user
            except Exception:
                # don't let errors here raise more than once
                self._jupyterhub_user = None
                raise
        return self._jupyterhub_user

    def find_user(self, name):
        """Get a user by name

        return None if no such user
        """
        orm_user = orm.User.find(db=self.db, name=name)
        return self._user_from_orm(orm_user)

    def user_from_username(self, username):
        """Get User for username, creating if it doesn't exist"""
        user = self.find_user(username)
        if user is None:
            # not found, create and register user
            u = orm.User(name=username)
            self.db.add(u)
            self.db.commit()
            user = self._user_from_orm(u)
        return user

    def clear_login_cookie(self, name=None):
        kwargs = {}
        if self.subdomain_host:
            kwargs['domain'] = self.domain
        user = self.get_current_user_cookie()
        session_id = self.get_session_cookie()
        if session_id:
            # clear session id
            self.clear_cookie(SESSION_COOKIE_NAME, **kwargs)

            if user:
                # user is logged in, clear any tokens associated with the current session
                # don't clear session tokens if not logged in,
                # because that could be a malicious logout request!
                count = 0
                for access_token in (
                    self.db.query(orm.OAuthAccessToken)
                    .filter(orm.OAuthAccessToken.user_id==user.id)
                    .filter(orm.OAuthAccessToken.session_id==session_id)
                ):
                    self.db.delete(access_token)
                    count += 1
                if count:
                    self.log.debug("Deleted %s access tokens for %s", count, user.name)
                    self.db.commit()


        # clear hub cookie
        self.clear_cookie(self.hub.cookie_name, path=self.hub.base_url, **kwargs)
        # clear services cookie
        self.clear_cookie('jupyterhub-services', path=url_path_join(self.base_url, 'services'), **kwargs)

    def _set_cookie(self, key, value, encrypted=True, **overrides):
        """Setting any cookie should go through here

        if encrypted use tornado's set_secure_cookie,
        otherwise set plaintext cookies.
        """
        # tornado <4.2 have a bug that consider secure==True as soon as
        # 'secure' kwarg is passed to set_secure_cookie
        kwargs = {
            'httponly': True,
        }
        if  self.request.protocol == 'https':
            kwargs['secure'] = True
        if self.subdomain_host:
            kwargs['domain'] = self.domain

        kwargs.update(self.settings.get('cookie_options', {}))
        kwargs.update(overrides)

        if encrypted:
            set_cookie = self.set_secure_cookie
        else:
            set_cookie = self.set_cookie

        self.log.debug("Setting cookie %s: %s", key, kwargs)
        set_cookie(key, value, **kwargs)


    def _set_user_cookie(self, user, server):
        self.log.debug("Setting cookie for %s: %s", user.name, server.cookie_name)
        self._set_cookie(
            server.cookie_name,
            user.cookie_id,
            encrypted=True,
            path=server.base_url,
        )

    def get_session_cookie(self):
        """Get the session id from a cookie

        Returns None if no session id is stored
        """
        return self.get_cookie(SESSION_COOKIE_NAME, None)

    def set_session_cookie(self):
        """Set a new session id cookie

        new session id is returned

        Session id cookie is *not* encrypted,
        so other services on this domain can read it.
        """
        session_id = uuid.uuid4().hex
        self._set_cookie(SESSION_COOKIE_NAME, session_id, encrypted=False)
        return session_id

    def set_service_cookie(self, user):
        """set the login cookie for services"""
        self._set_user_cookie(user, orm.Server(
            cookie_name='jupyterhub-services',
            base_url=url_path_join(self.base_url, 'services')
        ))

    def set_hub_cookie(self, user):
        """set the login cookie for the Hub"""
        self._set_user_cookie(user, self.hub)

    def set_login_cookie(self, user):
        """Set login cookies for the Hub and single-user server."""
        if self.subdomain_host and not self.request.host.startswith(self.domain):
            self.log.warning(
                "Possibly setting cookie on wrong domain: %s != %s",
                self.request.host, self.domain)

        # set single cookie for services
        if self.db.query(orm.Service).filter(orm.Service.server != None).first():
            self.set_service_cookie(user)

        if not self.get_session_cookie():
            self.set_session_cookie()

        # create and set a new cookie token for the hub
        if not self.get_current_user_cookie():
            self.set_hub_cookie(user)

    def authenticate(self, data):
        return maybe_future(self.authenticator.get_authenticated_user(self, data))

    def get_next_url(self, user=None):
        """Get the next_url for login redirect

        Default URL after login:

        - if redirect_to_server (default): send to user's own server
        - else: /hub/home
        """
        next_url = self.get_argument('next', default='')
        if (next_url + '/').startswith(
            (
                '%s://%s/' % (self.request.protocol, self.request.host),
                '//%s/' % self.request.host,
            )
        ):
            # treat absolute URLs for our host as absolute paths:
            parsed = urlparse(next_url)
            next_url = parsed.path
            if parsed.query:
                next_url = next_url + '?' + parsed.query
            if parsed.hash:
                next_url = next_url + '#' + parsed.hash
        if next_url and (urlparse(next_url).netloc or not next_url.startswith('/')):
            self.log.warning("Disallowing redirect outside JupyterHub: %r", next_url)
            next_url = ''
        if next_url and next_url.startswith(url_path_join(self.base_url, 'user/')):
            # add /hub/ prefix, to ensure we redirect to the right user's server.
            # The next request will be handled by SpawnHandler,
            # ultimately redirecting to the logged-in user's server.
            without_prefix = next_url[len(self.base_url):]
            next_url = url_path_join(self.hub.base_url, without_prefix)
            self.log.warning("Redirecting %s to %s. For sharing public links, use /user-redirect/",
                self.request.uri, next_url,
            )

        if not next_url:
            # custom default URL
            next_url = self.default_url

        if not next_url:
            # default URL after login
            # if self.redirect_to_server, default login URL initiates spawn,
            # otherwise send to Hub home page (control panel)
            if user and self.redirect_to_server:
                next_url = user.url
            else:
                next_url = url_path_join(self.hub.base_url, 'home')
        return next_url

    async def login_user(self, data=None):
        """Login a user"""
        auth_timer = self.statsd.timer('login.authenticate').start()
        authenticated = await self.authenticate(data)
        auth_timer.stop(send=False)

        if authenticated:
            username = authenticated['name']
            auth_state = authenticated.get('auth_state')
            admin = authenticated.get('admin')
            new_user = username not in self.users
            user = self.user_from_username(username)
            if new_user:
                await maybe_future(self.authenticator.add_user(user))
            # Only set `admin` if the authenticator returned an explicit value.
            if admin is not None and admin != user.admin:
                user.admin = admin
                self.db.commit()
            # always set auth_state and commit,
            # because there could be key-rotation or clearing of previous values
            # going on.
            if not self.authenticator.enable_auth_state:
                # auth_state is not enabled. Force None.
                auth_state = None
            await user.save_auth_state(auth_state)
            self.db.commit()
            self.set_login_cookie(user)
            self.statsd.incr('login.success')
            self.statsd.timing('login.authenticate.success', auth_timer.ms)
            self.log.info("User logged in: %s", username)
            return user
        else:
            self.statsd.incr('login.failure')
            self.statsd.timing('login.authenticate.failure', auth_timer.ms)
            self.log.warning("Failed login for %s", (data or {}).get('username', 'unknown user'))


    #---------------------------------------------------------------
    # spawning-related
    #---------------------------------------------------------------

    @property
    def slow_spawn_timeout(self):
        return self.settings.get('slow_spawn_timeout', 10)

    @property
    def slow_stop_timeout(self):
        return self.settings.get('slow_stop_timeout', 10)

    @property
    def spawner_class(self):
        return self.settings.get('spawner_class', LocalProcessSpawner)

    @property
    def concurrent_spawn_limit(self):
        return self.settings.get('concurrent_spawn_limit', 0)

    @property
    def active_server_limit(self):
        return self.settings.get('active_server_limit', 0)

    async def spawn_single_user(self, user, server_name='', options=None):
        # in case of error, include 'try again from /hub/home' message
        spawn_start_time = time.perf_counter()
        self.extra_error_html = self.spawn_home_error

        user_server_name = user.name

        if server_name:
            user_server_name = '%s:%s' % (user.name, server_name)

        if server_name in user.spawners and user.spawners[server_name].pending:
            pending = user.spawners[server_name].pending
            SERVER_SPAWN_DURATION_SECONDS.labels(
                status=ServerSpawnStatus.already_pending
            ).observe(time.perf_counter() - spawn_start_time)
            raise RuntimeError("%s pending %s" % (user_server_name, pending))

        # count active servers and pending spawns
        # we could do careful bookkeeping to avoid
        # but for 10k users this takes ~5ms
        # and saves us from bookkeeping errors
        active_counts = self.users.count_active_users()
        spawn_pending_count = active_counts['spawn_pending'] + active_counts['proxy_pending']
        active_count = active_counts['active']

        concurrent_spawn_limit = self.concurrent_spawn_limit
        active_server_limit = self.active_server_limit

        if concurrent_spawn_limit and spawn_pending_count >= concurrent_spawn_limit:
            SERVER_SPAWN_DURATION_SECONDS.labels(
                status=ServerSpawnStatus.throttled
            ).observe(time.perf_counter() - spawn_start_time)
            # Suggest number of seconds client should wait before retrying
            # This helps prevent thundering herd problems, where users simply
            # immediately retry when we are overloaded.
            retry_range = self.settings['spawn_throttle_retry_range']
            retry_time = int(random.uniform(*retry_range))

            # round suggestion to nicer human value (nearest 10 seconds or minute)
            if retry_time <= 90:
                # round human seconds up to nearest 10
                human_retry_time = "%i0 seconds" % math.ceil(retry_time / 10.)
            else:
                # round number of minutes
                human_retry_time = "%i minutes" % math.round(retry_time / 60.)

            self.log.warning(
                '%s pending spawns, throttling. Suggested retry in %s seconds.',
                spawn_pending_count, retry_time,
            )
            err = web.HTTPError(
                429,
                "Too many users trying to log in right now. Try again in {}.".format(human_retry_time)
            )
            # can't call set_header directly here because it gets ignored
            # when errors are raised
            # we handle err.headers ourselves in Handler.write_error
            err.headers = {'Retry-After': retry_time}
            raise err

        if active_server_limit and active_count >= active_server_limit:
            self.log.info(
                '%s servers active, no space available',
                active_count,
            )
            SERVER_SPAWN_DURATION_SECONDS.labels(
                status=ServerSpawnStatus.too_many_users
            ).observe(time.perf_counter() - spawn_start_time)
            raise web.HTTPError(429, "Active user limit exceeded. Try again in a few minutes.")

        tic = IOLoop.current().time()

        self.log.debug("Initiating spawn for %s", user_server_name)

        spawn_future = user.spawn(server_name, options, handler=self)

        self.log.debug("%i%s concurrent spawns",
            spawn_pending_count,
            '/%i' % concurrent_spawn_limit if concurrent_spawn_limit else '')
        self.log.debug("%i%s active servers",
            active_count,
            '/%i' % active_server_limit if active_server_limit else '')

        spawner = user.spawners[server_name]
        # set spawn_pending now, so there's no gap where _spawn_pending is False
        # while we are waiting for _proxy_pending to be set
        spawner._spawn_pending = True

        async def finish_user_spawn():
            """Finish the user spawn by registering listeners and notifying the proxy.

            If the spawner is slow to start, this is passed as an async callback,
            otherwise it is called immediately.
            """
            # wait for spawn Future
            await spawn_future
            toc = IOLoop.current().time()
            self.log.info("User %s took %.3f seconds to start", user_server_name, toc-tic)
            self.statsd.timing('spawner.success', (toc - tic) * 1000)
            SERVER_SPAWN_DURATION_SECONDS.labels(
                status=ServerSpawnStatus.success
            ).observe(time.perf_counter() - spawn_start_time)
            proxy_add_start_time = time.perf_counter()
            spawner._proxy_pending = True
            try:
                await self.proxy.add_user(user, server_name)

                PROXY_ADD_DURATION_SECONDS.labels(
                    status='success'
                ).observe(
                    time.perf_counter() - proxy_add_start_time
                )
            except Exception:
                self.log.exception("Failed to add %s to proxy!", user_server_name)
                self.log.error("Stopping %s to avoid inconsistent state", user_server_name)
                await user.stop()
                PROXY_ADD_DURATION_SECONDS.labels(
                    status='failure'
                ).observe(
                    time.perf_counter() - proxy_add_start_time
                )
            else:
                spawner.add_poll_callback(self.user_stopped, user, server_name)
            finally:
                spawner._proxy_pending = False

        # hook up spawner._spawn_future so that other requests can await
        # this result
        finish_spawn_future = spawner._spawn_future = maybe_future(finish_user_spawn())

        def _clear_spawn_future(f):
            # clear spawner._spawn_future when it's done
            # keep an exception around, though, to prevent repeated implicit spawns
            # if spawn is failing
            if f.exception() is None:
                spawner._spawn_future = None
            # Now we're all done. clear _spawn_pending flag
            spawner._spawn_pending = False

        finish_spawn_future.add_done_callback(_clear_spawn_future)

        # when spawn finishes (success or failure)
        # update failure count and abort if consecutive failure limit
        # is reached
        def _track_failure_count(f):
            if f.exception() is None:
                # spawn succeeded, reset failure count
                self.settings['failure_count'] = 0
                return
            # spawn failed, increment count and abort if limit reached
            self.settings.setdefault('failure_count', 0)
            self.settings['failure_count'] += 1
            failure_count = self.settings['failure_count']
            failure_limit = spawner.consecutive_failure_limit
            if failure_limit and 1 < failure_count < failure_limit:
                self.log.warning(
                    "%i consecutive spawns failed.  "
                    "Hub will exit if failure count reaches %i before succeeding",
                    failure_count, failure_limit,
                )
            if failure_limit and failure_count >= failure_limit:
                self.log.critical(
                    "Aborting due to %i consecutive spawn failures", failure_count
                )
                # abort in 2 seconds to allow pending handlers to resolve
                # mostly propagating errors for the current failures
                def abort():
                    raise SystemExit(1)
                IOLoop.current().call_later(2, abort)

        finish_spawn_future.add_done_callback(_track_failure_count)

        try:
            await gen.with_timeout(
                timedelta(seconds=self.slow_spawn_timeout), finish_spawn_future
            )
        except gen.TimeoutError:
            # waiting_for_response indicates server process has started,
            # but is yet to become responsive.
            if spawner._spawn_pending and not spawner._waiting_for_response:
                # still in Spawner.start, which is taking a long time
                # we shouldn't poll while spawn is incomplete.
                self.log.warning("User %s is slow to start (timeout=%s)",
                                 user_server_name, self.slow_spawn_timeout)
                return

            # start has finished, but the server hasn't come up
            # check if the server died while we were waiting
            status = await spawner.poll()
            if status is not None:
                toc = IOLoop.current().time()
                self.statsd.timing('spawner.failure', (toc - tic) * 1000)
                SERVER_SPAWN_DURATION_SECONDS.labels(
                    status=ServerSpawnStatus.failure
                ).observe(time.perf_counter() - spawn_start_time)
                raise web.HTTPError(500, "Spawner failed to start [status=%s]. The logs for %s may contain details." % (
                    status, spawner._log_name))

            if spawner._waiting_for_response:
                # hit timeout waiting for response, but server's running.
                # Hope that it'll show up soon enough,
                # though it's possible that it started at the wrong URL
                self.log.warning("User %s is slow to become responsive (timeout=%s)",
                                 user_server_name, self.slow_spawn_timeout)
                self.log.debug("Expecting server for %s at: %s",
                               user_server_name, spawner.server.url)
            if spawner._proxy_pending:
                # User.spawn finished, but it hasn't been added to the proxy
                # Could be due to load or a slow proxy
                self.log.warning("User %s is slow to be added to the proxy (timeout=%s)",
                                 user_server_name, self.slow_spawn_timeout)

    async def user_stopped(self, user, server_name):
        """Callback that fires when the spawner has stopped"""
        spawner = user.spawners[server_name]
        status = await spawner.poll()
        if status is None:
            status = 'unknown'
        self.log.warning("User %s server stopped, with exit code: %s",
            user.name, status,
        )
        await self.proxy.delete_user(user, server_name)
        await user.stop(server_name)

    async def stop_single_user(self, user, name=''):
        if name not in user.spawners:
            raise KeyError("User %s has no such spawner %r", user.name, name)
        spawner = user.spawners[name]
        if spawner.pending:
            raise RuntimeError("%s pending %s" % (spawner._log_name, spawner.pending))
        # set user._stop_pending before doing anything async
        # to avoid races
        spawner._stop_pending = True

        async def stop():
            """Stop the server

            1. remove it from the proxy
            2. stop the server
            3. notice that it stopped
            """
            tic = IOLoop.current().time()
            try:
                await self.proxy.delete_user(user, name)
                await user.stop(name)
            finally:
                spawner._stop_pending = False
            toc = IOLoop.current().time()
            self.log.info("User %s server took %.3f seconds to stop", user.name, toc - tic)
            self.statsd.timing('spawner.stop', (toc - tic) * 1000)

        try:
            await gen.with_timeout(timedelta(seconds=self.slow_stop_timeout), stop())
        except gen.TimeoutError:
            # hit timeout, but stop is still pending
            self.log.warning("User %s:%s server is slow to stop", user.name, name)

    #---------------------------------------------------------------
    # template rendering
    #---------------------------------------------------------------

    @property
    def spawn_home_error(self):
        """Extra message pointing users to try spawning again from /hub/home.

        Should be added to `self.extra_error_html` for any handler
        that could serve a failed spawn message.
        """
        home = url_path_join(self.hub.base_url, 'home')
        return (
            "You can try restarting your server from the "
            "<a href='{home}'>home page</a>.".format(home=home)
        )

    def get_template(self, name):
        """Return the jinja template object for a given name"""
        return self.settings['jinja2_env'].get_template(name)

    def render_template(self, name, **ns):
        template_ns = {}
        template_ns.update(self.template_namespace)
        template_ns.update(ns)
        template = self.get_template(name)
        return template.render(**template_ns)

    @property
    def template_namespace(self):
        user = self.get_current_user()
        ns = dict(
            base_url=self.hub.base_url,
            prefix=self.base_url,
            user=user,
            login_url=self.settings['login_url'],
            login_service=self.authenticator.login_service,
            logout_url=self.settings['logout_url'],
            static_url=self.static_url,
            version_hash=self.version_hash,
        )
        if self.settings['template_vars']:
            ns.update(self.settings['template_vars'])
        return ns

    def write_error(self, status_code, **kwargs):
        """render custom error pages"""
        exc_info = kwargs.get('exc_info')
        message = ''
        exception = None
        status_message = responses.get(status_code, 'Unknown HTTP Error')
        if exc_info:
            exception = exc_info[1]
            # get the custom message, if defined
            try:
                message = exception.log_message % exception.args
            except Exception:
                pass

            # construct the custom reason, if defined
            reason = getattr(exception, 'reason', '')
            if reason:
                message = reasons.get(reason, reason)

        if exception and isinstance(exception, SQLAlchemyError):
            self.log.warning("Rolling back session due to database error %s", exception)
            self.db.rollback()

        # build template namespace
        ns = dict(
            status_code=status_code,
            status_message=status_message,
            message=message,
            extra_error_html=getattr(self, 'extra_error_html', ''),
            exception=exception,
        )

        self.set_header('Content-Type', 'text/html')
        if isinstance(exception, web.HTTPError):
            # allow setting headers from exceptions
            # since exception handler clears headers
            headers = getattr(exception, 'headers', None)
            if headers:
                for key, value in headers.items():
                    self.set_header(key, value)
            # Content-Length must be recalculated.
            self.clear_header('Content-Length')

        # render the template
        try:
            html = self.render_template('%s.html' % status_code, **ns)
        except TemplateNotFound:
            self.log.debug("No template for %d", status_code)
            try:
                html = self.render_template('error.html', **ns)
            except:
                # In this case, any side effect must be avoided.
                ns['no_spawner_check'] = True
                html = self.render_template('error.html', **ns)

        self.write(html)


class Template404(BaseHandler):
    """Render our 404 template"""
    def prepare(self):
        raise web.HTTPError(404)


class PrefixRedirectHandler(BaseHandler):
    """Redirect anything outside a prefix inside.

    Redirects /foo to /prefix/foo, etc.
    """
    def get(self):
        uri = self.request.uri
        # Since self.base_url will end with trailing slash.
        # Ensure uri will end with trailing slash when matching
        # with self.base_url.
        if not uri.endswith('/'):
            uri += '/'
        if uri.startswith(self.base_url):
            path = self.request.uri[len(self.base_url):]
        else:
            path = self.request.path
        self.redirect(url_path_join(
            self.hub.base_url, path,
        ), permanent=False)


class UserSpawnHandler(BaseHandler):
    """Redirect requests to /user/name/* handled by the Hub.

    If logged in, spawn a single-user server and redirect request.
    If a user, alice, requests /user/bob/notebooks/mynotebook.ipynb,
    she will be redirected to /hub/user/bob/notebooks/mynotebook.ipynb,
    which will be handled by this handler,
    which will in turn send her to /user/alice/notebooks/mynotebook.ipynb.
    """

    def _fail_api_request(self, user):
        """Fail an API request to a not-running server"""
        self.set_status(404)
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"message": "%s is not running" % user.name}))
        self.finish()

    async def get(self, name, user_path):
        if not user_path:
            user_path = '/'
        current_user = self.get_current_user()
        if (
            current_user
            and current_user.name != name
            and current_user.admin
            and self.settings.get('admin_access', False)
        ):
            # allow admins to spawn on behalf of users
            user = self.find_user(name)
            if user is None:
                # no such user
                raise web.HTTPError(404, "No such user %s" % name)
            self.log.info("Admin %s requesting spawn on behalf of %s",
                          current_user.name, user.name)
            admin_spawn = True
            should_spawn = True
        else:
            user = current_user
            admin_spawn = False
            # For non-admins, we should spawn if the user matches
            # otherwise redirect users to their own server
            should_spawn = (current_user and current_user.name == name)

        if "api" in user_path.split("/") and not user.active:
            # API request for not-running server (e.g. notebook UI left open)
            # Avoid triggering a spawn.
            self._fail_api_request(user)
            return

        if should_spawn:
            # if spawning fails for any reason, point users to /hub/home to retry
            self.extra_error_html = self.spawn_home_error

            # If people visit /user/:name directly on the Hub,
            # the redirects will just loop, because the proxy is bypassed.
            # Try to check for that and warn,
            # though the user-facing behavior is unchanged
            host_info = urlparse(self.request.full_url())
            port = host_info.port
            if not port:
                port = 443 if host_info.scheme == 'https' else 80
            if port != Server.from_url(self.proxy.public_url).connect_port and port == self.hub.connect_port:
                self.log.warning("""
                    Detected possible direct connection to Hub's private ip: %s, bypassing proxy.
                    This will result in a redirect loop.
                    Make sure to connect to the proxied public URL %s
                    """, self.request.full_url(), self.proxy.public_url)

            # logged in as valid user, check for pending spawn
            spawner = user.spawner

            # First, check for previous failure.
            if (
                not spawner.active
                and spawner._spawn_future
                and spawner._spawn_future.done()
                and spawner._spawn_future.exception()
            ):
                # Condition: spawner not active and _spawn_future exists and contains an Exception
                # Implicit spawn on /user/:name is not allowed if the user's last spawn failed.
                # We should point the user to Home if the most recent spawn failed.
                exc = spawner._spawn_future.exception()
                self.log.error("Preventing implicit spawn for %s because last spawn failed: %s",
                    spawner._log_name, exc)
                # raise a copy because each time an Exception object is re-raised, its traceback grows
                raise copy.copy(exc).with_traceback(exc.__traceback__)

            # check for pending spawn
            if spawner.pending == 'spawn' and spawner._spawn_future:
                # wait on the pending spawn
                self.log.debug("Waiting for %s pending %s", spawner._log_name, spawner.pending)
                try:
                    await gen.with_timeout(timedelta(seconds=self.slow_spawn_timeout), spawner._spawn_future)
                except gen.TimeoutError:
                    self.log.info("Pending spawn for %s didn't finish in %.1f seconds", spawner._log_name, self.slow_spawn_timeout)
                    pass

            # we may have waited above, check pending again:
            # page could be pending spawn *or* stop
            if spawner.pending:
                self.log.info("%s is pending %s", spawner._log_name, spawner.pending)
                # spawn has started, but not finished
                self.statsd.incr('redirects.user_spawn_pending', 1)
                url_parts = []
                if spawner.pending == "stop":
                    page = "stop_pending.html"
                else:
                    page = "spawn_pending.html"
                html = self.render_template(
                    page,
                    user=user,
                    spawner=spawner,
                    progress_url=spawner._progress_url,
                )
                self.finish(html)
                return

            # spawn has supposedly finished, check on the status
            if spawner.ready:
                status = await spawner.poll()
            else:
                status = 0

            # server is not running, trigger spawn
            if status is not None:
                if spawner.options_form:
                    url_parts = [self.hub.base_url, 'spawn']
                    if current_user.name != user.name:
                        # spawning on behalf of another user
                        url_parts.append(user.name)
                    self.redirect(url_concat(url_path_join(*url_parts),
                                             {'next': self.request.uri}))
                    return
                else:
                    await self.spawn_single_user(user)

            # spawn didn't finish, show pending page
            if spawner.pending:
                self.log.info("%s is pending %s", spawner._log_name, spawner.pending)
                # spawn has started, but not finished
                self.statsd.incr('redirects.user_spawn_pending', 1)
                html = self.render_template(
                    "spawn_pending.html",
                    user=user,
                    progress_url=spawner._progress_url,
                )
                self.finish(html)
                return

            # We do exponential backoff here - since otherwise we can get stuck in a redirect loop!
            # This is important in many distributed proxy implementations - those are often eventually
            # consistent and can take up to a couple of seconds to actually apply throughout the cluster.
            try:
                redirects = int(self.get_argument('redirects', 0))
            except ValueError:
                self.log.warning("Invalid redirects argument %r", self.get_argument('redirects'))
                redirects = 0

            # check redirect limit to prevent browser-enforced limits.
            # In case of version mismatch, raise on only two redirects.
            if redirects >= self.settings.get(
                'user_redirect_limit', 4
            ) or (redirects >= 2 and spawner._jupyterhub_version != __version__):
                # We stop if we've been redirected too many times.
                msg = "Redirect loop detected."
                if spawner._jupyterhub_version != __version__:
                    msg += (
                        " Notebook has jupyterhub version {singleuser}, but the Hub expects {hub}."
                        " Try installing jupyterhub=={hub} in the user environment"
                        " if you continue to have problems."
                    ).format(
                        singleuser=spawner._jupyterhub_version or 'unknown (likely < 0.8)',
                        hub=__version__,
                    )
                raise web.HTTPError(500, msg)

            without_prefix = self.request.uri[len(self.hub.base_url):]
            target = url_path_join(self.base_url, without_prefix)
            if self.subdomain_host:
                target = user.host + target

            # record redirect count in query parameter
            if redirects:
                self.log.warning("Redirect loop detected on %s", self.request.uri)
                # add capped exponential backoff where cap is 10s
                await gen.sleep(min(1 * (2 ** redirects), 10))
                # rewrite target url with new `redirects` query value
                url_parts = urlparse(target)
                query_parts = parse_qs(url_parts.query)
                query_parts['redirects'] = redirects + 1
                url_parts = url_parts._replace(query=urlencode(query_parts))
                target = urlunparse(url_parts)
            else:
                target = url_concat(target, {'redirects': 1})

            self.redirect(target)
            self.statsd.incr('redirects.user_after_login')
        elif current_user:
            # logged in as a different user, redirect
            self.statsd.incr('redirects.user_to_user', 1)
            target = url_path_join(current_user.url, user_path or '')
            if self.request.query:
                # FIXME: use urlunparse instead?
                target += '?' + self.request.query
            self.redirect(target)
        else:
            # not logged in, clear any cookies and reload
            self.statsd.incr('redirects.user_to_login', 1)
            self.clear_login_cookie()
            self.redirect(url_concat(
                self.settings['login_url'],
                {'next': self.request.uri},
            ))


class UserRedirectHandler(BaseHandler):
    """Redirect requests to user servers.

    Allows public linking to "this file on your server".

    /user-redirect/path/to/foo will redirect to /user/:name/path/to/foo

    If the user is not logged in, send to login URL, redirecting back here.

    .. versionadded:: 0.7
    """
    @web.authenticated
    def get(self, path):
        user = self.get_current_user()
        url = url_path_join(user.url, path)
        if self.request.query:
            # FIXME: use urlunparse instead?
            url += '?' + self.request.query
        self.redirect(url)


class CSPReportHandler(BaseHandler):
    '''Accepts a content security policy violation report'''
    @web.authenticated
    def post(self):
        '''Log a content security policy violation report'''
        self.log.warning(
            "Content security violation: %s",
            self.request.body.decode('utf8', 'replace')
        )
        # Report it to statsd as well
        self.statsd.incr('csp_report')


class AddSlashHandler(BaseHandler):
    """Handler for adding trailing slash to URLs that need them"""
    def get(self, *args):
        src = urlparse(self.request.uri)
        dest = src._replace(path=src.path + '/')
        self.redirect(urlunparse(dest))

default_handlers = [
    (r'', AddSlashHandler),  # add trailing / to `/hub`
    (r'/user/([^/]+)(/.*)?', UserSpawnHandler),
    (r'/user-redirect/(.*)?', UserRedirectHandler),
    (r'/security/csp-report', CSPReportHandler),
]
