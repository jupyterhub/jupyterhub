"""sqlalchemy ORM tools for the state of the constellation of processes"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import base64
from datetime import datetime
import enum
import os
import json

try:
    import cryptography
except ImportError:
    cryptography = None

from tornado.log import app_log

from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy import (
    inspect,
    Column, Integer, ForeignKey, Unicode, Boolean,
    DateTime, Enum
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.expression import bindparam
from sqlalchemy_utils.types.encrypted import EncryptedType, FernetEngine
from sqlalchemy import create_engine, Table

from traitlets import HasTraits, List

from .utils import (
    random_port,
    new_token, hash_token, compare_token,
)


class JSONDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Usage::

        JSONDict(255)

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


def _fernet_key(key):
    """Generate a Fernet key from a secret
    
    Will always be 32 bytes (via sha256), url-safe base64-encoded,
    per fernet spec.
    """
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    if isinstance(key, str):
        key = key.encode()
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(key)
    return base64.urlsafe_b64encode(digest.finalize())


class MultiFernetEngine(FernetEngine):
    """Extend SQLAlchemy-Utils FernetEngine to use MultiFernet,

    which supports key rotation.
    """
    key_list = None

    def _update_key(self, key):
        if key == self.key_list:
            return
        return self._initialize_engine(key)

    def _initialize_engine(self, parent_class_key):
        from cryptography.fernet import MultiFernet, Fernet
        # key will be a *list* of keys
        self.key_list = parent_class_key
        self.fernet = MultiFernet([Fernet(_fernet_key(key)) for key in self.key_list])

class EncryptionUnavailable(Exception):
    pass

class EncryptionConfig(HasTraits):
    """Encapsulate encryption configuration
    
    Use via the encryption_config singleton below.
    """
    key_list = List()
    def _key_list_default(self):
        if 'AUTH_STATE_KEY' not in os.environ:
            return []
        # key can be a ;-separated sequence for key rotation.
        # First item in the list is used for encryption.
        return os.environ['AUTH_STATE_KEY'].split(';')

    @property
    def available(self):
        if not self.key_list:
            return False
        return cryptography is not None

encryption_config = EncryptionConfig()

class Encrypted(EncryptedType):
    def __init__(self, type_in=None, key=None, **kwargs):
        super().__init__(type_in, key=lambda : encryption_config.key_list, engine=MultiFernetEngine, **kwargs)


class CantEncrypt(TypeDecorator):
    """Use in place of Encrypted when Encrypted types can't even be instantiated (crypto unavailable)"""
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        raise EncryptionUnavailable("cryptography library is unavailable")

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        raise EncryptionUnavailable("cryptography library is unavailable")


# if cryptography library is unavailable, use CantEncrypt
if cryptography is None:
    Encrypted = CantEncrypt

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

    # added to handle multi-server feature
    last_activity = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return "<Server(%s:%s)>" % (self.ip, self.port)


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
        return db.query(cls).filter(cls.name == name).first()


class User(Base):
    """The User table

    Each user can have one or more single user notebook servers.

    Each single user notebook server will have a unique token for authorization.
    Therefore, a user with multiple notebook servers will have multiple tokens.

    API tokens grant access to the Hub's REST API.
    These are used by single-user servers to authenticate requests,
    and external services to manipulate the Hub.

    Cookies are set with a single ID.
    Resetting the Cookie ID invalidates all cookies, forcing user to login again.

    A `state` column contains a JSON dict,
    used for restoring state of a Spawner.


    `servers` is a list that contains a reference for each of the user's single user notebook servers.
    The method `server` returns the first entry in the user's `servers` list.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(1023), unique=True)

    _orm_spawners = relationship("Spawner", backref="user")
    @property
    def orm_spawners(self):
        return {s.name: s for s in self._orm_spawners}

    admin = Column(Boolean, default=False)
    last_activity = Column(DateTime, default=datetime.utcnow)

    api_tokens = relationship("APIToken", backref="user")
    cookie_id = Column(Unicode(1023), default=new_token, nullable=False, unique=True)
    # User.state is actually Spawner state
    # We will need to figure something else out if/when we have multiple spawners per user
    state = Column(JSONDict)
    # Authenticators can store their state here:
    _auth_state = Column('auth_state', Encrypted(JSONDict))
    
    # check for availability of encryption on a property
    # to get better errors than raising in the TypeDecorator methods,
    # which won't raise until `db.commit()`

    @property
    def auth_state(self):
        # TODO: handle decryption failure
        try:
            value = self._auth_state
        except Exception as e:
            if encryption_config.available:
                why = str(e)
            else:
                why = "encryption is unavailable"
            app_log.warning("Failed to retrieve encrypted auth_state for %s because %s",
                self.name, why)
            return None
        if value is not None and not encryption_config.available:
            raise EncryptionUnavailable("auth_state requires cryptography library and AUTH_STATE_KEY")
        return value
    
    @auth_state.setter
    def auth_state(self, value):
        if value is None:
            self._auth_state = value
            return
        if value is not None and not encryption_config.available:
            raise EncryptionUnavailable("auth_state requires cryptography library and AUTH_STATE_KEY")
        self._auth_state = value

    # group mapping
    groups = relationship('Group', secondary='user_group_map', back_populates='users')

    def __repr__(self):
        return "<{cls}({name} {running}/{total} running)>".format(
            cls=self.__class__.__name__,
            name=self.name,
            total=len(self._orm_spawners),
            running=sum(bool(s.server) for s in self._orm_spawners),
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
        return db.query(cls).filter(cls.name == name).first()

class Spawner(Base):
    """"State about a Spawner"""
    __tablename__ = 'spawners'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))

    server_id = Column(Integer, ForeignKey('servers.id'))
    server = relationship(Server)

    state = Column(JSONDict)
    name = Column(Unicode(512))


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
        return db.query(cls).filter(cls.name == name).first()

class Hashed(object):
    """Mixin for tables with hashed tokens"""
    prefix_length = 4
    algorithm = "sha512"
    rounds = 16384
    salt_bytes = 8
    min_length = 8

    @property
    def token(self):
        raise AttributeError("token is write-only")

    @token.setter
    def token(self, token):
        """Store the hashed value and prefix for a token"""
        self.prefix = token[:self.prefix_length]
        if len(token) >= 32:
            # Tokens are generally UUIDs, which have sufficient entropy on their own
            # and don't need salt & hash rounds.
            # ref: https://security.stackexchange.com/a/151262/155114
            rounds = 1
            salt_bytes = b''
        else:
            # users can still specify API tokens in a few ways,
            # so trigger salt & hash rounds if they provide a short token
            app_log.warning("Applying salt & hash rounds to %sB token" % len(token))
            rounds = self.rounds
            salt_bytes = self.salt_bytes
        self.hashed = hash_token(token, rounds=rounds, salt=salt_bytes, algorithm=self.algorithm)

    def match(self, token):
        """Is this my token?"""
        return compare_token(self.hashed, token)
    
    @classmethod
    def check_token(cls, db, token):
        """Check if a token is acceptable"""
        if len(token) < cls.min_length:
            raise ValueError("Tokens must be at least %i characters, got %r" % (
                cls.min_length, token)
            )
        found = cls.find(db, token)
        if found:
            raise ValueError("Collision on token: %s..." % token[:cls.prefix_length])

    @classmethod
    def find_prefix(cls, db, token):
        """Start the query for matching token.
        
        Returns an SQLAlchemy query already filtered by prefix-matches.
        """
        prefix = token[:cls.prefix_length]
        # since we can't filter on hashed values, filter on prefix
        # so we aren't comparing with all tokens
        return db.query(cls).filter(bindparam('prefix', prefix).startswith(cls.prefix))

    @classmethod
    def find(cls, db, token):
        """Find a token object by value.

        Returns None if not found.

        `kind='user'` only returns API tokens for users
        `kind='service'` only returns API tokens for services
        """
        prefix_match = cls.find_prefix(db, token)
        for orm_token in prefix_match:
            if orm_token.match(token):
                return orm_token

class APIToken(Hashed, Base):
    """An API token"""
    __tablename__ = 'api_tokens'

    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True)

    @declared_attr
    def service_id(cls):
        return Column(Integer, ForeignKey('services.id', ondelete="CASCADE"), nullable=True)

    id = Column(Integer, primary_key=True)
    hashed = Column(Unicode(1023))
    prefix = Column(Unicode(16))

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
        prefix_match = cls.find_prefix(db, token)
        if kind == 'user':
            prefix_match = prefix_match.filter(cls.user_id != None)
        elif kind == 'service':
            prefix_match = prefix_match.filter(cls.service_id != None)
        elif kind is not None:
            raise ValueError("kind must be 'user', 'service', or None, not %r" % kind)
        for orm_token in prefix_match:
            if orm_token.match(token):
                return orm_token

    @classmethod
    def new(cls, token=None, user=None, service=None):
        """Generate a new API token for a user or service"""
        assert user or service
        assert not (user and service)
        db = inspect(user or service).session
        if token is None:
            token = new_token()
        else:
            cls.check_token(db, token)
        orm_token = cls(token=token)
        if user:
            assert user.id is not None
            orm_token.user_id = user.id
        else:
            assert service.id is not None
            orm_token.service_id = service.id
        db.add(orm_token)
        db.commit()
        return token


#------------------------------------
# OAuth tables
#------------------------------------


class GrantType(enum.Enum):
    # we only use authorization_code for now
    authorization_code = 'authorization_code'
    implicit = 'implicit'
    password = 'password'
    client_credentials = 'client_credentials'
    refresh_token = 'refresh_token'


class OAuthAccessToken(Hashed, Base):
    __tablename__ = 'oauth_access_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)

    client_id = Column(Unicode(1023))
    grant_type = Column(Enum(GrantType), nullable=False)
    expires_at = Column(Integer)
    refresh_token = Column(Unicode(64))
    refresh_expires_at = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    user = relationship(User)
    session = None # for API-equivalence with APIToken

    # from Hashed
    hashed = Column(Unicode(64))
    prefix = Column(Unicode(16), index=True)
    
    def __repr__(self):
        return "<{cls}('{prefix}...', user='{user}'>".format(
            cls=self.__class__.__name__,
            user=self.user and self.user.name,
            prefix=self.prefix,
        )


class OAuthCode(Base):
    __tablename__ = 'oauth_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Unicode(1023))
    code = Column(Unicode(36))
    expires_at = Column(Integer)
    redirect_uri = Column(Unicode(1023))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))


class OAuthClient(Base):
    __tablename__ = 'oauth_clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(Unicode(1023), unique=True)
    secret = Column(Unicode(1023))
    redirect_uri = Column(Unicode(1023))


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
