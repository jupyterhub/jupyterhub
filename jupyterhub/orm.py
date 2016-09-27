"""sqlalchemy ORM tools for the state of the constellation of processes"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from datetime import datetime
import json

from tornado import gen
from tornado.log import app_log
from tornado.httpclient import HTTPRequest, AsyncHTTPClient

from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy import (
    inspect,
    Column, Integer, ForeignKey, Unicode, Boolean,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.expression import bindparam
from sqlalchemy import create_engine, Table

from .utils import (
    random_port, url_path_join, wait_for_server, wait_for_http_server,
    new_token, hash_token, compare_token, can_connect,
)


class JSONDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Usage::

        JSONEncodedDict(255)

    """

    impl = TEXT

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
    proto = Column(Unicode(15), default='http')
    ip = Column(Unicode(255), default='')  # could also be a DNS name
    port = Column(Integer, default=random_port)
    base_url = Column(Unicode(255), default='/')
    cookie_name = Column(Unicode(255), default='cookie')

    def __repr__(self):
        return "<Server(%s:%s)>" % (self.ip, self.port)

    @property
    def host(self):
        ip = self.ip
        if ip in {'', '0.0.0.0'}:
            # when listening on all interfaces, connect to localhost
            ip = '127.0.0.1'
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
            return self.url.replace('127.0.0.1', self.ip or '*', 1)
        return self.url

    @gen.coroutine
    def wait_up(self, timeout=10, http=False):
        """Wait for this server to come up"""
        if http:
            yield wait_for_http_server(self.url, timeout=timeout)
        else:
            yield wait_for_server(self.ip or '127.0.0.1', self.port, timeout=timeout)

    def is_up(self):
        """Is the server accepting connections?"""
        return can_connect(self.ip or '127.0.0.1', self.port)


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
    def add_service(self, service, client=None):
        """Add a service's server to the proxy table."""
        if not service.server:
            raise RuntimeError(
                "Service %s does not have an http endpoint to add to the proxy.", service.name)

        self.log.info("Adding service %s to proxy %s => %s",
            service.name, service.proxy_path, service.server.host,
        )

        yield self.api_request(service.proxy_path,
            method='POST',
            body=dict(
                target=service.server.host,
                service=service.name,
            ),
            client=client,
        )

    @gen.coroutine
    def delete_service(self, service, client=None):
        """Remove a service's server from the proxy table."""
        self.log.info("Removing service %s from proxy", service.name)
        yield self.api_request(service.proxy_path,
            method='DELETE',
            client=client,
        )

    @gen.coroutine
    def add_user(self, user, client=None):
        """Add a user's server to the proxy table."""
        self.log.info("Adding user %s to proxy %s => %s",
            user.name, user.proxy_path, user.server.host,
        )

        if user.spawn_pending:
            raise RuntimeError(
                "User %s's spawn is pending, shouldn't be added to the proxy yet!", user.name)

        yield self.api_request(user.proxy_path,
            method='POST',
            body=dict(
                target=user.server.host,
                user=user.name,
            ),
            client=client,
        )

    @gen.coroutine
    def delete_user(self, user, client=None):
        """Remove a user's server from the proxy table."""
        self.log.info("Removing user %s from proxy", user.name)
        yield self.api_request(user.proxy_path,
            method='DELETE',
            client=client,
        )

    @gen.coroutine
    def add_all_services(self, service_dict):
        """Update the proxy table from the database.

        Used when loading up a new proxy.
        """
        db = inspect(self).session
        futures = []
        for orm_service in db.query(Service):
            service = service_dict[orm_service.name]
            if service.server:
                futures.append(self.add_service(service))
        # wait after submitting them all
        for f in futures:
            yield f

    @gen.coroutine
    def add_all_users(self, user_dict):
        """Update the proxy table from the database.

        Used when loading up a new proxy.
        """
        db = inspect(self).session
        futures = []
        for orm_user in db.query(User):
            user = user_dict[orm_user]
            if user.running:
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
    def check_routes(self, user_dict, service_dict, routes=None):
        """Check that all users are properly routed on the proxy"""
        if not routes:
            routes = yield self.get_routes()

        user_routes = { r['user'] for r in routes.values() if 'user' in r }
        futures = []
        db = inspect(self).session
        for orm_user in db.query(User):
            user = user_dict[orm_user]
            if user.running:
                if user.name not in user_routes:
                    self.log.warning("Adding missing route for %s (%s)", user.name, user.server)
                    futures.append(self.add_user(user))
            else:
                # User not running, make sure it's not in the table
                if user.name in user_routes:
                    self.log.warning("Removing route for not running %s", user.name)
                    futures.append(self.delete_user(user))
        
        # check service routes
        service_routes = { r['service'] for r in routes.values() if 'service' in r }
        for orm_service in db.query(Service).filter(Service.server != None):
            service = service_dict[orm_service.name]
            if service.server is None:
                # This should never be True, but seems to be on rare occasion.
                # catch filter bug, either in sqlalchemy or my understanding of its behavior
                self.log.error("Service %s has no server, but wasn't filtered out.", service)
                continue
            if service.name not in service_routes:
                self.log.warning("Adding missing route for %s (%s)", service.name, service.server)
                futures.append(self.add_service(service))
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
    host = ''

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


# user:group many:many mapping table
user_group_map = Table('user_group_map', Base.metadata,
    Column('user_id', ForeignKey('users.id'), primary_key=True),
    Column('group_id', ForeignKey('groups.id'), primary_key=True),
)

class Group(Base):
    """User Groups"""
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(1023), unique=True)
    users = relationship('User', secondary='user_group_map', back_populates='groups')
    
    def __repr__(self):
        return "<%s %s (%i users)>" % (
            self.__class__.__name__, self.name, len(self.users)
        )
    @classmethod
    def find(cls, db, name):
        """Find a group by name.

        Returns None if not found.
        """
        return db.query(cls).filter(cls.name==name).first()


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
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(1023), unique=True)
    # should we allow multiple servers per user?
    _server_id = Column(Integer, ForeignKey('servers.id', ondelete="SET NULL"))
    server = relationship(Server, primaryjoin=_server_id == Server.id)
    admin = Column(Boolean, default=False)
    last_activity = Column(DateTime, default=datetime.utcnow)

    api_tokens = relationship("APIToken", backref="user")
    cookie_id = Column(Unicode(1023), default=new_token)
    # User.state is actually Spawner state
    # We will need to figure something else out if/when we have multiple spawners per user
    state = Column(JSONDict)
    # Authenticators can store their state here:
    auth_state = Column(JSONDict)
    # group mapping
    groups = relationship('Group', secondary='user_group_map', back_populates='users')

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

    def new_api_token(self, token=None):
        """Create a new API token
        
        If `token` is given, load that token.
        """
        return APIToken.new(token=token, user=self)

    @classmethod
    def find(cls, db, name):
        """Find a user by name.

        Returns None if not found.
        """
        return db.query(cls).filter(cls.name==name).first()


class Service(Base):
    """A service run with JupyterHub

    A service is similar to a User without a Spawner.
    A service can have API tokens for accessing the Hub's API

    It has:

    - name
    - admin
    - api tokens
    - server (if proxied http endpoint)

    In addition to what it has in common with users, a Service has extra info:

    - pid: the process id (if managed)

    """
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # common user interface:
    name = Column(Unicode(1023), unique=True)
    admin = Column(Boolean, default=False)

    api_tokens = relationship("APIToken", backref="service")

    # service-specific interface
    _server_id = Column(Integer, ForeignKey('servers.id'))
    server = relationship(Server, primaryjoin=_server_id == Server.id)
    pid = Column(Integer)

    def new_api_token(self, token=None):
        """Create a new API token

        If `token` is given, load that token.
        """
        return APIToken.new(token=token, service=self)
    
    @classmethod
    def find(cls, db, name):
        """Find a service by name.

        Returns None if not found.
        """
        return db.query(cls).filter(cls.name==name).first()


class APIToken(Base):
    """An API token"""
    __tablename__ = 'api_tokens'
    
    # _constraint = ForeignKeyConstraint(['user_id', 'server_id'], ['users.id', 'services.id'])
    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True)

    @declared_attr
    def service_id(cls):
        return Column(Integer, ForeignKey('services.id', ondelete="CASCADE"), nullable=True)

    id = Column(Integer, primary_key=True)
    hashed = Column(Unicode(1023))
    prefix = Column(Unicode(1023))
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
        if self.user is not None:
            kind = 'user'
            name = self.user.name
        elif self.service is not None:
            kind = 'service'
            name = self.service.name
        else:
            # this shouldn't happen
            kind = 'owner'
            name = 'unknown'
        return "<{cls}('{pre}...', {kind}='{name}')>".format(
            cls=self.__class__.__name__,
            pre=self.prefix,
            kind=kind,
            name=name,
        )

    @classmethod
    def find(cls, db, token, *, kind=None):
        """Find a token object by value.

        Returns None if not found.
        
        `kind='user'` only returns API tokens for users
        `kind='service'` only returns API tokens for services
        """
        prefix = token[:cls.prefix_length]
        # since we can't filter on hashed values, filter on prefix
        # so we aren't comparing with all tokens
        prefix_match = db.query(cls).filter(bindparam('prefix', prefix).startswith(cls.prefix))
        if kind == 'user':
            prefix_match = prefix_match.filter(cls.user_id != None)
        elif kind == 'service':
            prefix_match = prefix_match.filter(cls.service_id != None)
        elif kind is not None:
            raise ValueError("kind must be 'user', 'service', or None, not %r" % kind)
        for orm_token in prefix_match:
            if orm_token.match(token):
                return orm_token

    def match(self, token):
        """Is this my token?"""
        return compare_token(self.hashed, token)

    @classmethod
    def new(cls, token=None, user=None, service=None):
        """Generate a new API token for a user or service"""
        assert user or service
        assert not (user and service)
        db = inspect(user or service).session
        if token is None:
            token = new_token()
        else:
            if len(token) < 8:
                raise ValueError("Tokens must be at least 8 characters, got %r" % token)
            found = APIToken.find(db, token)
            if found:
                raise ValueError("Collision on token: %s..." % token[:4])
        orm_token = APIToken(token=token)
        if user:
            assert user.id is not None
            orm_token.user_id = user.id
        else:
            assert service.id is not None
            orm_token.service_id = service.id
        db.add(orm_token)
        db.commit()
        return token


def new_session_factory(url="sqlite:///:memory:", reset=False, **kwargs):
    """Create a new session at url"""
    if url.startswith('sqlite'):
        kwargs.setdefault('connect_args', {'check_same_thread': False})
    elif url.startswith('mysql'):
        kwargs.setdefault('pool_recycle', 60)

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
