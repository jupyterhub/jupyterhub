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
        user = self.get_current_user()
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
        user = self.get_current_user()
        if user.running:
            # trigger poll_and_notify event in case of a server that died
            await user.spawner.poll_and_notify()

        # send the user to /spawn if they aren't running or pending a spawn,
        # to establish that this is an explicit spawn request rather
        # than an implicit one, which can be caused by any link to `/user/:name`
        url = user.url if user.spawner.active else url_path_join(self.hub.base_url, 'spawn')
        html = self.render_template('home.html',
            user=user,
            url=url,
        )
        self.finish(html)


class SpawnHandler(BaseHandler):
    """Handle spawning of single-user servers via form.

    GET renders the form, POST handles form submission.

    Only enabled when Spawner.options_form is defined.
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
    async def get(self, for_user=None):
        """GET renders form for spawning with user-specified options

        or triggers spawn via redirect if there is no form.
        """
        user = current_user = self.get_current_user()
        if for_user is not None and for_user != user.name:
            if not user.admin:
                raise web.HTTPError(403, "Only admins can spawn on behalf of other users")

            user = self.find_user(for_user)
            if user is None:
                raise web.HTTPError(404, "No such user: %s" % for_user)

        if not self.allow_named_servers and user.running:
            url = user.url
            self.log.debug("User is running: %s", url)
            self.redirect(url)
            return
        if user.spawner.options_form:
            form = await self._render_form(for_user=user)
            self.finish(form)
        else:
            # Explicit spawn request: clear _spawn_future
            # which may have been saved to prevent implicit spawns
            # after a failure.
            if user.spawner._spawn_future and user.spawner._spawn_future.done():
                user.spawner._spawn_future = None
            # not running, no form. Trigger spawn by redirecting to /user/:name
            url = user.url
            if self.request.query:
                # add query params
                url += '?' + self.request.query
            self.redirect(url)

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


class AdminHandler(BaseHandler):
    """Render the admin page."""

    @admin_only
    def get(self):
        available = {'name', 'admin', 'running', 'last_activity'}
        default_sort = ['admin', 'name']
        mapping = {
            'running': orm.Spawner.server_id,
        }
        for name in available:
            if name not in mapping:
                mapping[name] = getattr(orm.User, name)

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
            for col in sorts[len(orders):]:
                orders.append(default_order[col])
        else:
            orders = orders[:len(sorts)]

        # this could be one incomprehensible nested list comprehension
        # get User columns
        cols = [ mapping[c] for c in sorts ]
        # get User.col.desc() order objects
        ordered = [ getattr(c, o)() for c, o in zip(cols, orders) ]

        users = self.db.query(orm.User).outerjoin(orm.Spawner).order_by(*ordered)
        users = [ self._user_from_orm(u) for u in users ]
        running = [ u for u in users if u.running ]

        html = self.render_template('admin.html',
            user=self.get_current_user(),
            admin_access=self.settings.get('admin_access', False),
            users=users,
            running=running,
            sort={s:o for s,o in zip(sorts, orders)},
        )
        self.finish(html)


class TokenPageHandler(BaseHandler):
    """Handler for page requesting new API tokens"""

    @web.authenticated
    def get(self):
        never = datetime(1900, 1, 1)

        user = self.get_current_user()
        def sort_key(token):
            return (
                token.last_activity or never,
                token.created or never,
            )

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
                if (
                    last_activity is None or
                    (token.last_activity and token.last_activity > last_activity)
                ):
                    last_activity = token.last_activity
            token = tokens[0]
            oauth_clients.append({
                'client': token.client,
                'description': token.client.description or token.client.identifier,
                'created': created,
                'last_activity': last_activity,
                'tokens': tokens,
                # only need one token id because
                # revoking one oauth token revokes all oauth tokens for that client
                'token_id': tokens[0].api_id,
                'token_count': len(tokens),
            })

        # sort oauth clients by last activity, created
        def sort_key(client):
            return (
                client['last_activity'] or never,
                client['created'] or never,
            )

        oauth_clients = sorted(oauth_clients, key=sort_key, reverse=True)

        html = self.render_template(
            'token.html',
            api_tokens=api_tokens,
            oauth_clients=oauth_clients,
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
            message_html = ' '.join([
                "Your server appears to be down.",
                "Try restarting it <a href='%s'>from the hub</a>" % hub_home
            ])
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


default_handlers = [
    (r'/', RootHandler),
    (r'/home', HomeHandler),
    (r'/admin', AdminHandler),
    (r'/spawn', SpawnHandler),
    (r'/spawn/([^/]+)', SpawnHandler),
    (r'/token', TokenPageHandler),
    (r'/error/(\d+)', ProxyErrorHandler),
]
