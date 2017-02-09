# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

from tornado import gen
from tornado.log import app_log

from sqlalchemy import inspect

from .utils import url_path_join

from . import orm
from traitlets import HasTraits, Any, Dict, observe, default
from .spawner import LocalProcessSpawner


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


class User(HasTraits):

    @default('log')
    def _log_default(self):
        return app_log

    settings = Dict()

    db = Any(allow_none=True)

    @default('db')
    def _db_default(self):
        if self.orm_user:
            return inspect(self.orm_user).session

    @observe('db')
    def _db_changed(self, change):
        """Changing db session reacquires ORM User object"""
        # db session changed, re-get orm User
        if self.orm_user:
            id = self.orm_user.id
            self.orm_user = change['new'].query(orm.User).filter(orm.User.id == id).first()
        self.spawner.db = self.db

    orm_user = None
    spawner = None
    spawn_pending = False
    stop_pending = False
    waiting_for_response = False

    @property
    def authenticator(self):
        return self.settings.get('authenticator', None)

    @property
    def spawner_class(self):
        return self.settings.get('spawner_class', LocalProcessSpawner)

    def __init__(self, orm_user, settings, **kwargs):
        self.orm_user = orm_user
        self.settings = settings
        super().__init__(**kwargs)

        hub = self.db.query(orm.Hub).first()

        self.cookie_name = '%s-%s' % (hub.server.cookie_name, quote(self.name, safe=''))
        self.base_url = url_path_join(
            self.settings.get('base_url', '/'), 'user', self.escaped_name)

        self.spawner = self.spawner_class(
            user=self,
            db=self.db,
            hub=hub,
            authenticator=self.authenticator,
            config=self.settings.get('config'),
        )

    # pass get/setattr to ORM user

    def __getattr__(self, attr):
        if hasattr(self.orm_user, attr):
            return getattr(self.orm_user, attr)
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if self.orm_user and hasattr(self.orm_user, attr):
            setattr(self.orm_user, attr, value)
        else:
            super().__setattr__(attr, value)

    def __repr__(self):
        return repr(self.orm_user)

    @property
    def running(self):
        """property for whether a user has a running server"""
        if self.spawn_pending or self.stop_pending:
            return False  # server is not running if spawn or stop is still pending
        if self.server is None:
            return False
        return True

    @property
    def escaped_name(self):
        """My name, escaped for use in URLs, cookies, etc."""
        return quote(self.name, safe='@')

    @property
    def proxy_path(self):
        if self.settings.get('subdomain_host'):
            return url_path_join('/' + self.domain, self.base_url)
        else:
            return self.base_url

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
    def spawn(self, options=None):
        """Start the user's spawner"""
        db = self.db
        server = orm.Server(
            cookie_name=self.cookie_name,
            base_url=self.base_url,
        )
        self.servers.append(server)
        db.add(self)
        db.commit()

        api_token = self.new_api_token()
        db.commit()

        spawner = self.spawner
        spawner.user_options = options or {}
        # we are starting a new server, make sure it doesn't restore state
        spawner.clear_state()
        spawner.api_token = api_token

        # trigger pre-spawn hook on authenticator
        authenticator = self.authenticator
        if (authenticator):
            yield gen.maybe_future(authenticator.pre_spawn_start(self, spawner))

        self.spawn_pending = True
        # wait for spawner.start to return
        try:
            f = spawner.start()
            # commit any changes in spawner.start (always commit db changes before yield)
            db.commit()
            ip_port = yield gen.with_timeout(timedelta(seconds=spawner.start_timeout), f)
            if ip_port:
                # get ip, port info from return value of start()
                self.server.ip, self.server.port = ip_port
            else:
                # prior to 0.7, spawners had to store this info in user.server themselves.
                # Handle < 0.7 behavior with a warning, assuming info was stored in db by the Spawner.
                self.log.warning("DEPRECATION: Spawner.start should return (ip, port) in JupyterHub >= 0.7")
            if spawner.api_token != api_token:
                # Spawner re-used an API token, discard the unused api_token
                orm_token = orm.APIToken.find(self.db, api_token)
                if orm_token is not None:
                    self.db.delete(orm_token)
                    self.db.commit()
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
            raise e
        spawner.start_polling()

        # store state
        self.state = spawner.get_state()
        self.last_activity = datetime.utcnow()
        db.commit()
        self.waiting_for_response = True
        try:
            yield self.server.wait_up(http=True, timeout=spawner.http_timeout)
        except Exception as e:
            if isinstance(e, TimeoutError):
                self.log.warning(
                    "{user}'s server never showed up at {url} "
                    "after {http_timeout} seconds. Giving up".format(
                        user=self.name,
                        url=self.server.url,
                        http_timeout=spawner.http_timeout,
                    )
                )
                e.reason = 'timeout'
            else:
                e.reason = 'error'
                self.log.error("Unhandled error waiting for {user}'s server to show up at {url}: {error}".format(
                    user=self.name, url=self.server.url, error=e,
                ))
            try:
                yield self.stop()
            except Exception:
                self.log.error("Failed to cleanup {user}'s server that failed to start".format(
                    user=self.name,
                ), exc_info=True)
            # raise original TimeoutError
            raise e
        finally:
            self.waiting_for_response = False
            self.spawn_pending = False
        return self

    @gen.coroutine
    def stop(self):
        """Stop the user's spawner

        and cleanup after it.
        """
        self.spawn_pending = False
        spawner = self.spawner
        self.spawner.stop_polling()
        self.stop_pending = True
        try:
            api_token = self.spawner.api_token
            status = yield spawner.poll()
            if status is None:
                yield self.spawner.stop()
            spawner.clear_state()
            self.state = spawner.get_state()
            self.last_activity = datetime.utcnow()
            # Cleanup defunct servers: delete entry and API token for each server
            for server in self.servers:
                # remove server entry from db
                self.db.delete(server)
            if not spawner.will_resume:
                # find and remove the API token if the spawner isn't
                # going to re-use it next time
                orm_token = orm.APIToken.find(self.db, api_token)
                if orm_token:
                    self.db.delete(orm_token)
            self.db.commit()
        finally:
            self.stop_pending = False
            # trigger post-spawner hook on authenticator
            auth = spawner.authenticator
            if auth:
                yield gen.maybe_future(
                    auth.post_spawn_stop(self, spawner)
                )
