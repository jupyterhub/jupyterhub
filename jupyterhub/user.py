# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import warnings
from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from urllib.parse import quote
from urllib.parse import urlparse

from sqlalchemy import inspect
from tornado import gen
from tornado import web
from tornado.httputil import urlencode
from tornado.log import app_log

from . import orm
from ._version import __version__
from ._version import _check_version
from .crypto import CryptKeeper
from .crypto import decrypt
from .crypto import encrypt
from .crypto import EncryptionUnavailable
from .crypto import InvalidToken
from .metrics import RUNNING_SERVERS
from .metrics import TOTAL_USERS
from .objects import Server
from .spawner import LocalProcessSpawner
from .utils import make_ssl_context
from .utils import maybe_future
from .utils import url_path_join


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
            TOTAL_USERS.inc()
        return self[orm_user.id]

    def __contains__(self, key):
        """key in userdict checks presence in the cache

        it does not check if the user is in the database
        """
        if isinstance(key, (User, orm.User)):
            key = key.id
        elif isinstance(key, str):
            # username lookup, O(N)
            for user in self.values():
                if user.name == key:
                    key = user.id
                    break
        return dict.__contains__(self, key)

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
                raise KeyError("No such user: %s" % key)
            else:
                key = orm_user.id
        if isinstance(key, orm.User):
            # users[orm_user] returns User(orm_user)
            orm_user = key
            if orm_user.id not in self:
                user = self[orm_user.id] = User(orm_user, self.settings)
                return user
            user = dict.__getitem__(self, orm_user.id)
            user.db = self.db
            return user
        elif isinstance(key, int):
            id = key
            if id not in self:
                orm_user = self.db.query(orm.User).filter(orm.User.id == id).first()
                if orm_user is None:
                    raise KeyError("No such user: %s" % id)
                user = self.add(orm_user)
            else:
                user = dict.__getitem__(self, id)
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
        dict.__delitem__(self, user.id)

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
        counts = defaultdict(lambda: 0)
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
        """Creat the low-level orm Spawner object"""
        orm_spawner = orm.Spawner(user=self.orm_user, name=server_name)
        self.db.add(orm_spawner)
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
        client_id = 'jupyterhub-user-%s' % quote(self.name)
        if server_name:
            client_id = '%s-%s' % (client_id, quote(server_name))

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
            proxy_spec=url_path_join(self.proxy_spec, server_name, '/'),
            db=self.db,
            oauth_client_id=client_id,
            cookie_options=self.settings.get('cookie_options', {}),
            trusted_alt_names=trusted_alt_names,
        )

        if self.settings.get('internal_ssl'):
            ssl_kwargs = dict(
                internal_ssl=self.settings.get('internal_ssl'),
                internal_trust_bundles=self.settings.get('internal_trust_bundles'),
                internal_certs_location=self.settings.get('internal_certs_location'),
            )
            spawn_kwargs.update(ssl_kwargs)

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
        return quote(self.name, safe='@~')

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
        # use underscore as escape char for domains
        return (
            quote(self.name).replace('%', '_').lower() + '.' + self.settings['domain']
        )

    @property
    def host(self):
        """Get the *host* for my server (proto://domain[:port])"""
        # FIXME: escaped_name probably isn't escaped enough in general for a domain fragment
        parsed = urlparse(self.settings['subdomain_host'])
        h = '%s://%s' % (parsed.scheme, self.domain)
        if parsed.port:
            h += ':%i' % parsed.port
        return h

    @property
    def url(self):
        """My URL

        Full name.domain/path if using subdomains, otherwise just my /base/url
        """
        if self.settings.get('subdomain_host'):
            return '{host}{path}'.format(host=self.host, path=self.base_url)
        else:
            return self.base_url

    def server_url(self, server_name=''):
        """Get the url for a server with a given name"""
        if not server_name:
            return self.url
        else:
            return url_path_join(self.url, server_name)

    def progress_url(self, server_name=''):
        """API URL for progress endpoint for a server with a given name"""
        url_parts = [self.settings['hub'].base_url, 'api/users', self.escaped_name]
        if server_name:
            url_parts.extend(['servers', server_name, 'progress'])
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
            raise web.HTTPError(
                400, "{}'s authentication has expired".format(self.name)
            )

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

        base_url = url_path_join(self.base_url, server_name) + '/'

        orm_server = orm.Server(base_url=base_url)
        db.add(orm_server)
        note = "Server at %s" % base_url
        api_token = self.new_api_token(note=note)
        db.commit()

        spawner = self.spawners[server_name]
        spawner.server = server = Server(orm_server=orm_server)
        assert spawner.orm_spawner.server is orm_server

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
            oauth_client = oauth_provider.fetch_by_client_id(client_id)
            # create a new OAuth client + secret on every launch
            # containers that resume will be updated below
            oauth_provider.add_client(
                client_id,
                api_token,
                url_path_join(self.url, server_name, 'oauth_callback'),
                description="Server at %s"
                % (url_path_join(self.base_url, server_name) + '/'),
            )
        db.commit()

        # trigger pre-spawn hook on authenticator
        authenticator = self.authenticator
        try:
            spawner._start_pending = True

            if authenticator:
                # pre_spawn_start can thow errors that can lead to a redirect loop
                # if left uncaught (see https://github.com/jupyterhub/jupyterhub/issues/2683)
                await maybe_future(authenticator.pre_spawn_start(self, spawner))

            # trigger auth_state hook
            auth_state = await self.get_auth_state()
            await spawner.run_auth_state_hook(auth_state)

            # update spawner start time, and activity for both spawner and user
            self.last_activity = (
                spawner.orm_spawner.started
            ) = spawner.orm_spawner.last_activity = datetime.utcnow()
            db.commit()
            # wait for spawner.start to return
            # run optional preparation work to bootstrap the notebook
            await maybe_future(spawner.run_pre_spawn_hook())
            if self.settings.get('internal_ssl'):
                self.log.debug("Creating internal SSL certs for %s", spawner._log_name)
                hub_paths = await maybe_future(spawner.create_certs())
                spawner.cert_paths = await maybe_future(spawner.move_certs(hub_paths))
            self.log.debug("Calling Spawner.start for %s", spawner._log_name)
            f = maybe_future(spawner.start())
            # commit any changes in spawner.start (always commit db changes before yield)
            db.commit()
            url = await gen.with_timeout(timedelta(seconds=spawner.start_timeout), f)
            if url:
                # get ip, port info from return value of start()
                if isinstance(url, str):
                    # >= 0.9 can return a full URL string
                    pass
                else:
                    # >= 0.7 returns (ip, port)
                    proto = 'https' if self.settings['internal_ssl'] else 'http'

                    # check if spawner returned an IPv6 address
                    if ':' in url[0]:
                        url = '%s://[%s]:%i' % ((proto,) + url)
                    else:
                        url = '%s://%s:%i' % ((proto,) + url)
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
                        raise ValueError("Invalid token for %s!" % self.name)
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
                        note="retrieved from spawner %s" % server_name,
                    )
                # update OAuth client secret with updated API token
                if oauth_provider:
                    oauth_provider.add_client(
                        client_id,
                        spawner.api_token,
                        url_path_join(self.url, server_name, 'oauth_callback'),
                    )
                    db.commit()

        except Exception as e:
            if isinstance(e, gen.TimeoutError):
                self.log.warning(
                    "{user}'s server failed to start in {s} seconds, giving up".format(
                        user=self.name, s=spawner.start_timeout
                    )
                )
                e.reason = 'timeout'
                self.settings['statsd'].incr('spawner.failure.timeout')
            else:
                self.log.error(
                    "Unhandled error starting {user}'s server: {error}".format(
                        user=self.name, error=e
                    )
                )
                self.settings['statsd'].incr('spawner.failure.error')
                e.reason = 'error'
            try:
                await self.stop(spawner.name)
            except Exception:
                self.log.error(
                    "Failed to cleanup {user}'s server that failed to start".format(
                        user=self.name
                    ),
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
                http=True, timeout=spawner.http_timeout, ssl_context=ssl_context
            )
        except Exception as e:
            if isinstance(e, TimeoutError):
                self.log.warning(
                    "{user}'s server never showed up at {url} "
                    "after {http_timeout} seconds. Giving up".format(
                        user=self.name,
                        url=server.url,
                        http_timeout=spawner.http_timeout,
                    )
                )
                e.reason = 'timeout'
                self.settings['statsd'].incr('spawner.failure.http_timeout')
            else:
                e.reason = 'error'
                self.log.error(
                    "Unhandled error waiting for {user}'s server to show up at {url}: {error}".format(
                        user=self.name, url=server.url, error=e
                    )
                )
                self.settings['statsd'].incr('spawner.failure.http_error')
            try:
                await self.stop(spawner.name)
            except Exception:
                self.log.error(
                    "Failed to cleanup {user}'s server that failed to start".format(
                        user=self.name
                    ),
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
            self.last_activity = spawner.orm_spawner.last_activity = datetime.utcnow()
            # remove server entry from db
            spawner.server = None
            if not spawner.will_resume:
                # find and remove the API token and oauth client if the spawner isn't
                # going to re-use it next time
                orm_token = orm.APIToken.find(self.db, api_token)
                if orm_token:
                    self.db.delete(orm_token)
                # remove oauth client as well
                # handle upgrades from 0.8, where client id will be `user-USERNAME`,
                # not just `jupyterhub-user-USERNAME`
                client_ids = (
                    spawner.oauth_client_id,
                    spawner.oauth_client_id.split('-', 1)[1],
                )
                for oauth_client in self.db.query(orm.OAuthClient).filter(
                    orm.OAuthClient.identifier.in_(client_ids)
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
            except:
                spawner.clear_state()
                spawner.orm_spawner.state = spawner.get_state()
                self.db.commit()
                raise
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
