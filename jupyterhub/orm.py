"""sqlalchemy ORM tools for the state of the constellation of processes"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from datetime import datetime, timedelta
import errno
import json
import socket
from urllib.parse import quote

from tornado import gen
from tornado.log import app_log
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError

from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy import (
    inspect,
    Column, Integer, ForeignKey, Unicode, Boolean,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.expression import bindparam
from sqlalchemy import create_engine

from .utils import (
    random_port, url_path_join, wait_for_server, wait_for_http_server,
    new_token, hash_token, compare_token,
)


class JSONDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Usage::

        JSONEncodedDict(255)

    """

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


Base = declarative_base()
Base.log = app_log


class Server(Base):
    """The basic state of a server
    
    connection and cookie info
    """
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True)
    proto = Column(Unicode, default='http')
    ip = Column(Unicode, default='')
    port = Column(Integer, default=random_port)
    base_url = Column(Unicode, default='/')
    cookie_name = Column(Unicode, default='cookie')
    
    def __repr__(self):
        return "<Server(%s:%s)>" % (self.ip, self.port)
    
    @property
    def host(self):
        ip = self.ip
        if ip in {'', '0.0.0.0'}:
            # when listening on all interfaces, connect to localhost
            ip = 'localhost'
        return "{proto}://{ip}:{port}".format(
            proto=self.proto,
            ip=ip,
            port=self.port,
        )

    @property
    def url(self):
        return "{host}{uri}".format(
            host=self.host,
            uri=self.base_url,
        )
    
    @property
    def bind_url(self):
        """representation of URL used for binding
        
        Never used in APIs, only logging,
        since it can be non-connectable value, such as '', meaning all interfaces.
        """
        if self.ip in {'', '0.0.0.0'}:
            return self.url.replace('localhost', self.ip or '*', 1)
        return self.url
    
    @gen.coroutine
    def wait_up(self, timeout=10, http=False):
        """Wait for this server to come up"""
        if http:
            yield wait_for_http_server(self.url, timeout=timeout)
        else:
            yield wait_for_server(self.ip or 'localhost', self.port, timeout=timeout)
    
    def is_up(self):
        """Is the server accepting connections?"""
        try:
            socket.create_connection((self.ip or 'localhost', self.port))
        except socket.error as e:
            if e.errno == errno.ECONNREFUSED:
                return False
            else:
                raise
        else:
            return True


class Proxy(Base):
    """A configurable-http-proxy instance.
    
    A proxy consists of the API server info and the public-facing server info,
    plus an auth token for configuring the proxy table.
    """
    __tablename__ = 'proxies'
    id = Column(Integer, primary_key=True)
    auth_token = None
    _public_server_id = Column(Integer, ForeignKey('servers.id'))
    public_server = relationship(Server, primaryjoin=_public_server_id == Server.id)
    _api_server_id = Column(Integer, ForeignKey('servers.id'))
    api_server = relationship(Server, primaryjoin=_api_server_id == Server.id)
    
    def __repr__(self):
        if self.public_server:
            return "<%s %s:%s>" % (
                self.__class__.__name__, self.public_server.ip, self.public_server.port,
            )
        else:
            return "<%s [unconfigured]>" % self.__class__.__name__
    
    def api_request(self, path, method='GET', body=None, client=None):
        """Make an authenticated API request of the proxy"""
        client = client or AsyncHTTPClient()
        url = url_path_join(self.api_server.url, path)

        if isinstance(body, dict):
            body = json.dumps(body)
        self.log.debug("Fetching %s %s", method, url)
        req = HTTPRequest(url,
            method=method,
            headers={'Authorization': 'token {}'.format(self.auth_token)},
            body=body,
        )

        return client.fetch(req)

    @gen.coroutine
    def add_user(self, user, client=None):
        """Add a user's server to the proxy table."""
        self.log.info("Adding user %s to proxy %s => %s",
            user.name, user.server.base_url, user.server.host,
        )
        
        yield self.api_request(user.server.base_url,
            method='POST',
            body=dict(
                target=user.server.host,
                user=user.name,
            ),
            client=client,
        )
    
    @gen.coroutine
    def delete_user(self, user, client=None):
        """Remove a user's server to the proxy table."""
        self.log.info("Removing user %s from proxy", user.name)
        yield self.api_request(user.server.base_url,
            method='DELETE',
            client=client,
        )
    
    @gen.coroutine
    def add_all_users(self):
        """Update the proxy table from the database.
        
        Used when loading up a new proxy.
        """
        db = inspect(self).session
        futures = []
        for user in db.query(User):
            if (user.server):
                futures.append(self.add_user(user))
        # wait after submitting them all
        for f in futures:
            yield f

    @gen.coroutine
    def get_routes(self, client=None):
        """Fetch the proxy's routes"""
        resp = yield self.api_request('', client=client)
        return json.loads(resp.body.decode('utf8', 'replace'))

    @gen.coroutine
    def check_routes(self, routes=None):
        """Check that all users are properly"""
        if not routes:
            routes = yield self.get_routes()

        have_routes = { r['user'] for r in routes.values() if 'user' in r }
        futures = []
        db = inspect(self).session
        for user in db.query(User).filter(User.server != None):
            if user.name not in have_routes:
                self.log.warn("Adding missing route for %s", user.name)
                futures.append(self.add_user(user))
        for f in futures:
            yield f



class Hub(Base):
    """Bring it all together at the hub.
    
    The Hub is a server, plus its API path suffix
    
    the api_url is the full URL plus the api_path suffix on the end
    of the server base_url.
    """
    __tablename__ = 'hubs'
    id = Column(Integer, primary_key=True)
    _server_id = Column(Integer, ForeignKey('servers.id'))
    server = relationship(Server, primaryjoin=_server_id == Server.id)
    
    @property
    def api_url(self):
        """return the full API url (with proto://host...)"""
        return url_path_join(self.server.url, 'api')
    
    def __repr__(self):
        if self.server:
            return "<%s %s:%s>" % (
                self.__class__.__name__, self.server.ip, self.server.port,
            )
        else:
            return "<%s [unconfigured]>" % self.__class__.__name__


class User(Base):
    """The User table
    
    Each user has a single server,
    and multiple tokens used for authorization.
    
    API tokens grant access to the Hub's REST API.
    These are used by single-user servers to authenticate requests,
    and external services to manipulate the Hub.
    
    Cookies are set with a single ID.
    Resetting the Cookie ID invalidates all cookies, forcing user to login again.
    
    A `state` column contains a JSON dict,
    used for restoring state of a Spawner.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode)
    # should we allow multiple servers per user?
    _server_id = Column(Integer, ForeignKey('servers.id'))
    server = relationship(Server, primaryjoin=_server_id == Server.id)
    admin = Column(Boolean, default=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    api_tokens = relationship("APIToken", backref="user")
    cookie_id = Column(Unicode, default=new_token)
    state = Column(JSONDict)
    spawner = None
    spawn_pending = False
    stop_pending = False

    other_user_cookies = set([])
    
    def __repr__(self):
        if self.server:
            return "<{cls}({name}@{ip}:{port})>".format(
                cls=self.__class__.__name__,
                name=self.name,
                ip=self.server.ip,
                port=self.server.port,
            )
        else:
            return "<{cls}({name} [unconfigured])>".format(
                cls=self.__class__.__name__,
                name=self.name,
            )
    
    @property
    def escaped_name(self):
        """My name, escaped for use in URLs, cookies, etc."""
        return quote(self.name, safe='@')
    
    @property
    def running(self):
        """property for whether a user has a running server"""
        if self.spawner is None:
            return False
        if self.server is None:
            return False
        return True
    
    def new_api_token(self):
        """Create a new API token"""
        assert self.id is not None
        db = inspect(self).session
        token = new_token()
        orm_token = APIToken(user_id=self.id)
        orm_token.token = token
        db.add(orm_token)
        db.commit()
        return token
    
    @classmethod
    def find(cls, db, name):
        """Find a user by name.

        Returns None if not found.
        """
        return db.query(cls).filter(cls.name==name).first()
    
    @gen.coroutine
    def spawn(self, spawner_class, base_url='/', hub=None, config=None):
        """Start the user's spawner"""
        db = inspect(self).session
        if hub is None:
            hub = db.query(Hub).first()
        
        self.server = Server(
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
        )
        # we are starting a new server, make sure it doesn't restore state
        spawner.clear_state()
        spawner.api_token = api_token
        
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
        if self.spawner is None:
            return
        self.spawner.stop_polling()
        self.stop_pending = True
        try:
            status = yield self.spawner.poll()
            if status is None:
                yield self.spawner.stop()
            self.spawner.clear_state()
            self.state = self.spawner.get_state()
            self.server = None
            inspect(self).session.commit()
        finally:
            self.stop_pending = False


class APIToken(Base):
    """An API token"""
    __tablename__ = 'api_tokens'
    
    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('users.id'))

    id = Column(Integer, primary_key=True)
    hashed = Column(Unicode)
    prefix = Column(Unicode)
    prefix_length = 4
    algorithm = "sha512"
    rounds = 16384
    salt_bytes = 8
    
    @property
    def token(self):
        raise AttributeError("token is write-only")
    
    @token.setter
    def token(self, token):
        """Store the hashed value and prefix for a token"""
        self.prefix = token[:self.prefix_length]
        self.hashed = hash_token(token, rounds=self.rounds, salt=self.salt_bytes, algorithm=self.algorithm)
    
    def __repr__(self):
        return "<{cls}('{pre}...', user='{u}')>".format(
            cls=self.__class__.__name__,
            pre=self.prefix,
            u=self.user.name,
        )

    @classmethod
    def find(cls, db, token):
        """Find a token object by value.

        Returns None if not found.
        """
        prefix = token[:cls.prefix_length]
        # since we can't filter on hashed values, filter on prefix
        # so we aren't comparing with all tokens
        prefix_match = db.query(cls).filter(bindparam('prefix', prefix).startswith(cls.prefix))
        for orm_token in prefix_match:
            if orm_token.match(token):
                return orm_token
    
    def match(self, token):
        """Is this my token?"""
        return compare_token(self.hashed, token)


def new_session_factory(url="sqlite:///:memory:", reset=False, **kwargs):
    """Create a new session at url"""
    if url.startswith('sqlite'):
        kwargs.setdefault('connect_args', {'check_same_thread': False})

    if url.endswith(':memory:'):
        # If we're using an in-memory database, ensure that only one connection
        # is ever created.
        kwargs.setdefault('poolclass', StaticPool)

    engine = create_engine(url, **kwargs)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    return session_factory
