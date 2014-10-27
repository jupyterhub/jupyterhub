"""sqlalchemy ORM tools for the state of the constellation of processes"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from datetime import datetime
import errno
import json
import socket
import uuid

from six import text_type

from tornado import gen
from tornado.log import app_log
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError

from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy import (
    inspect,
    Column, Integer, ForeignKey, Unicode, Binary, Boolean,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy_utils.types import PasswordType

from .utils import random_port, url_path_join, wait_for_server, wait_for_http_server


def new_token(*args, **kwargs):
    """generator for new random tokens
    
    For now, just UUIDs.
    """
    return text_type(uuid.uuid4().hex)

PASSWORD_SCHEMES = ['pbkdf2_sha512']

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


class Server(Base):
    """The basic state of a server
    
    connection and cookie info
    """
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True)
    proto = Column(Unicode, default=u'http')
    ip = Column(Unicode, default=u'localhost')
    port = Column(Integer, default=random_port)
    base_url = Column(Unicode, default=u'/')
    cookie_name = Column(Unicode, default=u'cookie')
    
    def __repr__(self):
        return "<Server(%s:%s)>" % (self.ip, self.port)
    
    @property
    def host(self):
        return "{proto}://{ip}:{port}".format(
            proto=self.proto,
            ip=self.ip or '*',
            port=self.port,
        )
    
    @property
    def url(self):
        return "{host}{uri}".format(
            host=self.host,
            uri=self.base_url,
        )
    
    @gen.coroutine
    def wait_up(self, timeout=10, http=False):
        """Wait for this server to come up"""
        if http:
            yield wait_for_http_server(self.url.replace('//*', '//localhost'), timeout=timeout)
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
    log = app_log
    
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
        raise gen.Return(json.loads(resp.body.decode('utf8', 'replace')))


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
    These are used by single-user servers to authenticate requests.
    
    Cookie tokens are used to authenticate browser sessions.
    
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
    cookie_tokens = relationship("CookieToken", backref="user")
    state = Column(JSONDict)
    spawner = None
    
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
    
    def _new_token(self, cls):
        """Create a new API or Cookie token"""
        assert self.id is not None
        db = inspect(self).session
        token = new_token()
        orm_token = cls(user_id=self.id)
        orm_token.token = token
        db.add(orm_token)
        db.commit()
        return token
    
    def new_api_token(self):
        """Return a new API token"""
        return self._new_token(APIToken)
    
    def new_cookie_token(self):
        """Return a new cookie token"""
        return self._new_token(CookieToken)

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
            cookie_name='%s-%s' % (hub.server.cookie_name, self.name),
            base_url=url_path_join(base_url, 'user', self.name),
        )
        db.add(self.server)
        db.commit()

        api_token = self.new_api_token()
        db.commit()
        
        
        spawner = self.spawner = spawner_class(
            config=config,
            user=self,
            hub=hub,
        )
        # we are starting a new server, make sure it doesn't restore state
        spawner.clear_state()
        spawner.api_token = api_token
        
        yield spawner.start()
        spawner.start_polling()

        # store state
        self.state = spawner.get_state()
        self.last_activity = datetime.utcnow()
        db.commit()
        
        yield self.server.wait_up(http=True)
        raise gen.Return(self)

    @gen.coroutine
    def stop(self):
        """Stop the user's spawner
        
        and cleanup after it.
        """
        if self.spawner is None:
            return
        self.spawner.stop_polling()
        status = yield self.spawner.poll()
        if status is None:
            yield self.spawner.stop()
        self.spawner.clear_state()
        self.state = self.spawner.get_state()
        self.last_activity = datetime.utcnow()
        self.server = None
        inspect(self).session.commit()


class Token(object):
    """Mixin for token tables, since we have two"""
    id = Column(Integer, primary_key=True)
    hashed = Column(PasswordType(schemes=PASSWORD_SCHEMES))
    prefix = Column(Unicode)
    prefix_length = 4
    _token = None
    
    @property
    def token(self):
        """plaintext tokens will only be accessible for tokens created during this session"""
        return self._token
    
    @token.setter
    def token(self, token):
        """Store the hashed value and prefix for a token"""
        self.prefix = token[:self.prefix_length]
        self.hashed = token
        self._token = token
    
    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('users.id'))
    
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
        prefix_match = db.query(cls).filter(cls.prefix==prefix)
        for orm_token in prefix_match:
            if orm_token.hashed == token:
                return orm_token


class APIToken(Token, Base):
    """An API token"""
    __tablename__ = 'api_tokens'


class CookieToken(Token, Base):
    """A cookie token"""
    __tablename__ = 'cookie_tokens'


def new_session(url="sqlite:///:memory:", reset=False, **kwargs):
    """Create a new session at url"""
    if url.startswith('sqlite'):
        kwargs.setdefault('connect_args', {'check_same_thread': False})
    kwargs.setdefault('poolclass', StaticPool)
    engine = create_engine(url, **kwargs)
    Session = sessionmaker(bind=engine)
    session = Session()
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return session


