# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import json
import warnings
from collections import defaultdict
from urllib.parse import quote, urlparse, urlunparse

from sqlalchemy import inspect
from tornado import web
from tornado.httputil import urlencode
from tornado.log import app_log

from . import orm, roles, scopes
from ._version import __version__, _check_version
from .crypto import CryptKeeper, EncryptionUnavailable, InvalidToken, decrypt, encrypt
from .metrics import RUNNING_SERVERS, TOTAL_USERS
from .objects import Server
from .spawner import LocalProcessSpawner
from .utils import (
    AnyTimeoutError,
    _strict_dns_safe,
    make_ssl_context,
    maybe_future,
    subdomain_hook_legacy,
    url_escape_path,
    url_path_join,
    utcnow,
)

# detailed messages about the most common failure-to-start errors,
# which manifest timeouts during start
start_timeout_message = """
Common causes of this timeout, and debugging tips:

1. Everything is working, but it took too long.
   To fix: increase `Spawner.start_timeout` configuration
   to a number of seconds that is enough for spawners to finish starting.
2. The server didn't finish starting,
   or it crashed due to a configuration issue.
   Check the single-user server's logs for hints at what needs fixing.
"""

http_timeout_message = """
Common causes of this timeout, and debugging tips:

1. The server didn't finish starting,
   or it crashed due to a configuration issue.
   Check the single-user server's logs for hints at what needs fixing.
2. The server started, but is not accessible at the specified URL.
   This may be a configuration issue specific to your chosen Spawner.
   Check the single-user server logs and resource to make sure the URL
   is correct and accessible from the Hub.
3. (unlikely) Everything is working, but the server took too long to respond.
   To fix: increase `Spawner.http_timeout` configuration
   to a number of seconds that is enough for servers to become responsive.
"""


class UserDict(dict):
    """Like defaultdict, but for users

    Users can be retrieved by:

    - integer database id
    - orm.User object
    - username str

    A User wrapper object is always returned.

    This dict contains at least all active users,
    but not necessarily all users in the database.

    Checking `key in userdict` returns whether
    an item is already in the cache,
    *not* whether it is in the database.

    .. versionchanged:: 1.2
        ``'username' in userdict`` pattern is now supported
    """

    def __init__(self, db_factory, settings):
        self.db_factory = db_factory
        self.settings = settings
        super().__init__()

    @property
    def db(self):
        return self.db_factory()

    def from_orm(self, orm_user):
        return User(orm_user, self.settings)

    def add(self, orm_user):
        """Add a user to the UserDict"""
        if orm_user.id not in self:
            self[orm_user.id] = self.from_orm(orm_user)
        return self[orm_user.id]

    def __contains__(self, key):
        """key in userdict checks presence in the cache

        it does not check if the user is in the database
        """
        if isinstance(key, User | orm.User):
            key = key.id
        elif isinstance(key, str):
            # username lookup, O(N)
            for user in self.values():
                if user.name == key:
                    key = user.id
                    break
        return super().__contains__(key)

    def __getitem__(self, key):
        """UserDict allows retrieval of user by any of:

        - User object
        - orm.User object
        - username (str)
        - orm.User.id int (actual key used in underlying dict)
        """
        if isinstance(key, User):
            key = key.id
        elif isinstance(key, str):
            orm_user = self.db.query(orm.User).filter(orm.User.name == key).first()
            if orm_user is None:
                raise KeyError(f"No such user: {key}")
            else:
                key = orm_user.id
        if isinstance(key, orm.User):
            # users[orm_user] returns User(orm_user)
            orm_user = key
            if orm_user.id not in self:
                user = self[orm_user.id] = User(orm_user, self.settings)
                return user
            user = super().__getitem__(orm_user.id)
            user.db = self.db
            return user
        elif isinstance(key, int):
            id = key
            if id not in self:
                orm_user = self.db.query(orm.User).filter(orm.User.id == id).first()
                if orm_user is None:
                    raise KeyError(f"No such user: {id}")
                user = self.add(orm_user)
            else:
                user = super().__getitem__(id)
            return user
        else:
            raise KeyError(repr(key))

    def get(self, key, default=None):
        """Retrieve a User object if it can be found, else default

        Lookup can be by User object, id, or name

        .. versionchanged:: 1.2
            ``get()`` accesses the database instead of just the cache by integer id,
            so is equivalent to catching KeyErrors on attempted lookup.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def __delitem__(self, key):
        user = self[key]
        for orm_spawner in user.orm_user._orm_spawners:
            if orm_spawner in self.db:
                self.db.expunge(orm_spawner)
        if user.orm_user in self.db:
            self.db.expunge(user.orm_user)
        super().__delitem__(user.id)

    def delete(self, key):
        """Delete a user from the cache and the database"""
        user = self[key]
        user_id = user.id
        self.db.delete(user)
        self.db.commit()
        # delete from dict after commit
        TOTAL_USERS.dec()
        del self[user_id]

    def count_active_users(self):
        """Count the number of user servers that are active/pending/ready

        Returns dict with counts of active/pending/ready servers
        """
        counts = defaultdict(int)
        for user in self.values():
            for spawner in user.spawners.values():
                pending = spawner.pending
                if pending:
                    counts['pending'] += 1
                    counts[pending + '_pending'] += 1
                if spawner.active:
                    counts['active'] += 1
                if spawner.ready:
                    counts['ready'] += 1

        return counts


class _SpawnerDict(dict):
    def __init__(self, spawner_factory):
        self.spawner_factory = spawner_factory

    def __getitem__(self, key):
        if key not in self:
            self[key] = self.spawner_factory(key)
        return super().__getitem__(key)


class User:
    """High-level wrapper around an orm.User object"""

    # declare instance attributes
    db = None
    orm_user = None
    log = app_log
    settings = None
    _auth_refreshed = None

    def __init__(self, orm_user, settings=None, db=None):
        self.db = db or inspect(orm_user).session
        self.settings = settings or {}
        self.orm_user = orm_user

        self.allow_named_servers = self.settings.get('allow_named_servers', False)

        self.base_url = self.prefix = (
            url_path_join(self.settings.get('base_url', '/'), 'user', self.escaped_name)
            + '/'
        )

        self.spawners = _SpawnerDict(self._new_spawner)

        # ensure default spawner exists in the database
        if '' not in self.orm_user.orm_spawners:
            self._new_orm_spawner('')

    @property
    def authenticator(self):
        return self.settings.get('authenticator', None)

    @property
    def spawner_class(self):
        return self.settings.get('spawner_class', LocalProcessSpawner)

    def get_spawner(self, server_name="", replace_failed=False):
        """Get a spawner by name

        replace_failed governs whether a failed spawner should be replaced
        or returned (default: returned).

        .. versionadded:: 2.2
        """
        spawner = self.spawners[server_name]
        if replace_failed and spawner._failed:
            self.log.debug(f"Discarding failed spawner {spawner._log_name}")
            # remove failed spawner, create a new one
            self.spawners.pop(server_name)
            spawner = self.spawners[server_name]
        return spawner

    def sync_groups(self, group_names):
        """Synchronize groups with database"""

        current_groups = {g.name for g in self.orm_user.groups}
        new_groups = set(group_names)
        if current_groups == new_groups:
            # no change, nothing to do
            return

        # log group changes
        added_groups = new_groups.difference(current_groups)
        removed_groups = current_groups.difference(group_names)
        if added_groups:
            self.log.info(f"Adding user {self.name} to group(s): {added_groups}")
        if removed_groups:
            self.log.info(f"Removing user {self.name} from group(s): {removed_groups}")

        if group_names:
            groups = (
                self.db.query(orm.Group).filter(orm.Group.name.in_(new_groups)).all()
            )
            existing_groups = {g.name for g in groups}
            for group_name in added_groups:
                if group_name not in existing_groups:
                    # create groups that don't exist yet
                    self.log.info(
                        f"Creating new group {group_name} for user {self.name}"
                    )
                    group = orm.Group(name=group_name)
                    self.db.add(group)
                    groups.append(group)
            self.orm_user.groups = groups
        else:
            self.orm_user.groups = []
        self.db.commit()

    def sync_roles(self, auth_roles):
        """Synchronize roles with database"""
        auth_roles_by_name = {role['name']: role for role in auth_roles}

        current_user_roles = {r.name for r in self.orm_user.roles}
        new_user_roles = set(auth_roles_by_name.keys())

        granted_roles = new_user_roles.difference(current_user_roles)
        stripped_roles = current_user_roles.difference(new_user_roles)

        if granted_roles:
            self.log.info(f"Granting user {self.name} roles(s): {granted_roles}")
        if stripped_roles:
            self.log.info(f"Stripping user {self.name} roles(s): {stripped_roles}")

        existing_granted_roles = {
            r.name
            for r in self.db.query(orm.Role).filter(orm.Role.name.in_(granted_roles))
        }
        created_roles = existing_granted_roles.difference(granted_roles)

        if created_roles:
            self.log.info(f"Creating new roles {created_roles} in the database")

        for role_name in new_user_roles:
            if role_name in created_roles:
                self.log.info(f"Creating new role {role_name}")
            else:
                self.log.debug(f"Updating existing role {role_name}")

            role = auth_roles_by_name[role_name]
            role['managed_by_auth'] = True

            # creates role, or if it exists, update its `description` and `scopes`
            try:
                orm_role = roles.create_role(
                    self.db, role, commit=False, reset_to_defaults=False
                )
            except (
                roles.RoleValueError,
                roles.InvalidNameError,
                scopes.ScopeNotFound,
            ) as e:
                raise web.HTTPError(409, str(e))

            # Update the groups, services and users for the role
            entity_map = {
                'groups': orm.Group,
                'services': orm.Service,
                'users': orm.User,
            }
            for key, Class in entity_map.items():
                if key in role.keys():
                    entities = []
                    not_found_entities = []
                    for entity_name in role[key]:
                        entity = Class.find(self.db, entity_name)
                        if entity is None:
                            not_found_entities.append(entity_name)
                        else:
                            entities.append(entity)
                    setattr(orm_role, key, entities)
                    if not_found_entities:
                        self.log.warning(
                            f'Could not assign the role {role_name} to {key}:'
                            f' {not_found_entities} not found in the database.'
                        )

        # assign the granted roles to the current user
        for role_name in granted_roles:
            roles.grant_role(
                self.db,
                entity=self.orm_user,
                rolename=role_name,
                commit=False,
                managed=True,
            )

        # strip the user of roles no longer directly granted
        for role_name in stripped_roles:
            roles.strip_role(
                self.db, entity=self.orm_user, rolename=role_name, commit=False
            )
        managed_stripped_roles = (
            self.db.query(orm.Role)
            .filter(
                orm.Role.name.in_(stripped_roles) & (orm.Role.managed_by_auth == True)
            )
            .all()
        )
        for stripped_role in managed_stripped_roles:
            if (
                not stripped_role.users
                and not stripped_role.services
                and not stripped_role.groups
            ):
                self.db.delete(stripped_role)

        self.db.commit()

    async def save_auth_state(self, auth_state):
        """Encrypt and store auth_state"""
        if auth_state is None:
            self.encrypted_auth_state = None
        else:
            self.encrypted_auth_state = await encrypt(auth_state)
        self.db.commit()

    async def get_auth_state(self):
        """Retrieve and decrypt auth_state for the user"""
        encrypted = self.encrypted_auth_state
        if encrypted is None:
            return None
        try:
            auth_state = await decrypt(encrypted)
        except (ValueError, InvalidToken, EncryptionUnavailable) as e:
            self.log.warning(
                "Failed to retrieve encrypted auth_state for %s because %s",
                self.name,
                e,
            )
            return
        # loading auth_state
        if auth_state:
            # Crypt has multiple keys, store again with new key for rotation.
            if len(CryptKeeper.instance().keys) > 1:
                await self.save_auth_state(auth_state)
        return auth_state

    async def delete_spawners(self):
        """Call spawner cleanup methods

        Allows the spawner to cleanup persistent resources
        """
        for name in self.orm_user.orm_spawners.keys():
            await self._delete_spawner(name)

    async def _delete_spawner(self, name_or_spawner):
        """Delete a single spawner"""
        # always ensure full Spawner
        # this may instantiate the Spawner if it wasn't already running,
        # just to delete it
        if isinstance(name_or_spawner, str):
            spawner = self.spawners[name_or_spawner]
        else:
            spawner = name_or_spawner

        if spawner.active:
            raise RuntimeError(
                f"Spawner {spawner._log_name} is active and cannot be deleted."
            )
        try:
            await maybe_future(spawner.delete_forever())
        except Exception as e:
            self.log.exception(
                f"Error cleaning up persistent resources on {spawner._log_name}"
            )

    def all_spawners(self, include_default=True):
        """Generator yielding all my spawners

        including those that are not running.

        Spawners that aren't running will be low-level orm.Spawner objects,
        while those that are will be higher-level Spawner wrapper objects.
        """

        for name, orm_spawner in sorted(self.orm_user.orm_spawners.items()):
            if name == '' and not include_default:
                continue
            if name and not self.allow_named_servers:
                continue
            if name in self.spawners:
                # yield wrapper if it exists (server may be active)
                yield self.spawners[name]
            else:
                # otherwise, yield low-level ORM object (server is not active)
                yield orm_spawner

    def _new_orm_spawner(self, server_name):
        """Create the low-level orm Spawner object"""
        orm_spawner = orm.Spawner(name=server_name)
        self.db.add(orm_spawner)
        orm_spawner.user = self.orm_user
        self.db.commit()
        assert server_name in self.orm_spawners
        return orm_spawner

    def _new_spawner(self, server_name, spawner_class=None, **kwargs):
        """Create a new spawner"""
        if spawner_class is None:
            spawner_class = self.spawner_class
        self.log.debug("Creating %s for %s:%s", spawner_class, self.name, server_name)

        orm_spawner = self.orm_spawners.get(server_name)
        if orm_spawner is None:
            orm_spawner = self._new_orm_spawner(server_name)
        if server_name == '' and self.state:
            # migrate user.state to spawner.state
            orm_spawner.state = self.state
            self.state = None

        # use fully quoted name for client_id because it will be used in cookie-name
        # self.escaped_name may contain @ which is legal in URLs but not cookie keys
        client_id = f'jupyterhub-user-{quote(self.name)}'
        if server_name:
            client_id = f'{client_id}-{quote(server_name)}'

        trusted_alt_names = []
        trusted_alt_names.extend(self.settings.get('trusted_alt_names', []))
        if self.settings.get('subdomain_host'):
            trusted_alt_names.append('DNS:' + self.domain)

        spawn_kwargs = dict(
            user=self,
            orm_spawner=orm_spawner,
            hub=self.settings.get('hub'),
            authenticator=self.authenticator,
            config=self.settings.get('config'),
            proxy_spec=url_path_join(
                self.proxy_spec, url_escape_path(server_name), '/'
            ),
            _deprecated_db_session=self.db,
            oauth_client_id=client_id,
            cookie_options=self.settings.get('cookie_options', {}),
            cookie_host_prefix_enabled=self.settings.get(
                "cookie_host_prefix_enabled", False
            ),
            trusted_alt_names=trusted_alt_names,
            user_options=orm_spawner.user_options or {},
        )

        if self.settings.get('internal_ssl'):
            ssl_kwargs = dict(
                internal_ssl=self.settings.get('internal_ssl'),
                internal_trust_bundles=self.settings.get('internal_trust_bundles'),
                internal_certs_location=self.settings.get('internal_certs_location'),
            )
            spawn_kwargs.update(ssl_kwargs)

        # public URLs
        if self.settings.get("public_url"):
            public_url = self.settings["public_url"]
            hub = self.settings.get('hub')
            if hub is None:
                # only in mock tests
                hub_path = "/hub/"
            else:
                hub_path = hub.base_url
            spawn_kwargs["public_hub_url"] = urlunparse(
                public_url._replace(path=hub_path)
            )
        spawn_kwargs["public_url"] = self.public_url(server_name)

        # update with kwargs. Mainly for testing.
        spawn_kwargs.update(kwargs)
        spawner = spawner_class(**spawn_kwargs)
        spawner.load_state(orm_spawner.state or {})
        return spawner

    # singleton property, self.spawner maps onto spawner with empty server_name
    @property
    def spawner(self):
        return self.spawners['']

    @spawner.setter
    def spawner(self, spawner):
        self.spawners[''] = spawner

    # pass get/setattr to ORM user
    def __getattr__(self, attr):
        if hasattr(self.orm_user, attr):
            return getattr(self.orm_user, attr)
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if not attr.startswith('_') and self.orm_user and hasattr(self.orm_user, attr):
            setattr(self.orm_user, attr, value)
        else:
            super().__setattr__(attr, value)

    def __repr__(self):
        return repr(self.orm_user)

    @property
    def running(self):
        """property for whether the user's default server is running"""
        if not self.spawners:
            return False
        return self.spawner.ready

    @property
    def active(self):
        """True if any server is active"""
        if not self.spawners:
            return False
        return any(s.active for s in self.spawners.values())

    @property
    def spawn_pending(self):
        warnings.warn(
            "User.spawn_pending is deprecated in JupyterHub 0.8. Use Spawner.pending",
            DeprecationWarning,
        )
        return self.spawner.pending == 'spawn'

    @property
    def stop_pending(self):
        warnings.warn(
            "User.stop_pending is deprecated in JupyterHub 0.8. Use Spawner.pending",
            DeprecationWarning,
        )
        return self.spawner.pending == 'stop'

    @property
    def server(self):
        return self.spawner.server

    @property
    def escaped_name(self):
        """My name, escaped for use in URLs, cookies, etc."""
        return url_escape_path(self.name)

    @property
    def json_escaped_name(self):
        """The user name, escaped for use in javascript inserts, etc."""
        return json.dumps(self.name)[1:-1]

    @property
    def proxy_spec(self):
        """The proxy routespec for my default server"""
        if self.settings.get('subdomain_host'):
            return url_path_join(self.domain, self.base_url, '/')
        else:
            return url_path_join(self.base_url, '/')

    @property
    def domain(self):
        """Get the domain for my server."""
        hook = self.settings.get("subdomain_hook", subdomain_hook_legacy)
        return hook(self.name, self.settings['domain'], kind='user')

    @property
    def dns_safe_name(self):
        """Get a dns-safe encoding of my name

        - always safe value for a single DNS label
        - max 40 characters, leaving room for additional components

        .. versionadded:: 5.0
        """
        return _strict_dns_safe(self.name, max_length=40)

    @property
    def host(self):
        """Get the *host* for my server (proto://domain[:port])"""
        # if subdomains are used, use our domain

        if self.settings.get('subdomain_host'):
            parsed = urlparse(self.settings['subdomain_host'])
            h = f"{parsed.scheme}://{self.domain}"
            if parsed.port:
                h = f"{h}:{parsed.port}"
            return h
        elif self.settings.get("public_url"):
            # no subdomain, use public host url without path
            return urlunparse(self.settings["public_url"]._replace(path=""))
        else:
            return ""

    @property
    def url(self):
        """My URL

        Full name.domain/path if using subdomains, otherwise just my /base/url
        """
        if self.settings.get("subdomain_host"):
            return f"{self.host}{self.base_url}"
        else:
            return self.base_url

    def server_url(self, server_name=''):
        """Get the url for a server with a given name"""
        if not server_name:
            return self.url
        else:
            return url_path_join(self.url, url_escape_path(server_name), "/")

    def public_url(self, server_name=''):
        """Get the public URL of a server by name

        Like server_url, but empty if no public URL is specified
        """
        # server_url will be a full URL if using subdomains
        url = self.server_url(server_name)
        if "://" not in url:
            # not using subdomains, public URL may be specified
            if self.settings.get("public_url"):
                # add server's base_url path prefix to public host
                url = urlunparse(self.settings["public_url"]._replace(path=url))
            else:
                # no public url (from subdomain or host),
                # leave unspecified
                url = ""
        return url

    def progress_url(self, server_name=''):
        """API URL for progress endpoint for a server with a given name"""
        url_parts = [self.settings['hub'].base_url, 'api/users', self.escaped_name]
        if server_name:
            url_parts.extend(['servers', url_escape_path(server_name), 'progress'])
        else:
            url_parts.extend(['server/progress'])
        return url_path_join(*url_parts)

    async def refresh_auth(self, handler):
        """Refresh authentication if needed

        Checks authentication expiry and refresh it if needed.
        See Spawner.

        If the auth is expired and cannot be refreshed
        without forcing a new login, a few things can happen:

        1. if this is a normal user spawn,
           the user should be redirected to login
           and back to spawn after login.
        2. if this is a spawn via API or other user,
           spawn will fail until the user logs in again.

        Args:
            handler (RequestHandler):
                The handler for the request triggering the spawn.
                May be None
        """
        authenticator = self.authenticator
        if authenticator is None or not authenticator.refresh_pre_spawn:
            # nothing to do
            return

        # refresh auth
        auth_user = await handler.refresh_auth(self, force=True)

        if auth_user:
            # auth refreshed, all done
            return

        # if we got to here, auth is expired and couldn't be refreshed
        self.log.error(
            "Auth expired for %s; cannot spawn until they login again", self.name
        )
        # auth expired, cannot spawn without a fresh login
        # it's the current user *and* spawn via GET, trigger login redirect
        if handler.request.method == 'GET' and handler.current_user is self:
            self.log.info("Redirecting %s to login to refresh auth", self.name)
            url = self.get_login_url()
            next_url = self.request.uri
            sep = '&' if '?' in url else '?'
            url += sep + urlencode(dict(next=next_url))
            self.redirect(url)
            raise web.Finish()
        else:
            # spawn via POST or on behalf of another user.
            # nothing we can do here but fail
            raise web.HTTPError(400, f"{self.name}'s authentication has expired")

    async def spawn(self, server_name='', options=None, handler=None):
        """Start the user's spawner

        depending from the value of JupyterHub.allow_named_servers

        if False:
        JupyterHub expects only one single-server per user
        url of the server will be /user/:name

        if True:
        JupyterHub expects more than one single-server per user
        url of the server will be /user/:name/:server_name
        """
        db = self.db

        if handler:
            await self.refresh_auth(handler)

        base_url = url_path_join(self.base_url, url_escape_path(server_name), "/")

        orm_server = orm.Server(base_url=base_url)
        db.add(orm_server)
        note = f"Server at {base_url}"
        db.commit()

        spawner = self.get_spawner(server_name, replace_failed=True)
        spawner.server = server = Server(orm_server=orm_server)
        assert spawner.orm_spawner.server is orm_server

        requested_scopes = spawner.server_token_scopes
        if callable(requested_scopes):
            requested_scopes = await maybe_future(requested_scopes(spawner))
        if not requested_scopes:
            # nothing requested, default to 'server' role
            requested_scopes = orm.Role.find(db, "server").scopes
        requested_scopes = set(requested_scopes)
        # resolve !server filter, which won't resolve elsewhere,
        # because this token is not owned by the server's own oauth client
        server_filter = f"={self.name}/{server_name}"
        requested_scopes = {
            scope + server_filter if scope.endswith("!server") else scope
            for scope in requested_scopes
        }
        # ensure activity scope is requested, since activity doesn't work without
        activity_scope = "users:activity!user"
        if not {activity_scope, "users:activity", "inherit"}.intersection(
            requested_scopes
        ):
            self.log.warning(
                f"Adding required scope {activity_scope} to server token, missing from Spawner.server_token_scopes. Please make sure to add it!"
            )
            requested_scopes |= {activity_scope}

        have_scopes = roles.roles_to_scopes(roles.get_roles_for(self.orm_user))
        have_scopes |= {"inherit"}
        jupyterhub_client = (
            db.query(orm.OAuthClient)
            .filter_by(
                identifier="jupyterhub",
            )
            .one()
        )

        resolved_scopes, excluded_scopes = scopes._resolve_requested_scopes(
            requested_scopes, have_scopes, self.orm_user, jupyterhub_client, db
        )
        if excluded_scopes:
            # what level should this be?
            # for admins-get-more use case, this is going to happen for most users
            # but for misconfiguration, folks will want to know!
            self.log.debug(
                "Not assigning requested scopes for %s: requested=%s, assigned=%s, excluded=%s",
                spawner._log_name,
                requested_scopes,
                resolved_scopes,
                excluded_scopes,
            )

        api_token = self.new_api_token(note=note, scopes=resolved_scopes)

        # pass requesting handler to the spawner
        # e.g. for processing GET params
        spawner.handler = handler

        # Passing user_options to the spawner
        if options is None:
            # options unspecified, load from db which should have the previous value
            options = spawner.orm_spawner.user_options or {}
        else:
            # options specified, save for use as future defaults
            spawner.orm_spawner.user_options = options
            db.commit()

        spawner.user_options = options
        # we are starting a new server, make sure it doesn't restore state
        spawner.clear_state()

        # create API and OAuth tokens
        spawner.api_token = api_token
        spawner.admin_access = self.settings.get('admin_access', False)
        client_id = spawner.oauth_client_id
        oauth_provider = self.settings.get('oauth_provider')
        if oauth_provider:
            allowed_scopes = await spawner._get_oauth_client_allowed_scopes()
            oauth_client = oauth_provider.add_client(
                client_id,
                api_token,
                url_path_join(self.url, url_escape_path(server_name), 'oauth_callback'),
                allowed_scopes=allowed_scopes,
                description=f"Server at {url_path_join(self.base_url, server_name, '/')}",
            )
            spawner.orm_spawner.oauth_client = oauth_client
        db.commit()

        # trigger pre-spawn hook on authenticator
        authenticator = self.authenticator
        try:
            spawner._start_pending = True

            if authenticator:
                # pre_spawn_start can throw errors that can lead to a redirect loop
                # if left uncaught (see https://github.com/jupyterhub/jupyterhub/issues/2683)
                await maybe_future(authenticator.pre_spawn_start(self, spawner))

            # trigger auth_state hook
            auth_state = await self.get_auth_state()
            await spawner.run_auth_state_hook(auth_state)

            # update spawner start time, and activity for both spawner and user
            self.last_activity = spawner.orm_spawner.started = (
                spawner.orm_spawner.last_activity
            ) = utcnow(with_tz=False)
            db.commit()
            # wait for spawner.start to return
            # run optional preparation work to bootstrap the notebook
            await spawner.apply_group_overrides()
            await spawner._run_apply_user_options(spawner.user_options)
            await maybe_future(spawner.run_pre_spawn_hook())
            if self.settings.get('internal_ssl'):
                self.log.debug("Creating internal SSL certs for %s", spawner._log_name)
                hub_paths = await maybe_future(spawner.create_certs())
                spawner.cert_paths = await maybe_future(spawner.move_certs(hub_paths))
            self.log.debug("Calling Spawner.start for %s", spawner._log_name)
            f = maybe_future(spawner.start())
            # commit any changes in spawner.start (always commit db changes before await)
            db.commit()
            # gen.with_timeout protects waited-for tasks from cancellation,
            # whereas wait_for cancels tasks that don't finish within timeout.
            # we want this task to halt if it doesn't return in the time limit.
            await asyncio.wait_for(f, timeout=spawner.start_timeout)
            url = f.result()
            if url:
                # get url from return value of start()
                if not isinstance(url, str):
                    # older Spawners return (ip, port)
                    proto = 'https' if self.settings['internal_ssl'] else 'http'
                    ip, port = url
                    # check if spawner returned an IPv6 address
                    if ':' in ip:
                        # ipv6 needs [::] in url
                        ip = f'[{ip}]'
                    url = f'{proto}://{ip}:{int(port)}'
                urlinfo = urlparse(url)
                server.proto = urlinfo.scheme
                server.ip = urlinfo.hostname
                port = urlinfo.port
                if not port:
                    if urlinfo.scheme == 'https':
                        port = 443
                    else:
                        port = 80
                server.port = port
                db.commit()
            else:
                # prior to 0.7, spawners had to store this info in user.server themselves.
                # Handle < 0.7 behavior with a warning, assuming info was stored in db by the Spawner.
                self.log.warning(
                    "DEPRECATION: Spawner.start should return a url or (ip, port) tuple in JupyterHub >= 0.9"
                )
            if spawner.api_token and spawner.api_token != api_token:
                # Spawner re-used an API token, discard the unused api_token
                orm_token = orm.APIToken.find(self.db, api_token)
                if orm_token is not None:
                    self.db.delete(orm_token)
                    self.db.commit()
                # check if the re-used API token is valid
                found = orm.APIToken.find(self.db, spawner.api_token)
                if found:
                    if found.user is not self.orm_user:
                        self.log.error(
                            "%s's server is using %s's token! Revoking this token.",
                            self.name,
                            (found.user or found.service).name,
                        )
                        self.db.delete(found)
                        self.db.commit()
                        raise ValueError(f"Invalid token for {self.name}!")
                else:
                    # Spawner.api_token has changed, but isn't in the db.
                    # What happened? Maybe something unclean in a resumed container.
                    self.log.warning(
                        "%s's server specified its own API token that's not in the database",
                        self.name,
                    )
                    # use generated=False because we don't trust this token
                    # to have been generated properly
                    self.new_api_token(
                        spawner.api_token,
                        generated=False,
                        note=f"retrieved from spawner {server_name}",
                        scopes=resolved_scopes,
                    )
                # update OAuth client secret with updated API token
                if oauth_provider:
                    oauth_provider.add_client(
                        client_id,
                        spawner.api_token,
                        url_path_join(
                            self.url, url_escape_path(server_name), 'oauth_callback'
                        ),
                    )
                    db.commit()

        except Exception as e:
            if isinstance(e, AnyTimeoutError):
                self.log.warning(
                    f"{self.name}'s server failed to start"
                    f" in {spawner.start_timeout} seconds, giving up."
                    f"\n{start_timeout_message}"
                )
                e.reason = 'timeout'
                self.settings['statsd'].incr('spawner.failure.timeout')
            else:
                self.log.exception(
                    f"Unhandled error starting {self.name}'s server: {e}"
                )
                self.settings['statsd'].incr('spawner.failure.error')
                e.reason = 'error'
            try:
                await self.stop(spawner.name)
            except Exception:
                self.log.exception(
                    f"Failed to cleanup {self.name}'s server that failed to start",
                    exc_info=True,
                )
            # raise original exception
            spawner._start_pending = False
            raise e
        finally:
            # clear reference to handler after start finishes
            spawner.handler = None
        spawner.start_polling()

        # store state
        if self.state is None:
            self.state = {}
        spawner.orm_spawner.state = spawner.get_state()
        db.commit()
        spawner._waiting_for_response = True
        await self._wait_up(spawner)

    async def _wait_up(self, spawner):
        """Wait for a server to finish starting.

        Shuts the server down if it doesn't respond within
        spawner.http_timeout.
        """
        server = spawner.server
        key = self.settings.get('internal_ssl_key')
        cert = self.settings.get('internal_ssl_cert')
        ca = self.settings.get('internal_ssl_ca')
        ssl_context = make_ssl_context(key, cert, cafile=ca)
        try:
            resp = await server.wait_up(
                http=True,
                timeout=spawner.http_timeout,
                ssl_context=ssl_context,
                extra_path="api",
            )
        except Exception as e:
            if isinstance(e, AnyTimeoutError):
                self.log.warning(
                    f"{self.name}'s server never showed up at {server.url}"
                    f" after {spawner.http_timeout} seconds. Giving up."
                    f"\n{http_timeout_message}"
                )
                e.reason = 'timeout'
                self.settings['statsd'].incr('spawner.failure.http_timeout')
            else:
                e.reason = 'error'
                self.log.exception(
                    f"Unhandled error waiting for {self.name}'s server to show up at {server.url}: {e}"
                )
                self.settings['statsd'].incr('spawner.failure.http_error')
            try:
                await self.stop(spawner.name)
            except Exception:
                self.log.exception(
                    f"Failed to cleanup {self.name}'s server that failed to start",
                    exc_info=True,
                )
            # raise original TimeoutError
            raise e
        else:
            server_version = resp.headers.get('X-JupyterHub-Version')
            _check_version(__version__, server_version, self.log)
            # record the Spawner version for better error messages
            # if it doesn't work
            spawner._jupyterhub_version = server_version
        finally:
            spawner._waiting_for_response = False
            spawner._start_pending = False
        return spawner

    async def stop(self, server_name=''):
        """Stop the user's spawner

        and cleanup after it.
        """
        spawner = self.spawners[server_name]
        spawner._spawn_pending = False
        spawner._start_pending = False
        spawner._check_pending = False
        spawner.stop_polling()
        spawner._stop_pending = True

        self.log.debug("Stopping %s", spawner._log_name)

        try:
            api_token = spawner.api_token
            status = await spawner.poll()
            if status is None:
                await spawner.stop()
            self.last_activity = spawner.orm_spawner.last_activity = utcnow(
                with_tz=False
            )
            # remove server entry from db
            spawner.server = None
            if not spawner.will_resume:
                # find and remove the API token and oauth client if the spawner isn't
                # going to re-use it next time
                orm_token = orm.APIToken.find(self.db, api_token)
                if orm_token:
                    self.db.delete(orm_token)
                # remove oauth client as well
                for oauth_client in self.db.query(orm.OAuthClient).filter_by(
                    identifier=spawner.oauth_client_id,
                ):
                    self.log.debug("Deleting oauth client %s", oauth_client.identifier)
                    self.db.delete(oauth_client)
            self.db.commit()
            self.log.debug("Finished stopping %s", spawner._log_name)
            RUNNING_SERVERS.dec()
        finally:
            spawner.server = None
            spawner.orm_spawner.started = None
            self.db.commit()
            # trigger post-stop hook
            try:
                await maybe_future(spawner.run_post_stop_hook())
            except Exception:
                self.log.exception("Error in Spawner.post_stop_hook for %s", self)
            spawner.clear_state()
            spawner.orm_spawner.state = spawner.get_state()
            self.db.commit()

            # trigger post-spawner hook on authenticator
            auth = spawner.authenticator
            try:
                if auth:
                    await maybe_future(auth.post_spawn_stop(self, spawner))
            except Exception:
                self.log.exception(
                    "Error in Authenticator.post_spawn_stop for %s", self
                )
            spawner._stop_pending = False
            if not (
                spawner._spawn_future
                and (
                    not spawner._spawn_future.done()
                    or spawner._spawn_future.exception()
                )
            ):
                # pop Spawner *unless* it's stopping due to an error
                # because some pages serve latest-spawn error messages
                self.spawners.pop(server_name)
