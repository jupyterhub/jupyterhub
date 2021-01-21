"""User handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from async_generator import aclosing
from dateutil.parser import parse as parse_date
from sqlalchemy import func
from tornado import web
from tornado.iostream import StreamClosedError

from .. import orm
from ..user import User
from ..utils import admin_only
from ..utils import isoformat
from ..utils import iterate_until
from ..utils import maybe_future
from ..utils import url_path_join
from .base import APIHandler


class SelfAPIHandler(APIHandler):
    """Return the authenticated user's model

    Based on the authentication info. Acts as a 'whoami' for auth tokens.
    """

    async def get(self):
        user = self.current_user
        if user is None:
            # whoami can be accessed via oauth token
            user = self.get_current_user_oauth_token()
        if user is None:
            raise web.HTTPError(403)
        if isinstance(user, orm.Service):
            model = self.service_model(user)
        else:
            model = self.user_model(user)
        self.write(json.dumps(model))


class UserListAPIHandler(APIHandler):
    def _user_has_ready_spawner(self, orm_user):
        """Return True if a user has *any* ready spawners

        Used for filtering from active -> ready
        """
        user = self.users[orm_user]
        return any(spawner.ready for spawner in user.spawners.values())

    @admin_only
    def get(self):
        state_filter = self.get_argument("state", None)

        # post_filter
        post_filter = None

        if state_filter in {"active", "ready"}:
            # only get users with active servers
            # an 'active' Spawner has a server record in the database
            # which means Spawner.server != None
            # it may still be in a pending start/stop state.
            # join filters out users with no Spawners
            query = (
                self.db.query(orm.User)
                # join filters out any Users with no Spawners
                .join(orm.Spawner)
                # this implicitly gets Users with *any* active server
                .filter(orm.Spawner.server != None)
            )
            if state_filter == "ready":
                # have to post-process query results because active vs ready
                # can only be distinguished with in-memory Spawner properties
                post_filter = self._user_has_ready_spawner

        elif state_filter == "inactive":
            # only get users with *no* active servers
            # as opposed to users with *any inactive servers*
            # this is the complement to the above query.
            # how expensive is this with lots of servers?
            query = (
                self.db.query(orm.User)
                .outerjoin(orm.Spawner)
                .outerjoin(orm.Server)
                .group_by(orm.User.id)
                .having(func.count(orm.Server.id) == 0)
            )
        elif state_filter:
            raise web.HTTPError(400, "Unrecognized state filter: %r" % state_filter)
        else:
            # no filter, return all users
            query = self.db.query(orm.User)

        data = [
            self.user_model(u, include_servers=True, include_state=True)
            for u in query
            if (post_filter is None or post_filter(u))
        ]
        self.write(json.dumps(data))

    @admin_only
    async def post(self):
        data = self.get_json_body()
        if not data or not isinstance(data, dict) or not data.get('usernames'):
            raise web.HTTPError(400, "Must specify at least one user to create")

        usernames = data.pop('usernames')
        self._check_user_model(data)
        # admin is set for all users
        # to create admin and non-admin users requires at least two API requests
        admin = data.get('admin', False)

        to_create = []
        invalid_names = []
        for name in usernames:
            name = self.authenticator.normalize_username(name)
            if not self.authenticator.validate_username(name):
                invalid_names.append(name)
                continue
            user = self.find_user(name)
            if user is not None:
                self.log.warning("User %s already exists" % name)
            else:
                to_create.append(name)

        if invalid_names:
            if len(invalid_names) == 1:
                msg = "Invalid username: %s" % invalid_names[0]
            else:
                msg = "Invalid usernames: %s" % ', '.join(invalid_names)
            raise web.HTTPError(400, msg)

        if not to_create:
            raise web.HTTPError(409, "All %i users already exist" % len(usernames))

        created = []
        for name in to_create:
            user = self.user_from_username(name)
            if admin:
                user.admin = True
                self.db.commit()
            try:
                await maybe_future(self.authenticator.add_user(user))
            except Exception as e:
                self.log.error("Failed to create user: %s" % name, exc_info=True)
                self.users.delete(user)
                raise web.HTTPError(
                    400, "Failed to create user %s: %s" % (name, str(e))
                )
            else:
                created.append(user)

        self.write(json.dumps([self.user_model(u) for u in created]))
        self.set_status(201)


def admin_or_self(method):
    """Decorator for restricting access to either the target user or admin"""

    def m(self, name, *args, **kwargs):
        current = self.current_user
        if current is None:
            raise web.HTTPError(403)
        if not (current.name == name or current.admin):
            raise web.HTTPError(403)

        # raise 404 if not found
        if not self.find_user(name):
            raise web.HTTPError(404)
        return method(self, name, *args, **kwargs)

    return m


class UserAPIHandler(APIHandler):
    @admin_or_self
    async def get(self, name):
        user = self.find_user(name)
        model = self.user_model(
            user, include_servers=True, include_state=self.current_user.admin
        )
        # auth state will only be shown if the requester is an admin
        # this means users can't see their own auth state unless they
        # are admins, Hub admins often are also marked as admins so they
        # will see their auth state but normal users won't
        requester = self.current_user
        if requester.admin:
            model['auth_state'] = await user.get_auth_state()
        self.write(json.dumps(model))

    @admin_only
    async def post(self, name):
        data = self.get_json_body()
        user = self.find_user(name)
        if user is not None:
            raise web.HTTPError(409, "User %s already exists" % name)

        user = self.user_from_username(name)
        if data:
            self._check_user_model(data)
            if 'admin' in data:
                user.admin = data['admin']
                self.db.commit()

        try:
            await maybe_future(self.authenticator.add_user(user))
        except Exception:
            self.log.error("Failed to create user: %s" % name, exc_info=True)
            # remove from registry
            self.users.delete(user)
            raise web.HTTPError(400, "Failed to create user: %s" % name)

        self.write(json.dumps(self.user_model(user)))
        self.set_status(201)

    @admin_only
    async def delete(self, name):
        user = self.find_user(name)
        if user is None:
            raise web.HTTPError(404)
        if user.name == self.current_user.name:
            raise web.HTTPError(400, "Cannot delete yourself!")
        if user.spawner._stop_pending:
            raise web.HTTPError(
                400, "%s's server is in the process of stopping, please wait." % name
            )
        if user.running:
            await self.stop_single_user(user)
            if user.spawner._stop_pending:
                raise web.HTTPError(
                    400,
                    "%s's server is in the process of stopping, please wait." % name,
                )

        await maybe_future(self.authenticator.delete_user(user))

        # allow the spawner to cleanup any persistent resources associated with the user
        try:
            await user.spawner.delete_forever()
        except Exception as e:
            self.log.error("Error cleaning up persistent resources: %s" % e)

        # remove from registry
        self.users.delete(user)

        self.set_status(204)

    @admin_only
    async def patch(self, name):
        user = self.find_user(name)
        if user is None:
            raise web.HTTPError(404)
        data = self.get_json_body()
        self._check_user_model(data)
        if 'name' in data and data['name'] != name:
            # check if the new name is already taken inside db
            if self.find_user(data['name']):
                raise web.HTTPError(
                    400,
                    "User %s already exists, username must be unique" % data['name'],
                )
        for key, value in data.items():
            if key == 'auth_state':
                await user.save_auth_state(value)
            else:
                setattr(user, key, value)
        self.db.commit()
        user_ = self.user_model(user)
        user_['auth_state'] = await user.get_auth_state()
        self.write(json.dumps(user_))


class UserTokenListAPIHandler(APIHandler):
    """API endpoint for listing/creating tokens"""

    @admin_or_self
    def get(self, name):
        """Get tokens for a given user"""
        user = self.find_user(name)
        if not user:
            raise web.HTTPError(404, "No such user: %s" % name)

        now = datetime.utcnow()

        api_tokens = []

        def sort_key(token):
            return token.last_activity or token.created

        for token in sorted(user.api_tokens, key=sort_key):
            if token.expires_at and token.expires_at < now:
                # exclude expired tokens
                self.db.delete(token)
                self.db.commit()
                continue
            api_tokens.append(self.token_model(token))

        oauth_tokens = []
        # OAuth tokens use integer timestamps
        now_timestamp = now.timestamp()
        for token in sorted(user.oauth_tokens, key=sort_key):
            if token.expires_at and token.expires_at < now_timestamp:
                # exclude expired tokens
                self.db.delete(token)
                self.db.commit()
                continue
            oauth_tokens.append(self.token_model(token))
        self.write(json.dumps({'api_tokens': api_tokens, 'oauth_tokens': oauth_tokens}))

    async def post(self, name):
        body = self.get_json_body() or {}
        if not isinstance(body, dict):
            raise web.HTTPError(400, "Body must be a JSON dict or empty")

        requester = self.current_user
        if requester is None:
            # defer to Authenticator for identifying the user
            # can be username+password or an upstream auth token
            try:
                name = await self.authenticate(body.get('auth'))
                if isinstance(name, dict):
                    # not a simple string so it has to be a dict
                    name = name.get('name')
            except web.HTTPError as e:
                # turn any authentication error into 403
                raise web.HTTPError(403)
            except Exception as e:
                # suppress and log error here in case Authenticator
                # isn't prepared to handle auth via this data
                self.log.error(
                    "Error authenticating request for %s: %s", self.request.uri, e
                )
                raise web.HTTPError(403)
            requester = self.find_user(name)
        if requester is None:
            # couldn't identify requester
            raise web.HTTPError(403)
        user = self.find_user(name)
        if requester is not user and not requester.admin:
            raise web.HTTPError(403, "Only admins can request tokens for other users")
        if not user:
            raise web.HTTPError(404, "No such user: %s" % name)
        if requester is not user:
            kind = 'user' if isinstance(requester, User) else 'service'

        note = body.get('note')
        if not note:
            note = "Requested via api"
            if requester is not user:
                note += " by %s %s" % (kind, requester.name)

        api_token = user.new_api_token(
            note=note, expires_in=body.get('expires_in', None)
        )
        if requester is not user:
            self.log.info(
                "%s %s requested API token for %s",
                kind.title(),
                requester.name,
                user.name,
            )
        else:
            user_kind = 'user' if isinstance(user, User) else 'service'
            self.log.info("%s %s requested new API token", user_kind.title(), user.name)
        # retrieve the model
        token_model = self.token_model(orm.APIToken.find(self.db, api_token))
        token_model['token'] = api_token
        self.write(json.dumps(token_model))


class UserTokenAPIHandler(APIHandler):
    """API endpoint for retrieving/deleting individual tokens"""

    def find_token_by_id(self, user, token_id):
        """Find a token object by token-id key

        Raises 404 if not found for any reason
        (e.g. wrong owner, invalid key format, etc.)
        """
        not_found = "No such token %s for user %s" % (token_id, user.name)
        prefix, id = token_id[0], token_id[1:]
        if prefix == 'a':
            Token = orm.APIToken
        elif prefix == 'o':
            Token = orm.OAuthAccessToken
        else:
            raise web.HTTPError(404, not_found)
        try:
            id = int(id)
        except ValueError:
            raise web.HTTPError(404, not_found)

        orm_token = self.db.query(Token).filter(Token.id == id).first()
        if orm_token is None or orm_token.user is not user.orm_user:
            raise web.HTTPError(404, "Token not found %s", orm_token)
        return orm_token

    @admin_or_self
    def get(self, name, token_id):
        """"""
        user = self.find_user(name)
        if not user:
            raise web.HTTPError(404, "No such user: %s" % name)
        token = self.find_token_by_id(user, token_id)
        self.write(json.dumps(self.token_model(token)))

    @admin_or_self
    def delete(self, name, token_id):
        """Delete a token"""
        user = self.find_user(name)
        if not user:
            raise web.HTTPError(404, "No such user: %s" % name)
        token = self.find_token_by_id(user, token_id)
        # deleting an oauth token deletes *all* oauth tokens for that client
        if isinstance(token, orm.OAuthAccessToken):
            client_id = token.client_id
            tokens = [
                token for token in user.oauth_tokens if token.client_id == client_id
            ]
        else:
            tokens = [token]
        for token in tokens:
            self.db.delete(token)
        self.db.commit()
        self.set_header('Content-Type', 'text/plain')
        self.set_status(204)


class UserServerAPIHandler(APIHandler):
    """Start and stop single-user servers"""

    @admin_or_self
    async def post(self, name, server_name=''):
        user = self.find_user(name)
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
                            name, self.named_server_limit_per_user
                        ),
                    )
        spawner = user.spawners[server_name]
        pending = spawner.pending
        if pending == 'spawn':
            self.set_header('Content-Type', 'text/plain')
            self.set_status(202)
            return
        elif pending:
            raise web.HTTPError(400, "%s is pending %s" % (spawner._log_name, pending))

        if spawner.ready:
            # include notify, so that a server that died is noticed immediately
            # set _spawn_pending flag to prevent races while we wait
            spawner._spawn_pending = True
            try:
                state = await spawner.poll_and_notify()
            finally:
                spawner._spawn_pending = False
            if state is None:
                raise web.HTTPError(400, "%s is already running" % spawner._log_name)

        options = self.get_json_body()
        await self.spawn_single_user(user, server_name, options=options)
        status = 202 if spawner.pending == 'spawn' else 201
        self.set_header('Content-Type', 'text/plain')
        self.set_status(status)

    @admin_or_self
    async def delete(self, name, server_name=''):
        user = self.find_user(name)
        options = self.get_json_body()
        remove = (options or {}).get('remove', False)

        def _remove_spawner(f=None):
            if f and f.exception():
                return
            self.log.info("Deleting spawner %s", spawner._log_name)
            self.db.delete(spawner.orm_spawner)
            user.spawners.pop(server_name, None)
            self.db.commit()

        if server_name:
            if not self.allow_named_servers:
                raise web.HTTPError(400, "Named servers are not enabled.")
            if server_name not in user.orm_spawners:
                raise web.HTTPError(
                    404, "%s has no server named '%s'" % (name, server_name)
                )
        elif remove:
            raise web.HTTPError(400, "Cannot delete the default server")

        spawner = user.spawners[server_name]
        if spawner.pending == 'stop':
            self.log.debug("%s already stopping", spawner._log_name)
            self.set_header('Content-Type', 'text/plain')
            self.set_status(202)
            if remove:
                spawner._stop_future.add_done_callback(_remove_spawner)
            return

        if spawner.pending:
            raise web.HTTPError(
                400,
                "%s is pending %s, please wait" % (spawner._log_name, spawner.pending),
            )

        stop_future = None
        if spawner.ready:
            # include notify, so that a server that died is noticed immediately
            status = await spawner.poll_and_notify()
            if status is None:
                stop_future = await self.stop_single_user(user, server_name)

        if remove:
            if stop_future:
                stop_future.add_done_callback(_remove_spawner)
            else:
                _remove_spawner()

        status = 202 if spawner._stop_pending else 204
        self.set_header('Content-Type', 'text/plain')
        self.set_status(status)


class UserAdminAccessAPIHandler(APIHandler):
    """Grant admins access to single-user servers

    This handler sets the necessary cookie for an admin to login to a single-user server.
    """

    @admin_only
    def post(self, name):
        self.log.warning(
            "Deprecated in JupyterHub 0.8."
            " Admin access API is not needed now that we use OAuth."
        )
        current = self.current_user
        self.log.warning(
            "Admin user %s has requested access to %s's server", current.name, name
        )
        if not self.settings.get('admin_access', False):
            raise web.HTTPError(403, "admin access to user servers disabled")
        user = self.find_user(name)
        if user is None:
            raise web.HTTPError(404)


class SpawnProgressAPIHandler(APIHandler):
    """EventStream handler for pending spawns"""

    keepalive_interval = 8

    def get_content_type(self):
        return 'text/event-stream'

    async def send_event(self, event):
        try:
            self.write('data: {}\n\n'.format(json.dumps(event)))
            await self.flush()
        except StreamClosedError:
            self.log.warning("Stream closed while handling %s", self.request.uri)
            # raise Finish to halt the handler
            raise web.Finish()

    def initialize(self):
        super().initialize()
        self._finish_future = asyncio.Future()

    def on_finish(self):
        self._finish_future.set_result(None)

    async def keepalive(self):
        """Write empty lines periodically

        to avoid being closed by intermediate proxies
        when there's a large gap between events.
        """
        while not self._finish_future.done():
            try:
                self.write("\n\n")
                await self.flush()
            except (StreamClosedError, RuntimeError):
                return

            await asyncio.wait([self._finish_future], timeout=self.keepalive_interval)

    @admin_or_self
    async def get(self, username, server_name=''):
        self.set_header('Cache-Control', 'no-cache')
        if server_name is None:
            server_name = ''
        user = self.find_user(username)
        if user is None:
            # no such user
            raise web.HTTPError(404)
        if server_name not in user.spawners:
            # user has no such server
            raise web.HTTPError(404)
        spawner = user.spawners[server_name]

        # start sending keepalive to avoid proxies closing the connection
        asyncio.ensure_future(self.keepalive())
        # cases:
        # - spawner already started and ready
        # - spawner not running at all
        # - spawner failed
        # - spawner pending start (what we expect)
        url = url_path_join(user.url, server_name, '/')
        ready_event = {
            'progress': 100,
            'ready': True,
            'message': "Server ready at {}".format(url),
            'html_message': 'Server ready at <a href="{0}">{0}</a>'.format(url),
            'url': url,
        }
        failed_event = {'progress': 100, 'failed': True, 'message': "Spawn failed"}

        if spawner.ready:
            # spawner already ready. Trigger progress-completion immediately
            self.log.info("Server %s is already started", spawner._log_name)
            await self.send_event(ready_event)
            return

        spawn_future = spawner._spawn_future

        if not spawner._spawn_pending:
            # not pending, no progress to fetch
            # check if spawner has just failed
            f = spawn_future
            if f and f.done() and f.exception():
                failed_event['message'] = "Spawn failed: %s" % f.exception()
                await self.send_event(failed_event)
                return
            else:
                raise web.HTTPError(400, "%s is not starting...", spawner._log_name)

        # retrieve progress events from the Spawner
        async with aclosing(
            iterate_until(spawn_future, spawner._generate_progress())
        ) as events:
            try:
                async for event in events:
                    # don't allow events to sneakily set the 'ready' flag
                    if 'ready' in event:
                        event.pop('ready', None)
                    await self.send_event(event)
            except asyncio.CancelledError:
                pass

        # progress finished, wait for spawn to actually resolve,
        # in case progress finished early
        # (ignore errors, which will be logged elsewhere)
        await asyncio.wait([spawn_future])

        # progress and spawn finished, check if spawn succeeded
        if spawner.ready:
            # spawner is ready, signal completion and redirect
            self.log.info("Server %s is ready", spawner._log_name)
            await self.send_event(ready_event)
        else:
            # what happened? Maybe spawn failed?
            f = spawn_future
            if f and f.done() and f.exception():
                failed_event['message'] = "Spawn failed: %s" % f.exception()
            else:
                self.log.warning(
                    "Server %s didn't start for unknown reason", spawner._log_name
                )
            await self.send_event(failed_event)


def _parse_timestamp(timestamp):
    """Parse and return a utc timestamp

    - raise HTTPError(400) on parse error
    - handle and strip tz info for internal consistency
      (we use naive utc timestamps everywhere)
    """
    try:
        dt = parse_date(timestamp)
    except Exception:
        raise web.HTTPError(400, "Not a valid timestamp: %r", timestamp)
    if dt.tzinfo:
        # strip timezone info to naive UTC datetime
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    now = datetime.utcnow()
    if (dt - now) > timedelta(minutes=59):
        raise web.HTTPError(
            400,
            "Rejecting activity from more than an hour in the future: {}".format(
                isoformat(dt)
            ),
        )
    return dt


class ActivityAPIHandler(APIHandler):
    def _validate_servers(self, user, servers):
        """Validate servers dict argument

        - types are correct
        - each server exists
        - last_activity fields are parsed into datetime objects
        """
        msg = "servers must be a dict of the form {server_name: {last_activity: timestamp}}"
        if not isinstance(servers, dict):
            raise web.HTTPError(400, msg)

        spawners = user.orm_spawners
        for server_name, server_info in servers.items():
            if server_name not in spawners:
                raise web.HTTPError(
                    400,
                    "No such server '{}' for user {}".format(server_name, user.name),
                )
            # check that each per-server field is a dict
            if not isinstance(server_info, dict):
                raise web.HTTPError(400, msg)
            # check that last_activity is defined for each per-server dict
            if 'last_activity' not in server_info:
                raise web.HTTPError(400, msg)
            # parse last_activity timestamps
            # _parse_timestamp above is responsible for raising errors
            server_info['last_activity'] = _parse_timestamp(
                server_info['last_activity']
            )
        return servers

    @admin_or_self
    def post(self, username):
        user = self.find_user(username)
        if user is None:
            # no such user
            raise web.HTTPError(404, "No such user: %r", username)

        body = self.get_json_body()
        if not isinstance(body, dict):
            raise web.HTTPError(400, "body must be a json dict")

        last_activity_timestamp = body.get('last_activity')
        servers = body.get('servers')
        if not last_activity_timestamp and not servers:
            raise web.HTTPError(
                400, "body must contain at least one of `last_activity` or `servers`"
            )

        if servers:
            # validate server args
            servers = self._validate_servers(user, servers)
            # at this point we know that the servers dict
            # is valid and contains only servers that exist
            # and last_activity is defined and a valid datetime object

        # update user.last_activity if specified
        if last_activity_timestamp:
            last_activity = _parse_timestamp(last_activity_timestamp)
            if (not user.last_activity) or last_activity > user.last_activity:
                self.log.debug(
                    "Activity for user %s: %s", user.name, isoformat(last_activity)
                )
                user.last_activity = last_activity
            else:
                self.log.debug(
                    "Not updating activity for %s: %s < %s",
                    user,
                    isoformat(last_activity),
                    isoformat(user.last_activity),
                )

        if servers:
            for server_name, server_info in servers.items():
                last_activity = server_info['last_activity']
                spawner = user.orm_spawners[server_name]

                if (not spawner.last_activity) or last_activity > spawner.last_activity:
                    self.log.debug(
                        "Activity on server %s/%s: %s",
                        user.name,
                        server_name,
                        isoformat(last_activity),
                    )
                    spawner.last_activity = last_activity
                else:
                    self.log.debug(
                        "Not updating server activity on %s/%s: %s < %s",
                        user.name,
                        server_name,
                        isoformat(last_activity),
                        isoformat(user.last_activity),
                    )

        self.db.commit()


default_handlers = [
    (r"/api/user", SelfAPIHandler),
    (r"/api/users", UserListAPIHandler),
    (r"/api/users/([^/]+)", UserAPIHandler),
    (r"/api/users/([^/]+)/server", UserServerAPIHandler),
    (r"/api/users/([^/]+)/server/progress", SpawnProgressAPIHandler),
    (r"/api/users/([^/]+)/tokens", UserTokenListAPIHandler),
    (r"/api/users/([^/]+)/tokens/([^/]*)", UserTokenAPIHandler),
    (r"/api/users/([^/]+)/servers/([^/]*)", UserServerAPIHandler),
    (r"/api/users/([^/]+)/servers/([^/]*)/progress", SpawnProgressAPIHandler),
    (r"/api/users/([^/]+)/activity", ActivityAPIHandler),
    (r"/api/users/([^/]+)/admin-access", UserAdminAccessAPIHandler),
]
