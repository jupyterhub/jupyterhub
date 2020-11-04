"""Basic html-rendering handlers."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import time
from collections import defaultdict
from datetime import datetime
from http.client import responses

from jinja2 import TemplateNotFound
from tornado import web
from tornado.httputil import url_concat
from tornado.httputil import urlparse

from .. import __version__
from .. import orm
from ..metrics import SERVER_POLL_DURATION_SECONDS
from ..metrics import ServerPollStatus
from ..pagination import Pagination
from ..utils import admin_only
from ..utils import maybe_future
from ..utils import url_path_join
from .base import BaseHandler


class RootHandler(BaseHandler):
    """Render the Hub root page.

    If next argument is passed by single-user server,
    redirect to base_url + single-user page.

    If logged in, redirects to:

    - single-user server if settings.redirect_to_server (default)
    - hub home, otherwise

    Otherwise, renders login page.
    """

    def get(self):
        user = self.current_user
        if self.default_url:
            url = self.default_url
        elif user:
            url = self.get_next_url(user)
        else:
            url = self.settings['login_url']
        self.redirect(url)


class HomeHandler(BaseHandler):
    """Render the user's home page."""

    @web.authenticated
    async def get(self):
        user = self.current_user
        if user.running:
            # trigger poll_and_notify event in case of a server that died
            await user.spawner.poll_and_notify()

        # send the user to /spawn if they have no active servers,
        # to establish that this is an explicit spawn request rather
        # than an implicit one, which can be caused by any link to `/user/:name(/:server_name)`
        if user.active:
            url = url_path_join(self.base_url, 'user', user.escaped_name)
        else:
            url = url_path_join(self.hub.base_url, 'spawn', user.escaped_name)

        auth_state = await user.get_auth_state()
        html = self.render_template(
            'home.html',
            auth_state=auth_state,
            user=user,
            url=url,
            allow_named_servers=self.allow_named_servers,
            named_server_limit_per_user=self.named_server_limit_per_user,
            url_path_join=url_path_join,
            # can't use user.spawners because the stop method of User pops named servers from user.spawners when they're stopped
            spawners=user.orm_user._orm_spawners,
            default_server=user.spawner,
        )
        self.finish(html)


class SpawnHandler(BaseHandler):
    """Handle spawning of single-user servers

    GET renders the form, POST handles form submission.

    If no `options_form` is enabled, GET triggers spawn directly.
    """

    default_url = None

    async def _render_form(self, for_user, spawner_options_form, message=''):
        auth_state = await for_user.get_auth_state()
        return self.render_template(
            'spawn.html',
            for_user=for_user,
            auth_state=auth_state,
            spawner_options_form=spawner_options_form,
            error_message=message,
            url=self.request.uri,
            spawner=for_user.spawner,
        )

    @web.authenticated
    async def get(self, for_user=None, server_name=''):
        """GET renders form for spawning with user-specified options

        or triggers spawn via redirect if there is no form.
        """

        user = current_user = self.current_user
        if for_user is not None and for_user != user.name:
            if not user.admin:
                raise web.HTTPError(
                    403, "Only admins can spawn on behalf of other users"
                )

            user = self.find_user(for_user)
            if user is None:
                raise web.HTTPError(404, "No such user: %s" % for_user)

        if server_name:
            if not self.allow_named_servers:
                raise web.HTTPError(400, "Named servers are not enabled.")
            if (
                self.named_server_limit_per_user > 0
                and server_name not in user.orm_spawners
            ):
                named_spawners = list(user.all_spawners(include_default=False))
                if self.named_server_limit_per_user <= len(named_spawners):
                    raise web.HTTPError(
                        400,
                        "User {} already has the maximum of {} named servers."
                        "  One must be deleted before a new server can be created".format(
                            user.name, self.named_server_limit_per_user
                        ),
                    )

        if not self.allow_named_servers and user.running:
            url = self.get_next_url(user, default=user.server_url(server_name))
            self.log.info("User is running: %s", user.name)
            self.redirect(url)
            return

        if server_name is None:
            server_name = ''

        spawner = user.spawners[server_name]

        pending_url = self._get_pending_url(user, server_name)

        # spawner is active, redirect back to get progress, etc.
        if spawner.ready:
            self.log.info("Server %s is already running", spawner._log_name)
            next_url = self.get_next_url(user, default=user.server_url(server_name))
            self.redirect(next_url)
            return

        elif spawner.active:
            self.log.info("Server %s is already active", spawner._log_name)
            self.redirect(pending_url)
            return

        # Add handler to spawner here so you can access query params in form rendering.
        spawner.handler = self

        # auth_state may be an input to options form,
        # so resolve the auth state hook here
        auth_state = await user.get_auth_state()
        await spawner.run_auth_state_hook(auth_state)

        # Try to start server directly when query arguments are passed.
        error_message = ''
        query_options = {}
        for key, byte_list in self.request.query_arguments.items():
            query_options[key] = [bs.decode('utf8') for bs in byte_list]

        # 'next' is reserved argument for redirect after spawn
        query_options.pop('next', None)

        if len(query_options) > 0:
            try:
                self.log.debug(
                    "Triggering spawn with supplied query arguments for %s",
                    spawner._log_name,
                )
                options = await maybe_future(spawner.options_from_query(query_options))
                pending_url = self._get_pending_url(user, server_name)
                return await self._wrap_spawn_single_user(
                    user, server_name, spawner, pending_url, options
                )
            except Exception as e:
                self.log.error(
                    "Failed to spawn single-user server with query arguments",
                    exc_info=True,
                )
                error_message = str(e)
                # fallback to behavior without failing query arguments

        spawner_options_form = await spawner.get_options_form()
        if spawner_options_form:
            self.log.debug("Serving options form for %s", spawner._log_name)
            form = await self._render_form(
                for_user=user,
                spawner_options_form=spawner_options_form,
                message=error_message,
            )
            self.finish(form)
        else:
            self.log.debug(
                "Triggering spawn with default options for %s", spawner._log_name
            )
            return await self._wrap_spawn_single_user(
                user, server_name, spawner, pending_url
            )

    @web.authenticated
    async def post(self, for_user=None, server_name=''):
        """POST spawns with user-specified options"""
        user = current_user = self.current_user
        if for_user is not None and for_user != user.name:
            if not user.admin:
                raise web.HTTPError(
                    403, "Only admins can spawn on behalf of other users"
                )
            user = self.find_user(for_user)
            if user is None:
                raise web.HTTPError(404, "No such user: %s" % for_user)

        spawner = user.spawners[server_name]

        if spawner.ready:
            raise web.HTTPError(400, "%s is already running" % (spawner._log_name))
        elif spawner.pending:
            raise web.HTTPError(
                400, "%s is pending %s" % (spawner._log_name, spawner.pending)
            )

        form_options = {}
        for key, byte_list in self.request.body_arguments.items():
            form_options[key] = [bs.decode('utf8') for bs in byte_list]
        for key, byte_list in self.request.files.items():
            form_options["%s_file" % key] = byte_list
        try:
            self.log.debug(
                "Triggering spawn with supplied form options for %s", spawner._log_name
            )
            options = await maybe_future(spawner.options_from_form(form_options))
            pending_url = self._get_pending_url(user, server_name)
            return await self._wrap_spawn_single_user(
                user, server_name, spawner, pending_url, options
            )
        except Exception as e:
            self.log.error(
                "Failed to spawn single-user server with form", exc_info=True
            )
            spawner_options_form = await user.spawner.get_options_form()
            form = await self._render_form(
                for_user=user, spawner_options_form=spawner_options_form, message=str(e)
            )
            self.finish(form)
            return
        if current_user is user:
            self.set_login_cookie(user)
        next_url = self.get_next_url(
            user,
            default=url_path_join(
                self.hub.base_url, "spawn-pending", user.escaped_name, server_name
            ),
        )
        self.redirect(next_url)

    def _get_pending_url(self, user, server_name):
        # resolve `?next=...`, falling back on the spawn-pending url
        # must not be /user/server for named servers,
        # which may get handled by the default server if they aren't ready yet

        pending_url = url_path_join(
            self.hub.base_url, "spawn-pending", user.escaped_name, server_name
        )

        pending_url = self.append_query_parameters(pending_url, exclude=['next'])

        if self.get_argument('next', None):
            # preserve `?next=...` through spawn-pending
            pending_url = url_concat(pending_url, {'next': self.get_argument('next')})

        return pending_url

    async def _wrap_spawn_single_user(
        self, user, server_name, spawner, pending_url, options=None
    ):
        # Explicit spawn request: clear _spawn_future
        # which may have been saved to prevent implicit spawns
        # after a failure.
        if spawner._spawn_future and spawner._spawn_future.done():
            spawner._spawn_future = None
        # not running, no form. Trigger spawn and redirect back to /user/:name
        f = asyncio.ensure_future(
            self.spawn_single_user(user, server_name, options=options)
        )
        done, pending = await asyncio.wait([f], timeout=1)
        # If spawn_single_user throws an exception, raise a 500 error
        # otherwise it may cause a redirect loop
        if f.done() and f.exception():
            exc = f.exception()
            raise web.HTTPError(
                500,
                "Error in Authenticator.pre_spawn_start: %s %s"
                % (type(exc).__name__, str(exc)),
            )
        return self.redirect(pending_url)


class SpawnPendingHandler(BaseHandler):
    """Handle /hub/spawn-pending/:user/:server

    One and only purpose:

    - wait for pending spawn
    - serve progress bar
    - redirect to /user/:name when ready
    - show error if spawn failed

    Functionality split out of /user/:name handler to
    have clearer behavior at the right time.

    Requests for this URL will never trigger any actions
    such as spawning new servers.
    """

    @web.authenticated
    async def get(self, for_user, server_name=''):
        user = current_user = self.current_user
        if for_user is not None and for_user != current_user.name:
            if not current_user.admin:
                raise web.HTTPError(
                    403, "Only admins can spawn on behalf of other users"
                )
            user = self.find_user(for_user)
            if user is None:
                raise web.HTTPError(404, "No such user: %s" % for_user)

        if server_name and server_name not in user.spawners:
            raise web.HTTPError(
                404, "%s has no such server %s" % (user.name, server_name)
            )

        spawner = user.spawners[server_name]

        if spawner.ready:
            # spawner is ready and waiting. Redirect to it.
            next_url = self.get_next_url(default=user.server_url(server_name))
            self.redirect(next_url)
            return

        # if spawning fails for any reason, point users to /hub/home to retry
        self.extra_error_html = self.spawn_home_error

        auth_state = await user.get_auth_state()

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
            self.log.error("Previous spawn for %s failed: %s", spawner._log_name, exc)
            spawn_url = url_path_join(
                self.hub.base_url, "spawn", user.escaped_name, server_name
            )
            self.set_status(500)
            html = self.render_template(
                "not_running.html",
                user=user,
                auth_state=auth_state,
                server_name=server_name,
                spawn_url=spawn_url,
                failed=True,
                failed_message=getattr(exc, 'jupyterhub_message', ''),
                exception=exc,
            )
            self.finish(html)
            return

        # Check for pending events. This should usually be the case
        # when we are on this page.
        # page could be pending spawn *or* stop
        if spawner.pending:
            self.log.info("%s is pending %s", spawner._log_name, spawner.pending)
            # spawn has started, but not finished
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
                auth_state=auth_state,
            )
            self.finish(html)
            return

        # spawn is supposedly ready, check on the status
        if spawner.ready:
            poll_start_time = time.perf_counter()
            status = await spawner.poll()
            SERVER_POLL_DURATION_SECONDS.labels(
                status=ServerPollStatus.from_status(status)
            ).observe(time.perf_counter() - poll_start_time)
        else:
            status = 0

        # server is not running, render "not running" page
        # further, set status to 404 because this is not
        # serving the expected page
        if status is not None:
            spawn_url = url_path_join(
                self.hub.base_url, "spawn", user.escaped_name, server_name
            )
            html = self.render_template(
                "not_running.html",
                user=user,
                auth_state=auth_state,
                server_name=server_name,
                spawn_url=spawn_url,
            )
            self.finish(html)
            return

        # we got here, server appears to be ready and running,
        # no longer pending.
        # redirect to the running server.

        next_url = self.get_next_url(default=user.server_url(server_name))
        self.redirect(next_url)


class AdminHandler(BaseHandler):
    """Render the admin page."""

    @web.authenticated
    @admin_only
    async def get(self):
        page, per_page, offset = Pagination(config=self.config).get_page_args(self)

        available = {'name', 'admin', 'running', 'last_activity'}
        default_sort = ['admin', 'name']
        mapping = {'running': orm.Spawner.server_id}
        for name in available:
            if name not in mapping:
                table = orm.User if name != "last_activity" else orm.Spawner
                mapping[name] = getattr(table, name)

        default_order = {
            'name': 'asc',
            'last_activity': 'desc',
            'admin': 'desc',
            'running': 'desc',
        }

        sorts = self.get_arguments('sort') or default_sort
        orders = self.get_arguments('order')

        for bad in set(sorts).difference(available):
            self.log.warning("ignoring invalid sort: %r", bad)
            sorts.remove(bad)
        for bad in set(orders).difference({'asc', 'desc'}):
            self.log.warning("ignoring invalid order: %r", bad)
            orders.remove(bad)

        # add default sort as secondary
        for s in default_sort:
            if s not in sorts:
                sorts.append(s)
        if len(orders) < len(sorts):
            for col in sorts[len(orders) :]:
                orders.append(default_order[col])
        else:
            orders = orders[: len(sorts)]

        # this could be one incomprehensible nested list comprehension
        # get User columns
        cols = [mapping[c] for c in sorts]
        # get User.col.desc() order objects
        ordered = [getattr(c, o)() for c, o in zip(cols, orders)]

        users = (
            self.db.query(orm.User)
            .outerjoin(orm.Spawner)
            .order_by(*ordered)
            .limit(per_page)
            .offset(offset)
        )
        users = [self._user_from_orm(u) for u in users]

        running = []
        for u in users:
            running.extend(s for s in u.spawners.values() if s.active)

        total = self.db.query(orm.User.id).count()
        pagination = Pagination(
            url=self.request.uri,
            total=total,
            page=page,
            per_page=per_page,
            config=self.config,
        )

        auth_state = await self.current_user.get_auth_state()
        html = self.render_template(
            'admin.html',
            current_user=self.current_user,
            auth_state=auth_state,
            admin_access=self.settings.get('admin_access', False),
            users=users,
            running=running,
            sort={s: o for s, o in zip(sorts, orders)},
            allow_named_servers=self.allow_named_servers,
            named_server_limit_per_user=self.named_server_limit_per_user,
            server_version='{} {}'.format(__version__, self.version_hash),
            pagination=pagination,
        )
        self.finish(html)


class TokenPageHandler(BaseHandler):
    """Handler for page requesting new API tokens"""

    @web.authenticated
    async def get(self):
        never = datetime(1900, 1, 1)

        user = self.current_user

        def sort_key(token):
            return (token.last_activity or never, token.created or never)

        now = datetime.utcnow()
        api_tokens = []
        for token in sorted(user.api_tokens, key=sort_key, reverse=True):
            if token.expires_at and token.expires_at < now:
                self.db.delete(token)
                self.db.commit()
                continue
            api_tokens.append(token)

        # group oauth client tokens by client id
        # AccessTokens have expires_at as an integer timestamp
        now_timestamp = now.timestamp()
        oauth_tokens = defaultdict(list)
        for token in user.oauth_tokens:
            if token.expires_at and token.expires_at < now_timestamp:
                self.log.warning("Deleting expired token")
                self.db.delete(token)
                self.db.commit()
                continue
            if not token.client_id:
                # token should have been deleted when client was deleted
                self.log.warning("Deleting stale oauth token for %s", user.name)
                self.db.delete(token)
                self.db.commit()
                continue
            oauth_tokens[token.client_id].append(token)

        # get the earliest created and latest last_activity
        # timestamp for a given oauth client
        oauth_clients = []
        for client_id, tokens in oauth_tokens.items():
            created = tokens[0].created
            last_activity = tokens[0].last_activity
            for token in tokens[1:]:
                if token.created < created:
                    created = token.created
                if last_activity is None or (
                    token.last_activity and token.last_activity > last_activity
                ):
                    last_activity = token.last_activity
            token = tokens[0]
            oauth_clients.append(
                {
                    'client': token.client,
                    'description': token.client.description or token.client.identifier,
                    'created': created,
                    'last_activity': last_activity,
                    'tokens': tokens,
                    # only need one token id because
                    # revoking one oauth token revokes all oauth tokens for that client
                    'token_id': tokens[0].api_id,
                    'token_count': len(tokens),
                }
            )

        # sort oauth clients by last activity, created
        def sort_key(client):
            return (client['last_activity'] or never, client['created'] or never)

        oauth_clients = sorted(oauth_clients, key=sort_key, reverse=True)

        auth_state = await self.current_user.get_auth_state()
        html = self.render_template(
            'token.html',
            api_tokens=api_tokens,
            oauth_clients=oauth_clients,
            auth_state=auth_state,
        )
        self.finish(html)


class ProxyErrorHandler(BaseHandler):
    """Handler for rendering proxy error pages"""

    def get(self, status_code_s):
        status_code = int(status_code_s)
        status_message = responses.get(status_code, 'Unknown HTTP Error')
        # build template namespace

        hub_home = url_path_join(self.hub.base_url, 'home')
        message_html = ''
        if status_code == 503:
            message_html = ' '.join(
                [
                    "Your server appears to be down.",
                    "Try restarting it <a href='%s'>from the hub</a>" % hub_home,
                ]
            )
        ns = dict(
            status_code=status_code,
            status_message=status_message,
            message_html=message_html,
            logo_url=hub_home,
        )

        self.set_header('Content-Type', 'text/html')
        # render the template
        try:
            html = self.render_template('%s.html' % status_code, **ns)
        except TemplateNotFound:
            self.log.debug("No template for %d", status_code)
            html = self.render_template('error.html', **ns)

        self.write(html)


class HealthCheckHandler(BaseHandler):
    """Serve health check probes as quickly as possible"""

    # There is nothing for us to do other than return a positive
    # HTTP status code as quickly as possible for GET or HEAD requests
    def get(self):
        pass

    head = get


default_handlers = [
    (r'/', RootHandler),
    (r'/home', HomeHandler),
    (r'/admin', AdminHandler),
    (r'/spawn-pending/([^/]+)', SpawnPendingHandler),
    (r'/spawn-pending/([^/]+)/([^/]+)', SpawnPendingHandler),
    (r'/spawn', SpawnHandler),
    (r'/spawn/([^/]+)', SpawnHandler),
    (r'/spawn/([^/]+)/([^/]+)', SpawnHandler),
    (r'/token', TokenPageHandler),
    (r'/error/(\d+)', ProxyErrorHandler),
    (r'/health$', HealthCheckHandler),
]
