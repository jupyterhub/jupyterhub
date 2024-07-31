"""User handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import inspect
import json
import sys
from datetime import timedelta, timezone

if sys.version_info >= (3, 10):
    from contextlib import aclosing
else:
    from async_generator import aclosing

from dateutil.parser import parse as parse_date
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, raiseload, selectinload  # noqa
from tornado import web
from tornado.iostream import StreamClosedError

from .. import orm, scopes
from ..roles import assign_default_roles
from ..scopes import needs_scope
from ..user import User
from ..utils import (
    isoformat,
    iterate_until,
    maybe_future,
    url_escape_path,
    url_path_join,
    utcnow,
)
from .base import APIHandler


class SelfAPIHandler(APIHandler):
    """Return the authenticated user's model

    Based on the authentication info. Acts as a 'whoami' for auth tokens.
    """

    async def get(self):
        user = self.current_user
        if user is None:
            raise web.HTTPError(403)

        _added_scopes = set()
        if isinstance(user, orm.Service):
            # ensure we have the minimal 'identify' scopes for the token owner
            identify_scopes = scopes.identify_scopes(user)
            get_model = self.service_model
        else:
            identify_scopes = scopes.identify_scopes(user.orm_user)
            get_model = self.user_model

        # ensure we have permission to identify ourselves
        # all tokens can do this on this endpoint
        for scope in identify_scopes:
            if scope not in self.expanded_scopes:
                _added_scopes.add(scope)
                self.expanded_scopes |= {scope}
        if _added_scopes:
            # re-parse with new scopes
            self.parsed_scopes = scopes.parse_scopes(self.expanded_scopes)

        model = get_model(user)

        # add session_id associated with token
        # added in 2.0
        # token_id added in 5.0
        token = self.get_token()
        if token:
            model["token_id"] = token.api_id
            model["session_id"] = token.session_id
        else:
            model["token_id"] = None
            model["session_id"] = None

        # add scopes to identify model,
        # but not the scopes we added to ensure we could read our own model
        model["scopes"] = sorted(self.expanded_scopes.difference(_added_scopes))
        self.write(json.dumps(model))


class UserListAPIHandler(APIHandler):
    def _user_has_ready_spawner(self, orm_user):
        """Return True if a user has *any* ready spawners

        Used for filtering from active -> ready
        """
        user = self.users[orm_user]
        return any(spawner.ready for spawner in user.spawners.values())

    @needs_scope('list:users')
    def get(self):
        state_filter = self.get_argument("state", None)
        name_filter = self.get_argument("name_filter", None)
        sort = sort_by_param = self.get_argument("sort", "id")
        sort_direction = "asc"
        if sort[:1] == '-':
            sort_direction = "desc"
            sort = sort[1:]

        offset, limit = self.get_api_pagination()

        if sort in {"id", "name", "last_activity"}:
            sort_column = getattr(orm.User, sort)
        else:
            raise web.HTTPError(
                400,
                f"sort must be 'id', 'name', or 'last_activity', not '{sort_by_param}'",
            )

        # NULL is sorted inconsistently, so make it explicit
        if sort_direction == "asc":
            sort_order = (sort_column.is_not(None), sort_column.asc())
        elif sort_direction == "desc":
            sort_order = (sort_column.is_(None), sort_column.desc())
        else:
            # this can't happen, users don't specify direction
            raise ValueError(
                f"sort_direction must be 'asc' or 'desc', got '{sort_direction}'"
            )

        # post_filter
        post_filter = None

        # starting query
        query = self.db.query(orm.User)

        if state_filter in {"active", "ready"}:
            # only get users with active servers
            # an 'active' Spawner has a server record in the database
            # which means Spawner.server != None
            # it may still be in a pending start/stop state.
            # join filters out users with no Spawners
            query = (
                query
                # join filters out any Users with no Spawners
                .join(orm.Spawner, orm.User._orm_spawners)
                # this implicitly gets Users with *any* active server
                .filter(orm.Spawner.server != None)
                # group-by ensures the count is correct
                .group_by(orm.User.id)
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
                query.outerjoin(orm.Spawner, orm.User._orm_spawners)
                .outerjoin(orm.Server, orm.Spawner.server)
                .group_by(orm.User.id)
                .having(func.count(orm.Server.id) == 0)
            )
        elif state_filter:
            raise web.HTTPError(400, f"Unrecognized state filter: {state_filter!r}")

        # apply eager load options
        query = query.options(
            selectinload(orm.User.roles),
            selectinload(orm.User.groups),
            joinedload(orm.User._orm_spawners).joinedload(orm.Spawner.user),
            # raiseload here helps us make sure we've loaded everything in one query
            # but since we share a single db session, we can't do this for real
            # but it's useful in testing
            # raiseload("*"),
        )

        sub_scope = self.parsed_scopes['list:users']
        if sub_scope != scopes.Scope.ALL:
            if not set(sub_scope).issubset({'group', 'user'}):
                # don't expand invalid !server=x filter to all users!
                self.log.warning(
                    f"Invalid filter on list:user for {self.current_user}: {sub_scope}"
                )
                raise web.HTTPError(403)
            filters = []
            if 'user' in sub_scope:
                filters.append(orm.User.name.in_(sub_scope['user']))
            if 'group' in sub_scope:
                filters.append(
                    orm.User.groups.any(
                        orm.Group.name.in_(sub_scope['group']),
                    )
                )

            if len(filters) == 1:
                query = query.filter(filters[0])
            else:
                query = query.filter(or_(*filters))

        if name_filter:
            query = query.filter(orm.User.name.ilike(f'%{name_filter}%'))

        full_query = query
        query = query.order_by(*sort_order).offset(offset).limit(limit)

        user_list = []
        for u in query:
            if post_filter is None or post_filter(u):
                user_model = self.user_model(u)
                if user_model:
                    user_list.append(user_model)

        total_count = full_query.count()
        if self.accepts_pagination:
            data = self.paginated_model(user_list, offset, limit, total_count)
        else:
            query_count = query.count()
            if offset == 0 and total_count > query_count:
                self.log.warning(
                    f"Truncated user list in request that does not expect pagination. Processing {query_count} of {total_count} total users."
                )
            data = user_list

        self.write(json.dumps(data))
        # if testing with raiseload above, need expire_all to avoid affecting other operations
        # self.db.expire_all()

    @needs_scope('admin:users')
    async def post(self):
        data = self.get_json_body()
        if not data or not isinstance(data, dict) or not data.get('usernames'):
            raise web.HTTPError(400, "Must specify at least one user to create")

        usernames = data.pop('usernames')
        self._check_user_model(data)
        # admin is set for all users
        # to create admin and non-admin users requires at least two API requests
        admin = data.get('admin', False)
        if admin and not self.current_user.admin:
            raise web.HTTPError(403, "Only admins can grant admin permissions")

        to_create = []
        invalid_names = []
        for name in usernames:
            name = self.authenticator.normalize_username(name)
            if not self.authenticator.validate_username(name):
                invalid_names.append(name)
                continue
            user = self.find_user(name)
            if user is not None:
                self.log.warning(f"User {name} already exists")
            else:
                to_create.append(name)

        if invalid_names:
            if len(invalid_names) == 1:
                msg = f"Invalid username: {invalid_names[0]}"
            else:
                msg = "Invalid usernames: {}".format(', '.join(invalid_names))
            raise web.HTTPError(400, msg)

        if not to_create:
            raise web.HTTPError(409, "All %i users already exist" % len(usernames))

        created = []
        for name in to_create:
            user = self.user_from_username(name)
            if admin:
                user.admin = True
            assign_default_roles(self.db, entity=user)
            self.db.commit()
            try:
                await maybe_future(self.authenticator.add_user(user))
            except Exception as e:
                self.log.error(f"Failed to create user: {name}", exc_info=True)
                self.users.delete(user)
                raise web.HTTPError(400, f"Failed to create user {name}: {e}")
            else:
                created.append(user)

        self.write(json.dumps([self.user_model(u) for u in created]))
        self.set_status(201)


class UserAPIHandler(APIHandler):
    @needs_scope(
        'read:users',
        'read:users:name',
        'read:servers',
        'read:users:groups',
        'read:users:activity',
        'read:roles:users',
    )
    async def get(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404)
        model = self.user_model(user)
        # auth state will only be shown if the requester is an admin
        # this means users can't see their own auth state unless they
        # are admins, Hub admins often are also marked as admins so they
        # will see their auth state but normal users won't
        if 'auth_state' in model:
            model['auth_state'] = await user.get_auth_state()
        self.write(json.dumps(model))

    @needs_scope('admin:users')
    async def post(self, user_name):
        data = self.get_json_body()
        user = self.find_user(user_name)
        if user is not None:
            raise web.HTTPError(409, f"User {user_name} already exists")

        if data:
            self._check_user_model(data)
            if data.get('admin', False) and not self.current_user.admin:
                raise web.HTTPError(403, "Only admins can grant admin permissions")

        # create the user
        user = self.user_from_username(user_name)
        if data and data.get('admin', False):
            user.admin = data['admin']
            assign_default_roles(self.db, entity=user)
        self.db.commit()

        try:
            await maybe_future(self.authenticator.add_user(user))
        except Exception:
            self.log.error(f"Failed to create user: {user_name}", exc_info=True)
            # remove from registry
            self.users.delete(user)
            raise web.HTTPError(400, f"Failed to create user: {user_name}")

        self.write(json.dumps(self.user_model(user)))
        self.set_status(201)

    @needs_scope('delete:users')
    async def delete(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404)
        if user.name == self.current_user.name:
            raise web.HTTPError(400, "Cannot delete yourself!")
        if user.spawner._stop_pending:
            raise web.HTTPError(
                400,
                f"{user_name}'s server is in the process of stopping, please wait.",
            )
        if user.running:
            await self.stop_single_user(user)
            if user.spawner._stop_pending:
                raise web.HTTPError(
                    400,
                    f"{user_name}'s server is in the process of stopping, please wait.",
                )

        await maybe_future(self.authenticator.delete_user(user))

        await user.delete_spawners()

        # remove from registry
        self.users.delete(user)

        self.set_status(204)

    @needs_scope('admin:users')
    async def patch(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404)
        data = self.get_json_body()
        self._check_user_model(data)
        if 'name' in data and data['name'] != user_name:
            # check if the new name is already taken inside db
            if self.find_user(data['name']):
                raise web.HTTPError(
                    400,
                    "User {} already exists, username must be unique".format(
                        data['name']
                    ),
                )

        if not self.current_user.admin:
            if user.admin:
                raise web.HTTPError(403, "Only admins can modify other admins")
            if 'admin' in data and data['admin']:
                raise web.HTTPError(403, "Only admins can grant admin permissions")
        for key, value in data.items():
            value_s = "..." if key == "auth_state" else repr(value)
            self.log.info(
                f"{self.current_user.name} setting {key}={value_s} for {user.name}"
            )
            if key == 'auth_state':
                await user.save_auth_state(value)
            else:
                setattr(user, key, value)
                if key == 'admin':
                    assign_default_roles(self.db, entity=user)
        self.db.commit()
        user_ = self.user_model(user)
        user_['auth_state'] = await user.get_auth_state()
        self.write(json.dumps(user_))


class UserTokenListAPIHandler(APIHandler):
    """API endpoint for listing/creating tokens"""

    # defer check_xsrf_cookie so we can accept auth
    # in the `auth` request field, which shouldn't require xsrf cookies
    _skip_post_check_xsrf = True

    def check_xsrf_cookie(self):
        if self.request.method == 'POST' and self._skip_post_check_xsrf:
            return
        return super().check_xsrf_cookie()

    @needs_scope('read:tokens')
    def get(self, user_name):
        """Get tokens for a given user"""
        user = self.find_user(user_name)
        if not user:
            raise web.HTTPError(404, f"No such user: {user_name}")

        now = utcnow(with_tz=False)
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

        self.write(json.dumps({'api_tokens': api_tokens}))

    async def post(self, user_name):
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
                # don't check xsrf if we've authenticated via the request body
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
            if name is None:
                raise web.HTTPError(403)
            requester = self.find_user(name)
        else:
            # perform delayed xsrf check
            # if we aren't authenticating via the request body
            self._skip_post_check_xsrf = False
            self.check_xsrf_cookie()
        if requester is None:
            # couldn't identify requester
            raise web.HTTPError(403)
        self._jupyterhub_user = requester
        self._resolve_roles_and_scopes()
        user = self.find_user(user_name)
        kind = 'user' if isinstance(requester, User) else 'service'
        scope_filter = self.get_scope_filter('tokens')
        if user is None or not scope_filter(user, kind):
            raise web.HTTPError(
                403,
                f"{kind.title()} {user_name} not found or no permissions to generate tokens",
            )

        note = body.get('note')
        if not note:
            note = "Requested via api"
            if requester is not user:
                note += f" by {kind} {requester.name}"

        token_roles = body.get("roles")
        token_scopes = body.get("scopes")

        # check type of permissions
        for key in ("roles", "scopes"):
            value = body.get(key)
            if value is None:
                continue
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise web.HTTPError(
                    400, f"token {key} must be null or a list of strings, not {value!r}"
                )

        expires_in = body.get('expires_in', None)
        if not (expires_in is None or isinstance(expires_in, int)):
            raise web.HTTPError(
                400,
                f"token expires_in must be null or integer, not {expires_in!r}",
            )
        expires_in_max = self.settings["token_expires_in_max_seconds"]
        if expires_in_max:
            # validate expires_in against limit
            if expires_in is None:
                # expiration unspecified, use max value
                # (default before max limit was introduced was 'never', this is closest equivalent)
                expires_in = expires_in_max
            elif expires_in > expires_in_max:
                raise web.HTTPError(
                    400,
                    f"token expires_in: {expires_in} must not exceed {expires_in_max}",
                )

        try:
            api_token = user.new_api_token(
                note=note,
                expires_in=expires_in,
                roles=token_roles,
                scopes=token_scopes,
            )
        except (ValueError, KeyError) as e:
            raise web.HTTPError(400, str(e))
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
        orm_token = orm.APIToken.find(self.db, api_token)
        if orm_token is None:
            self.log.error(
                "Failed to find token after creating it: %r. Maybe it expired already?",
                body,
            )
            raise web.HTTPError(500, "Failed to create token")
        token_model = self.token_model(orm_token)
        token_model['token'] = api_token
        self.write(json.dumps(token_model))
        self.set_status(201)


class UserTokenAPIHandler(APIHandler):
    """API endpoint for retrieving/deleting individual tokens"""

    def find_token_by_id(self, user, token_id):
        """Find a token object by token-id key

        Raises 404 if not found for any reason
        (e.g. wrong owner, invalid key format, etc.)
        """
        not_found = f"No such token {token_id} for user {user.name}"
        prefix, id_ = token_id[:1], token_id[1:]
        if prefix != 'a':
            raise web.HTTPError(404, not_found)
        try:
            id_ = int(id_)
        except ValueError:
            raise web.HTTPError(404, not_found)

        orm_token = self.db.query(orm.APIToken).filter_by(id=id_).first()
        if orm_token is None or orm_token.user is not user.orm_user:
            raise web.HTTPError(404, not_found)
        return orm_token

    @needs_scope('read:tokens')
    def get(self, user_name, token_id):
        """"""
        user = self.find_user(user_name)
        if not user:
            raise web.HTTPError(404, f"No such user: {user_name}")
        token = self.find_token_by_id(user, token_id)
        self.write(json.dumps(self.token_model(token)))

    @needs_scope('tokens')
    def delete(self, user_name, token_id):
        """Delete a token"""
        user = self.find_user(user_name)
        if not user:
            raise web.HTTPError(404, f"No such user: {user_name}")
        token = self.find_token_by_id(user, token_id)
        # deleting an oauth token deletes *all* oauth tokens for that client
        client_id = token.client_id
        if token.client_id != "jupyterhub":
            tokens = [
                token for token in user.api_tokens if token.client_id == client_id
            ]
            self.log.info(
                f"Deleting {len(tokens)} tokens for {user_name} issued by {token.client_id}"
            )
        else:
            self.log.info(f"Deleting token {token_id} for {user_name}")
            tokens = [token]
        for token in tokens:
            self.db.delete(token)
        self.db.commit()
        self.set_header('Content-Type', 'text/plain')
        self.set_status(204)


class UserServerAPIHandler(APIHandler):
    """Start and stop single-user servers"""

    @needs_scope('servers')
    async def post(self, user_name, server_name=''):
        user = self.find_user(user_name)
        if user is None:
            # this can be reached if a token has `servers`
            # permission on *all* users
            raise web.HTTPError(404)

        if server_name:
            if not self.allow_named_servers:
                raise web.HTTPError(400, "Named servers are not enabled.")

            named_server_limit_per_user = (
                await self.get_current_user_named_server_limit()
            )

            if named_server_limit_per_user > 0 and server_name not in user.orm_spawners:
                named_spawners = list(user.all_spawners(include_default=False))
                if named_server_limit_per_user <= len(named_spawners):
                    raise web.HTTPError(
                        400,
                        f"User {user_name} already has the maximum of {named_server_limit_per_user} named servers."
                        "  One must be deleted before a new server can be created",
                    )
        spawner = user.get_spawner(server_name, replace_failed=True)
        pending = spawner.pending
        if pending == 'spawn':
            self.set_header('Content-Type', 'text/plain')
            self.set_status(202)
            return
        elif pending:
            raise web.HTTPError(400, f"{spawner._log_name} is pending {pending}")

        if spawner.ready:
            # include notify, so that a server that died is noticed immediately
            # set _spawn_pending flag to prevent races while we wait
            spawner._spawn_pending = True
            try:
                state = await spawner.poll_and_notify()
            finally:
                spawner._spawn_pending = False
            if state is None:
                raise web.HTTPError(400, f"{spawner._log_name} is already running")

        options = self.get_json_body()
        await self.spawn_single_user(user, server_name, options=options)
        status = 202 if spawner.pending == 'spawn' else 201
        self.set_header('Content-Type', 'text/plain')
        self.set_status(status)

    @needs_scope('delete:servers')
    async def delete(self, user_name, server_name=''):
        user = self.find_user(user_name)
        options = self.get_json_body()
        remove = (options or {}).get('remove', False)

        async def _remove_spawner(f=None):
            """Remove the spawner object

            only called after it stops successfully
            """
            if f:
                # await f, stop on error,
                # leaving resources in the db in case of failure to stop
                await f
            self.log.info("Deleting spawner %s", spawner._log_name)
            await maybe_future(user._delete_spawner(spawner))

            self.db.delete(spawner.orm_spawner)
            user.spawners.pop(server_name, None)
            self.db.commit()

        if server_name:
            if not self.allow_named_servers:
                raise web.HTTPError(400, "Named servers are not enabled.")
            if server_name not in user.orm_spawners:
                raise web.HTTPError(
                    404, f"{user_name} has no server named '{server_name}'"
                )
        elif remove:
            raise web.HTTPError(400, "Cannot delete the default server")

        spawner = user.spawners[server_name]
        if spawner.pending == 'stop':
            self.log.debug("%s already stopping", spawner._log_name)
            self.set_header('Content-Type', 'text/plain')
            self.set_status(202)
            if remove:
                # schedule remove when stop completes
                asyncio.ensure_future(_remove_spawner(spawner._stop_future))
            return

        stop_future = None
        if spawner.pending:
            # we are interrupting a pending start
            # hopefully nothing gets leftover
            self.log.warning(
                f"Interrupting spawner {spawner._log_name}, pending {spawner.pending}"
            )
            spawn_future = spawner._spawn_future
            if spawn_future:
                spawn_future.cancel()
            # Give cancel a chance to resolve?
            # not sure what we would wait for here,
            await asyncio.sleep(1)
            stop_future = await self.stop_single_user(user, server_name)

        elif spawner.ready:
            # include notify, so that a server that died is noticed immediately
            status = await spawner.poll_and_notify()
            if status is None:
                stop_future = await self.stop_single_user(user, server_name)

        if remove:
            if stop_future:
                # schedule remove when stop completes
                asyncio.ensure_future(_remove_spawner(spawner._stop_future))
            else:
                await _remove_spawner()

        status = 202 if spawner._stop_pending else 204
        self.set_header('Content-Type', 'text/plain')
        self.set_status(status)


class UserAdminAccessAPIHandler(APIHandler):
    """Grant admins access to single-user servers

    This handler sets the necessary cookie for an admin to login to a single-user server.
    """

    @needs_scope('servers')
    def post(self, user_name):
        self.log.warning(
            "Deprecated in JupyterHub 0.8."
            " Admin access API is not needed now that we use OAuth."
        )
        current = self.current_user
        self.log.warning(
            "Admin user %s has requested access to %s's server", current.name, user_name
        )
        if not self.settings.get('admin_access', False):
            raise web.HTTPError(403, "admin access to user servers disabled")
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404)


class SpawnProgressAPIHandler(APIHandler):
    """EventStream handler for pending spawns"""

    keepalive_interval = 8

    def get_content_type(self):
        return 'text/event-stream'

    async def send_event(self, event):
        try:
            self.write(f'data: {json.dumps(event)}\n\n')
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

    @needs_scope('read:servers')
    async def get(self, user_name, server_name=''):
        self.set_header('Cache-Control', 'no-cache')
        if server_name is None:
            server_name = ''
        user = self.find_user(user_name)
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
        failed_event = {'progress': 100, 'failed': True, 'message': "Spawn failed"}

        async def get_ready_event():
            url = url_path_join(user.url, url_escape_path(server_name), '/')
            ready_event = {
                'progress': 100,
                'ready': True,
                'message': f"Server ready at {url}",
                'html_message': f'Server ready at <a href="{url}">{url}</a>',
                'url': url,
            }
            original_ready_event = ready_event.copy()
            if spawner.progress_ready_hook:
                try:
                    ready_event = spawner.progress_ready_hook(spawner, ready_event)
                    if inspect.isawaitable(ready_event):
                        ready_event = await ready_event
                except Exception as e:
                    self.log.exception(f"Error in ready_event hook: {e}")
                    ready_event = original_ready_event
            return ready_event

        if spawner.ready:
            # spawner already ready. Trigger progress-completion immediately
            self.log.info("Server %s is already started", spawner._log_name)
            ready_event = await get_ready_event()
            await self.send_event(ready_event)
            return

        spawn_future = spawner._spawn_future

        if not spawner._spawn_pending:
            # not pending, no progress to fetch
            # check if spawner has just failed
            f = spawn_future
            if f and f.cancelled():
                failed_event['message'] = "Spawn cancelled"
            elif f and f.done() and f.exception():
                exc = f.exception()
                message = getattr(exc, "jupyterhub_message", str(exc))
                failed_event['message'] = f"Spawn failed: {message}"
                html_message = getattr(exc, "jupyterhub_html_message", "")
                if html_message:
                    failed_event['html_message'] = html_message
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
            ready_event = await get_ready_event()
            await self.send_event(ready_event)
        else:
            # what happened? Maybe spawn failed?
            f = spawn_future
            if f and f.cancelled():
                failed_event['message'] = "Spawn cancelled"
            elif f and f.done() and f.exception():
                exc = f.exception()
                message = getattr(exc, "jupyterhub_message", str(exc))
                failed_event['message'] = f"Spawn failed: {message}"
                html_message = getattr(exc, "jupyterhub_html_message", "")
                if html_message:
                    failed_event['html_message'] = html_message
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

    now = utcnow(with_tz=False)
    if (dt - now) > timedelta(minutes=59):
        raise web.HTTPError(
            400,
            f"Rejecting activity from more than an hour in the future: {isoformat(dt)}",
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
                    f"No such server '{server_name}' for user {user.name}",
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

    @needs_scope('users:activity')
    def post(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            # no such user
            raise web.HTTPError(404, "No such user: %r", user_name)

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
