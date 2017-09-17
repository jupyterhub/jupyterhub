# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse
import warnings

from oauth2.error import ClientNotFoundError
from sqlalchemy import inspect
from tornado import gen
from tornado.log import app_log
from traitlets import HasTraits, Any, Dict, default

from .utils import url_path_join

from . import orm
from ._version import _check_version, __version__
from .objects import Server
from .spawner import LocalProcessSpawner
from .crypto import encrypt, decrypt, CryptKeeper, EncryptionUnavailable, InvalidToken

class UserDict(dict):
    """Like defaultdict, but for users

    Getting by a user id OR an orm.User instance returns a User wrapper around the orm user.
    """
    def __init__(self, db_factory, settings):
        self.db_factory = db_factory
        self.settings = settings
        super().__init__()

    @property
    def db(self):
        return self.db_factory()

    def __contains__(self, key):
        if isinstance(key, (User, orm.User)):
            key = key.id
        return dict.__contains__(self, key)

    def __getitem__(self, key):
        if isinstance(key, User):
            key = key.id
        elif isinstance(key, str):
            orm_user = self.db.query(orm.User).filter(orm.User.name == key).first()
            if orm_user is None:
                raise KeyError("No such user: %s" % key)
            else:
                key = orm_user
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
                user = self[id] = User(orm_user, self.settings)
            return dict.__getitem__(self, id)
        else:
            raise KeyError(repr(key))

    def __delitem__(self, key):
        user = self[key]
        user_id = user.id
        db = self.db
        db.delete(user.orm_user)
        db.commit()
        dict.__delitem__(self, user_id)

    def count_active_users(self):
        """Count the number of user servers that are active/pending/ready
        
        Returns dict with counts of active/pending/ready servers
        """
        counts = defaultdict(lambda : 0)
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


class User(HasTraits):

    @default('log')
    def _log_default(self):
        return app_log

    spawners = None
    settings = Dict()

    db = Any(allow_none=True)

    @default('db')
    def _db_default(self):
        if self.orm_user:
            return inspect(self.orm_user).session

    orm_user = Any(allow_none=True)

    @gen.coroutine
    def save_auth_state(self, auth_state):
        """Encrypt and store auth_state"""
        if auth_state is None:
            self.encrypted_auth_state = None
        else:
            self.encrypted_auth_state = yield encrypt(auth_state)
        self.db.commit()

    @gen.coroutine
    def get_auth_state(self):
        """Retrieve and decrypt auth_state for the user"""
        encrypted = self.encrypted_auth_state
        if encrypted is None:
            return None
        try:
            auth_state = yield decrypt(encrypted)
        except (ValueError, InvalidToken, EncryptionUnavailable) as e:
            self.log.warning("Failed to retrieve encrypted auth_state for %s because %s",
                self.name, e,
            )
            return
        # loading auth_state
        if auth_state:
            # Crypt has multiple keys, store again with new key for rotation.
            if len(CryptKeeper.instance().keys) > 1:
                yield self.save_auth_state(auth_state)
        return auth_state

    @property
    def authenticator(self):
        return self.settings.get('authenticator', None)

    @property
    def spawner_class(self):
        return self.settings.get('spawner_class', LocalProcessSpawner)

    def __init__(self, orm_user, settings=None, **kwargs):
        if settings:
            kwargs['settings'] = settings
        kwargs['orm_user'] = orm_user
        super().__init__(**kwargs)

        self.allow_named_servers = self.settings.get('allow_named_servers', False)

        self.base_url = self.prefix = url_path_join(
            self.settings.get('base_url', '/'), 'user', self.escaped_name) + '/'

        self.spawners = _SpawnerDict(self._new_spawner)
        # load existing named spawners
        for name in self.orm_spawners:
            self.spawners[name] = self._new_spawner(name)

    def _new_spawner(self, name, spawner_class=None, **kwargs):
        """Create a new spawner"""
        if spawner_class is None:
            spawner_class = self.spawner_class
        self.log.debug("Creating %s for %s:%s", spawner_class, self.name, name)
        
        orm_spawner = self.orm_spawners.get(name)
        if orm_spawner is None:
            orm_spawner = orm.Spawner(user=self.orm_user, name=name)
            self.db.add(orm_spawner)
            self.db.commit()
            assert name in self.orm_spawners
        if name == '' and self.state:
            # migrate user.state to spawner.state
            orm_spawner.state = self.state
            self.state = None
        
        spawn_kwargs = dict(
            user=self,
            orm_spawner=orm_spawner,
            hub=self.settings.get('hub'),
            authenticator=self.authenticator,
            config=self.settings.get('config'),
            proxy_spec=url_path_join(self.proxy_spec, name, '/'),
            db=self.db,
        )
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
        return self.spawner.ready

    @property
    def active(self):
        """True if any server is active"""
        return any(s.active for s in self.spawners.values())

    @property
    def spawn_pending(self):
        warnings.warn("User.spawn_pending is deprecated in JupyterHub 0.8. Use Spawner.pending",
            DeprecationWarning,
        )
        return self.spawner.pending == 'spawn'

    @property
    def stop_pending(self):
        warnings.warn("User.stop_pending is deprecated in JupyterHub 0.8. Use Spawner.pending",
            DeprecationWarning,
        )
        return self.spawner.pending == 'stop'

    @property
    def server(self):
        return self.spawner.server

    @property
    def escaped_name(self):
        """My name, escaped for use in URLs, cookies, etc."""
        return quote(self.name, safe='@')

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
        # FIXME: escaped_name probably isn't escaped enough in general for a domain fragment
        return self.escaped_name + '.' + self.settings['domain']

    @property
    def host(self):
        """Get the *host* for my server (proto://domain[:port])"""
        # FIXME: escaped_name probably isn't escaped enough in general for a domain fragment
        parsed = urlparse(self.settings['subdomain_host'])
        h = '%s://%s.%s' % (parsed.scheme, self.escaped_name, parsed.netloc)
        return h

    @property
    def url(self):
        """My URL

        Full name.domain/path if using subdomains, otherwise just my /base/url
        """
        if self.settings.get('subdomain_host'):
            return '{host}{path}'.format(
                host=self.host,
                path=self.base_url,
            )
        else:
            return self.base_url

    @gen.coroutine
    def spawn(self, server_name='', options=None):
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

        base_url = url_path_join(self.base_url, server_name) + '/'

        orm_server = orm.Server(
            base_url=base_url,
        )
        db.add(orm_server)

        api_token = self.new_api_token()
        db.commit()


        spawner = self.spawners[server_name]
        spawner.server = server = Server(orm_server=orm_server)
        assert spawner.orm_spawner.server is orm_server

        # Passing user_options to the spawner
        spawner.user_options = options or {}
        # we are starting a new server, make sure it doesn't restore state
        spawner.clear_state()

        # create API and OAuth tokens
        spawner.api_token = api_token
        spawner.admin_access = self.settings.get('admin_access', False)
        # use fully quoted name for client_id because it will be used in cookie-name
        # self.escaped_name may contain @ which is legal in URLs but not cookie keys
        client_id = 'user-%s' % quote(self.name)
        if server_name:
            client_id = '%s-%s' % (client_id, quote(server_name))
        spawner.oauth_client_id = client_id
        oauth_provider = self.settings.get('oauth_provider')
        if oauth_provider:
            client_store = oauth_provider.client_authenticator.client_store
            try:
                oauth_client = client_store.fetch_by_client_id(client_id)
            except ClientNotFoundError:
                oauth_client = None
            # create a new OAuth client + secret on every launch
            # containers that resume will be updated below
            client_store.add_client(client_id, api_token,
                                    url_path_join(self.url, server_name, 'oauth_callback'),
                                    )
        db.commit()

        # trigger pre-spawn hook on authenticator
        authenticator = self.authenticator
        if (authenticator):
            yield gen.maybe_future(authenticator.pre_spawn_start(self, spawner))

        spawner._start_pending = True
        # wait for spawner.start to return
        try:
            # run optional preparation work to bootstrap the notebook
            yield gen.maybe_future(self.spawner.run_pre_spawn_hook())
            f = spawner.start()
            # commit any changes in spawner.start (always commit db changes before yield)
            db.commit()
            ip_port = yield gen.with_timeout(timedelta(seconds=spawner.start_timeout), f)
            if ip_port:
                # get ip, port info from return value of start()
                server.ip, server.port = ip_port
            else:
                # prior to 0.7, spawners had to store this info in user.server themselves.
                # Handle < 0.7 behavior with a warning, assuming info was stored in db by the Spawner.
                self.log.warning("DEPRECATION: Spawner.start should return (ip, port) in JupyterHub >= 0.7")
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
                        self.log.error("%s's server is using %s's token! Revoking this token.",
                            self.name, (found.user or found.service).name)
                        self.db.delete(found)
                        self.db.commit()
                        raise ValueError("Invalid token for %s!" % self.name)
                else:
                    # Spawner.api_token has changed, but isn't in the db.
                    # What happened? Maybe something unclean in a resumed container.
                    self.log.warning("%s's server specified its own API token that's not in the database",
                        self.name
                    )
                    # use generated=False because we don't trust this token
                    # to have been generated properly
                    self.new_api_token(spawner.api_token, generated=False)
                # update OAuth client secret with updated API token
                if oauth_provider:
                    client_store = oauth_provider.client_authenticator.client_store
                    client_store.add_client(client_id, spawner.api_token,
                                            url_path_join(self.url, server_name, 'oauth_callback'),
                                            )
                    db.commit()

        except Exception as e:
            if isinstance(e, gen.TimeoutError):
                self.log.warning("{user}'s server failed to start in {s} seconds, giving up".format(
                    user=self.name, s=spawner.start_timeout,
                ))
                e.reason = 'timeout'
            else:
                self.log.error("Unhandled error starting {user}'s server: {error}".format(
                    user=self.name, error=e,
                ))
                e.reason = 'error'
            try:
                yield self.stop()
            except Exception:
                self.log.error("Failed to cleanup {user}'s server that failed to start".format(
                    user=self.name,
                ), exc_info=True)
            # raise original exception
            spawner._start_pending = False
            raise e
        spawner.start_polling()

        # store state
        if self.state is None:
            self.state = {}
        spawner.orm_spawner.state = spawner.get_state()
        self.last_activity = spawner.orm_spawner.last_activity = datetime.utcnow()
        db.commit()
        spawner._waiting_for_response = True
        try:
            resp = yield server.wait_up(http=True, timeout=spawner.http_timeout)
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
            else:
                e.reason = 'error'
                self.log.error("Unhandled error waiting for {user}'s server to show up at {url}: {error}".format(
                    user=self.name, url=server.url, error=e,
                ))
            try:
                yield self.stop()
            except Exception:
                self.log.error("Failed to cleanup {user}'s server that failed to start".format(
                    user=self.name,
                ), exc_info=True)
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
        return self

    @gen.coroutine
    def stop(self, server_name=''):
        """Stop the user's spawner

        and cleanup after it.
        """
        spawner = self.spawners[server_name]
        spawner._spawn_pending = False
        spawner._start_pending = False
        spawner.stop_polling()
        spawner._stop_pending = True
        try:
            api_token = spawner.api_token
            status = yield spawner.poll()
            if status is None:
                yield spawner.stop()
            spawner.clear_state()
            spawner.orm_spawner.state = spawner.get_state()
            self.last_activity = spawner.orm_spawner.last_activity = datetime.utcnow()
            # remove server entry from db
            spawner.server = None
            if not spawner.will_resume:
                # find and remove the API token if the spawner isn't
                # going to re-use it next time
                orm_token = orm.APIToken.find(self.db, api_token)
                if orm_token:
                    self.db.delete(orm_token)
            self.db.commit()
        finally:
            # trigger post-spawner hook on authenticator
            auth = spawner.authenticator
            try:
                if auth:
                    yield gen.maybe_future(
                        auth.post_spawn_stop(self, spawner)
                    )
            except Exception:
                self.log.exception("Error in Authenticator.post_spawn_stop for %s", self)
            spawner._stop_pending = False
