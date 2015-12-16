# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from datetime import datetime, timedelta
from urllib.parse import quote

from tornado import gen
from tornado.log import app_log

from sqlalchemy import inspect

from .utils import url_path_join

from . import orm
from traitlets import HasTraits, Any

class UserDict(dict):
    """Like defaultdict, but for users
    
    Getting by a user id OR an orm.User instance returns a User wrapper around the orm user.
    """
    def __init__(self, db_factory):
        self.db_factory = db_factory
        super().__init__()
    
    @property
    def db(self):
        return self.db_factory()
    
    def __getitem__(self, key):
        if isinstance(key, orm.User):
            # users[orm_user] returns User(orm_user)
            orm_user = key
            if orm_user.id not in self:
                user = self[orm_user.id] = User(orm_user)
                return user
            user = dict.__getitem__(self, orm_user.id)
            user.db = self.db
            return user
        elif isinstance(key, int):
            id = key
            if id not in self:
                orm_user = self.db.query(orm.User).filter(orm.User.id==id).first()
                if orm_user is None:
                    raise KeyError("No such user: %s" % id)
                user = self[id] = User(orm_user)
            return dict.__getitem__(self, id)
        else:
            raise KeyError(repr(key))


class User(HasTraits):
    
    def _log_default(self):
        return app_log
    
    db = Any(allow_none=True)
    def _db_default(self):
        if self.orm_user:
            return inspect(self.orm_user).session
    
    def _db_changed(self, name, old, new):
        """Changing db session reacquires ORM User object"""
        # db session changed, re-get orm User
        if self.orm_user:
            id = self.orm_user.id
            self.orm_user = new.query(orm.User).filter(orm.User.id==id).first()
    
    orm_user = None
    spawner = None
    spawn_pending = False
    stop_pending = False
    
    def __init__(self, orm_user, **kwargs):
        self.orm_user = orm_user
        super().__init__(**kwargs)
    
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
        if self.spawner is None:
            return False
        if self.server is None:
            return False
        return True
    
    @property
    def escaped_name(self):
        """My name, escaped for use in URLs, cookies, etc."""
        return quote(self.name, safe='@')
    
    @gen.coroutine
    def spawn(self, spawner_class, base_url='/', hub=None, config=None,
              authenticator=None, options=None):
        """Start the user's spawner"""
        db = self.db
        if hub is None:
            hub = db.query(orm.Hub).first()
        
        self.server = orm.Server(
            cookie_name='%s-%s' % (hub.server.cookie_name, quote(self.name, safe='')),
            base_url=url_path_join(base_url, 'user', self.escaped_name),
        )
        db.add(self.server)
        db.commit()
        
        api_token = self.new_api_token()
        db.commit()
        
        spawner = self.spawner = spawner_class(
            config=config,
            user=self,
            hub=hub,
            db=db,
            authenticator=authenticator,
            user_options=options or {},
        )
        # we are starting a new server, make sure it doesn't restore state
        spawner.clear_state()
        spawner.api_token = api_token

        # trigger pre-spawn hook on authenticator
        if (authenticator):
            yield gen.maybe_future(authenticator.pre_spawn_start(self, spawner))

        self.spawn_pending = True
        # wait for spawner.start to return
        try:
            f = spawner.start()
            yield gen.with_timeout(timedelta(seconds=spawner.start_timeout), f)
        except Exception as e:
            if isinstance(e, gen.TimeoutError):
                self.log.warn("{user}'s server failed to start in {s} seconds, giving up".format(
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
        try:
            yield self.server.wait_up(http=True, timeout=spawner.http_timeout)
        except Exception as e:
            if isinstance(e, TimeoutError):
                self.log.warn(
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
        self.spawn_pending = False
        return self

    @gen.coroutine
    def stop(self):
        """Stop the user's spawner
        
        and cleanup after it.
        """
        self.spawn_pending = False
        spawner = self.spawner
        if spawner is None:
            return
        self.spawner.stop_polling()
        self.stop_pending = True
        try:
            status = yield spawner.poll()
            if status is None:
                yield self.spawner.stop()
            spawner.clear_state()
            self.state = spawner.get_state()
            self.last_activity = datetime.utcnow()
            self.server = None
            self.db.commit()
        finally:
            self.stop_pending = False
            # trigger post-spawner hook on authenticator
            auth = spawner.authenticator
            if auth:
                yield gen.maybe_future(
                    auth.post_spawn_stop(self, spawner)
                )

