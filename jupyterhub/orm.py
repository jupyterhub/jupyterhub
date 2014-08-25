"""sqlalchemy ORM tools for the state of the constellation of processes"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json
import uuid

from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Unicode, Binary,
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import create_engine

from IPython.utils.py3compat import str_to_unicode

from .utils import random_port, url_path_join


def new_token(*args, **kwargs):
    """generator for new random tokens
    
    For now, just UUIDs.
    """
    return str_to_unicode(uuid.uuid4().hex)


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
    cookie_secret = Column(Binary, default=b'secret')
    cookie_name = Column(Unicode, default=u'cookie')
    
    def __repr__(self):
        return "<Server(%s:%s)>" % (self.ip, self.port)
    
    @property
    def host(self):
        return "{proto}://{ip}:{port}".format(
            proto=self.proto,
            ip=self.ip,
            port=self.port,
        )
    
    @property
    def url(self):
        return "{host}{uri}".format(
            host=self.host,
            uri=self.base_url,
        )


class Proxy(Base):
    """A configurable-http-proxy instance.
    
    A proxy consists of the API server info and the public-facing server info,
    plus an auth token for configuring the proxy table.
    """
    __tablename__ = 'proxies'
    id = Column(Integer, primary_key=True)
    auth_token = Column(Unicode, default=new_token)
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
        assert self.id is not None
        return cls(token=new_token(), user_id=self.id)
    
    def new_api_token(self):
        """Return a new API token"""
        return self._new_token(APIToken)
    
    def new_cookie_token(self):
        """Return a new cookie token"""
        return self._new_token(CookieToken)


class Token(object):
    """Mixin for token tables, since we have two"""
    token = Column(String, primary_key=True)
    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('users.id'))
    
    def __repr__(self):
        return "<{cls}('{t}', user='{u}')>".format(
            cls=self.__class__.__name__,
            t=self.token,
            u=self.user.name,
        )


class APIToken(Token, Base):
    """An API token"""
    __tablename__ = 'api_tokens'


class CookieToken(Token, Base):
    """A cookie token"""
    __tablename__ = 'cookie_tokens'


def new_session(url="sqlite:///:memory:", **kwargs):
    """Create a new session at url"""
    engine = create_engine(url, **kwargs)
    Session = sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(engine)
    return session


