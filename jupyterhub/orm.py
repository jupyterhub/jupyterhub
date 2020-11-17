"""sqlalchemy ORM tools for the state of the constellation of processes"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import enum
import json
from base64 import decodebytes
from base64 import encodebytes
from datetime import datetime
from datetime import timedelta

import alembic.command
import alembic.config
from alembic.script import ScriptDirectory
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import event
from sqlalchemy import exc
from sqlalchemy import ForeignKey
from sqlalchemy import inspect
from sqlalchemy import Integer
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import interfaces
from sqlalchemy.orm import object_session
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.types import LargeBinary
from sqlalchemy.types import Text
from sqlalchemy.types import TypeDecorator
from tornado.log import app_log

from .utils import compare_token
from .utils import hash_token
from .utils import new_token
from .utils import random_port

# top-level variable for easier mocking in tests
utcnow = datetime.utcnow


class JSONDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Usage::

        JSONDict(255)

    """

    impl = Text

    def _json_default(self, obj):
        """encode non-jsonable objects as JSON

        Currently only bytes are supported

        """
        if not isinstance(obj, bytes):
            app_log.warning(
                "Non-jsonable data in user_options: %r; will persist None.", type(obj)
            )
            return None

        return {"__jupyterhub_bytes__": True, "data": encodebytes(obj).decode('ascii')}

    def _object_hook(self, dct):
        """decode non-json objects packed by _json_default"""
        if dct.get("__jupyterhub_bytes__", False):
            return decodebytes(dct['data'].encode('ascii'))
        return dct

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value, default=self._json_default)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value, object_hook=self._object_hook)
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


# user:group many:many mapping table
user_group_map = Table(
    'user_group_map',
    Base.metadata,
    Column('user_id', ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('group_id', ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
)


class Group(Base):
    """User Groups"""

    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(255), unique=True)
    users = relationship('User', secondary='user_group_map', backref='groups')

    def __repr__(self):
        return "<%s %s (%i users)>" % (
            self.__class__.__name__,
            self.name,
            len(self.users),
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
    name = Column(Unicode(255), unique=True)

    _orm_spawners = relationship(
        "Spawner", backref="user", cascade="all, delete-orphan"
    )

    @property
    def orm_spawners(self):
        return {s.name: s for s in self._orm_spawners}

    admin = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, nullable=True)

    api_tokens = relationship("APIToken", backref="user", cascade="all, delete-orphan")
    oauth_tokens = relationship(
        "OAuthAccessToken", backref="user", cascade="all, delete-orphan"
    )
    oauth_codes = relationship(
        "OAuthCode", backref="user", cascade="all, delete-orphan"
    )
    cookie_id = Column(Unicode(255), default=new_token, nullable=False, unique=True)
    # User.state is actually Spawner state
    # We will need to figure something else out if/when we have multiple spawners per user
    state = Column(JSONDict)
    # Authenticators can store their state here:
    # Encryption is handled elsewhere
    encrypted_auth_state = Column(LargeBinary)

    def __repr__(self):
        return "<{cls}({name} {running}/{total} running)>".format(
            cls=self.__class__.__name__,
            name=self.name,
            total=len(self._orm_spawners),
            running=sum(bool(s.server) for s in self._orm_spawners),
        )

    def new_api_token(self, token=None, **kwargs):
        """Create a new API token

        If `token` is given, load that token.
        """
        return APIToken.new(token=token, user=self, **kwargs)

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

    server_id = Column(Integer, ForeignKey('servers.id', ondelete='SET NULL'))
    server = relationship(
        Server,
        backref=backref('spawner', uselist=False),
        single_parent=True,
        cascade="all, delete-orphan",
    )

    state = Column(JSONDict)
    name = Column(Unicode(255))

    started = Column(DateTime)
    last_activity = Column(DateTime, nullable=True)
    user_options = Column(JSONDict)

    # properties on the spawner wrapper
    # some APIs get these low-level objects
    # when the spawner isn't running,
    # for which these should all be False
    active = running = ready = False
    pending = None

    @property
    def orm_spawner(self):
        return self


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
    name = Column(Unicode(255), unique=True)
    admin = Column(Boolean, default=False)

    api_tokens = relationship(
        "APIToken", backref="service", cascade="all, delete-orphan"
    )

    # service-specific interface
    _server_id = Column(Integer, ForeignKey('servers.id', ondelete='SET NULL'))
    server = relationship(
        Server,
        backref=backref('service', uselist=False),
        single_parent=True,
        cascade="all, delete-orphan",
    )
    pid = Column(Integer)

    def new_api_token(self, token=None, **kwargs):
        """Create a new API token
        If `token` is given, load that token.
        """
        return APIToken.new(token=token, service=self, **kwargs)

    @classmethod
    def find(cls, db, name):
        """Find a service by name.

        Returns None if not found.
        """
        return db.query(cls).filter(cls.name == name).first()


class Expiring:
    """Mixin for expiring entries

    Subclass must define at least expires_at property,
    which should be unix timestamp or datetime object
    """

    now = utcnow  # funciton, must return float timestamp or datetime
    expires_at = None  # must be defined

    @property
    def expires_in(self):
        """Property returning expiration in seconds from now

        or None
        """
        if self.expires_at:
            delta = self.expires_at - self.now()
            if isinstance(delta, timedelta):
                delta = delta.total_seconds()
            return delta
        else:
            return None

    @classmethod
    def purge_expired(cls, db):
        """Purge expired API Tokens from the database"""
        now = cls.now()
        deleted = False
        for obj in (
            db.query(cls).filter(cls.expires_at != None).filter(cls.expires_at < now)
        ):
            app_log.debug("Purging expired %s", obj)
            deleted = True
            db.delete(obj)
        if deleted:
            db.commit()


class Hashed(Expiring):
    """Mixin for tables with hashed tokens"""

    prefix_length = 4
    algorithm = "sha512"
    rounds = 16384
    salt_bytes = 8
    min_length = 8

    # values to use for internally generated tokens,
    # which have good entropy as UUIDs
    generated = True
    generated_salt_bytes = 8
    generated_rounds = 1

    @property
    def token(self):
        raise AttributeError("token is write-only")

    @token.setter
    def token(self, token):
        """Store the hashed value and prefix for a token"""
        self.prefix = token[: self.prefix_length]
        if self.generated:
            # Generated tokens are UUIDs, which have sufficient entropy on their own
            # and don't need salt & hash rounds.
            # ref: https://security.stackexchange.com/a/151262/155114
            rounds = self.generated_rounds
            salt_bytes = self.generated_salt_bytes
        else:
            rounds = self.rounds
            salt_bytes = self.salt_bytes
        self.hashed = hash_token(
            token, rounds=rounds, salt=salt_bytes, algorithm=self.algorithm
        )

    def match(self, token):
        """Is this my token?"""
        return compare_token(self.hashed, token)

    @classmethod
    def check_token(cls, db, token):
        """Check if a token is acceptable"""
        if len(token) < cls.min_length:
            raise ValueError(
                "Tokens must be at least %i characters, got %r"
                % (cls.min_length, token)
            )
        found = cls.find(db, token)
        if found:
            raise ValueError("Collision on token: %s..." % token[: cls.prefix_length])

    @classmethod
    def find_prefix(cls, db, token):
        """Start the query for matching token.

        Returns an SQLAlchemy query already filtered by prefix-matches.

        .. versionchanged:: 1.2

            Excludes expired matches.
        """
        prefix = token[: cls.prefix_length]
        # since we can't filter on hashed values, filter on prefix
        # so we aren't comparing with all tokens
        prefix_match = db.query(cls).filter(
            bindparam('prefix', prefix).startswith(cls.prefix)
        )
        prefix_match = prefix_match.filter(
            or_(cls.expires_at == None, cls.expires_at >= cls.now())
        )
        return prefix_match

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

    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True)
    service_id = Column(
        Integer, ForeignKey('services.id', ondelete="CASCADE"), nullable=True
    )

    id = Column(Integer, primary_key=True)
    hashed = Column(Unicode(255), unique=True)
    prefix = Column(Unicode(16), index=True)

    @property
    def api_id(self):
        return 'a%i' % self.id

    # token metadata for bookkeeping
    now = datetime.utcnow  # for expiry
    created = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=None, nullable=True)
    last_activity = Column(DateTime)
    note = Column(Unicode(1023))

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
            cls=self.__class__.__name__, pre=self.prefix, kind=kind, name=name
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
    def new(
        cls,
        token=None,
        user=None,
        service=None,
        note='',
        generated=True,
        expires_in=None,
    ):
        """Generate a new API token for a user or service"""
        assert user or service
        assert not (user and service)
        db = inspect(user or service).session
        if token is None:
            token = new_token()
            # Don't need hash + salt rounds on generated tokens,
            # which already have good entropy
            generated = True
        else:
            cls.check_token(db, token)
        # two stages to ensure orm_token.generated has been set
        # before token setter is called
        orm_token = cls(generated=generated, note=note or '')
        orm_token.token = token
        if user:
            assert user.id is not None
            orm_token.user = user
        else:
            assert service.id is not None
            orm_token.service = service
        if expires_in is not None:
            orm_token.expires_at = cls.now() + timedelta(seconds=expires_in)
        db.add(orm_token)
        db.commit()
        return token


# ------------------------------------
# OAuth tables
# ------------------------------------


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

    @staticmethod
    def now():
        return datetime.utcnow().timestamp()

    @property
    def api_id(self):
        return 'o%i' % self.id

    client_id = Column(
        Unicode(255), ForeignKey('oauth_clients.identifier', ondelete='CASCADE')
    )
    grant_type = Column(Enum(GrantType), nullable=False)
    expires_at = Column(Integer)
    refresh_token = Column(Unicode(255))
    # TODO: drop refresh_expires_at. Refresh tokens shouldn't expire
    refresh_expires_at = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    service = None  # for API-equivalence with APIToken

    # the browser session id associated with a given token
    session_id = Column(Unicode(255))

    # from Hashed
    hashed = Column(Unicode(255), unique=True)
    prefix = Column(Unicode(16), index=True)

    created = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, nullable=True)

    def __repr__(self):
        return "<{cls}('{prefix}...', client_id={client_id!r}, user={user!r}, expires_in={expires_in}>".format(
            cls=self.__class__.__name__,
            client_id=self.client_id,
            user=self.user and self.user.name,
            prefix=self.prefix,
            expires_in=self.expires_in,
        )

    @classmethod
    def find(cls, db, token):
        orm_token = super().find(db, token)
        if orm_token and not orm_token.client_id:
            app_log.warning(
                "Deleting stale oauth token for %s with no client",
                orm_token.user and orm_token.user.name,
            )
            db.delete(orm_token)
            db.commit()
            return
        return orm_token


class OAuthCode(Expiring, Base):
    __tablename__ = 'oauth_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        Unicode(255), ForeignKey('oauth_clients.identifier', ondelete='CASCADE')
    )
    code = Column(Unicode(36))
    expires_at = Column(Integer)
    redirect_uri = Column(Unicode(1023))
    session_id = Column(Unicode(255))
    # state = Column(Unicode(1023))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))

    @staticmethod
    def now():
        return datetime.utcnow().timestamp()

    @classmethod
    def find(cls, db, code):
        return (
            db.query(cls)
            .filter(cls.code == code)
            .filter(or_(cls.expires_at == None, cls.expires_at >= cls.now()))
            .first()
        )


class OAuthClient(Base):
    __tablename__ = 'oauth_clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(Unicode(255), unique=True)
    description = Column(Unicode(1023))
    secret = Column(Unicode(255))
    redirect_uri = Column(Unicode(1023))

    @property
    def client_id(self):
        return self.identifier

    access_tokens = relationship(
        OAuthAccessToken, backref='client', cascade='all, delete-orphan'
    )
    codes = relationship(OAuthCode, backref='client', cascade='all, delete-orphan')


# General database utilities


class DatabaseSchemaMismatch(Exception):
    """Exception raised when the database schema version does not match

    the current version of JupyterHub.
    """


def register_foreign_keys(engine):
    """register PRAGMA foreign_keys=on on connection"""

    @event.listens_for(engine, "connect")
    def connect(dbapi_con, con_record):
        cursor = dbapi_con.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _expire_relationship(target, relationship_prop):
    """Expire relationship backrefs

    used when an object with relationships is deleted
    """

    session = object_session(target)
    # get peer objects to be expired
    peers = getattr(target, relationship_prop.key)
    if peers is None:
        # no peer to clear
        return
    # many-to-many and one-to-many have a list of peers
    # many-to-one has only one
    if (
        relationship_prop.direction is interfaces.MANYTOONE
        or not relationship_prop.uselist
    ):
        peers = [peers]
    for obj in peers:
        if inspect(obj).persistent:
            session.expire(obj, [relationship_prop.back_populates])


@event.listens_for(Session, "persistent_to_deleted")
def _notify_deleted_relationships(session, obj):
    """Expire relationships when an object becomes deleted

    Needed to keep relationships up to date.
    """
    mapper = inspect(obj).mapper
    for prop in mapper.relationships:
        if prop.back_populates:
            _expire_relationship(obj, prop)


def register_ping_connection(engine):
    """Check connections before using them.

    Avoids database errors when using stale connections.

    From SQLAlchemy docs on pessimistic disconnect handling:

    https://docs.sqlalchemy.org/en/rel_1_1/core/pooling.html#disconnect-handling-pessimistic
    """

    @event.listens_for(engine, "engine_connect")
    def ping_connection(connection, branch):
        if branch:
            # "branch" refers to a sub-connection of a connection,
            # we don't want to bother pinging on these.
            return

        # turn off "close with result".  This flag is only used with
        # "connectionless" execution, otherwise will be False in any case
        save_should_close_with_result = connection.should_close_with_result
        connection.should_close_with_result = False

        try:
            # run a SELECT 1.   use a core select() so that
            # the SELECT of a scalar value without a table is
            # appropriately formatted for the backend
            connection.scalar(select([1]))
        except exc.DBAPIError as err:
            # catch SQLAlchemy's DBAPIError, which is a wrapper
            # for the DBAPI's exception.  It includes a .connection_invalidated
            # attribute which specifies if this connection is a "disconnect"
            # condition, which is based on inspection of the original exception
            # by the dialect in use.
            if err.connection_invalidated:
                app_log.error(
                    "Database connection error, attempting to reconnect: %s", err
                )
                # run the same SELECT again - the connection will re-validate
                # itself and establish a new connection.  The disconnect detection
                # here also causes the whole connection pool to be invalidated
                # so that all stale connections are discarded.
                connection.scalar(select([1]))
            else:
                raise
        finally:
            # restore "close with result"
            connection.should_close_with_result = save_should_close_with_result


def check_db_revision(engine):
    """Check the JupyterHub database revision

    After calling this function, an alembic tag is guaranteed to be stored in the db.

    - Checks the alembic tag and raises a ValueError if it's not the current revision
    - If no tag is stored (Bug in Hub prior to 0.8),
      guess revision based on db contents and tag the revision.
    - Empty databases are tagged with the current revision
    """
    # Check database schema version
    current_table_names = set(engine.table_names())
    my_table_names = set(Base.metadata.tables.keys())

    from .dbutil import _temp_alembic_ini

    with _temp_alembic_ini(engine.url) as ini:
        cfg = alembic.config.Config(ini)
        scripts = ScriptDirectory.from_config(cfg)
        head = scripts.get_heads()[0]
        base = scripts.get_base()

        if not my_table_names.intersection(current_table_names):
            # no tables have been created, stamp with current revision
            app_log.debug("Stamping empty database with alembic revision %s", head)
            alembic.command.stamp(cfg, head)
            return

        if 'alembic_version' not in current_table_names:
            # Has not been tagged or upgraded before.
            # we didn't start tagging revisions correctly except during `upgrade-db`
            # until 0.8
            # This should only occur for databases created prior to JupyterHub 0.8
            msg_t = "Database schema version not found, guessing that JupyterHub %s created this database."
            if 'spawners' in current_table_names:
                # 0.8
                app_log.warning(msg_t, '0.8.dev')
                rev = head
            elif 'services' in current_table_names:
                # services is present, tag for 0.7
                app_log.warning(msg_t, '0.7.x')
                rev = 'af4cbdb2d13c'
            else:
                # it's old, mark as first revision
                app_log.warning(msg_t, '0.6 or earlier')
                rev = base
            app_log.debug("Stamping database schema version %s", rev)
            alembic.command.stamp(cfg, rev)

    # check database schema version
    # it should always be defined at this point
    alembic_revision = engine.execute(
        'SELECT version_num FROM alembic_version'
    ).first()[0]
    if alembic_revision == head:
        app_log.debug("database schema version found: %s", alembic_revision)
        pass
    else:
        raise DatabaseSchemaMismatch(
            "Found database schema version {found} != {head}. "
            "Backup your database and run `jupyterhub upgrade-db`"
            " to upgrade to the latest schema.".format(
                found=alembic_revision, head=head
            )
        )


def mysql_large_prefix_check(engine):
    """Check mysql has innodb_large_prefix set"""
    if not str(engine.url).startswith('mysql'):
        return False
    variables = dict(
        engine.execute(
            'show variables where variable_name like '
            '"innodb_large_prefix" or '
            'variable_name like "innodb_file_format";'
        ).fetchall()
    )
    if (
        variables.get('innodb_file_format', 'Barracuda') == 'Barracuda'
        and variables.get('innodb_large_prefix', 'ON') == 'ON'
    ):
        return True
    else:
        return False


def add_row_format(base):
    for t in base.metadata.tables.values():
        t.dialect_kwargs['mysql_ROW_FORMAT'] = 'DYNAMIC'


def new_session_factory(
    url="sqlite:///:memory:", reset=False, expire_on_commit=False, **kwargs
):
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
    if url.startswith('sqlite'):
        register_foreign_keys(engine)

    # enable pessimistic disconnect handling
    register_ping_connection(engine)

    if reset:
        Base.metadata.drop_all(engine)

    if mysql_large_prefix_check(engine):  # if mysql is allows large indexes
        add_row_format(Base)  # set format on the tables
    # check the db revision (will raise, pointing to `upgrade-db` if version doesn't match)
    check_db_revision(engine)

    Base.metadata.create_all(engine)

    # We set expire_on_commit=False, since we don't actually need
    # SQLAlchemy to expire objects after committing - we don't expect
    # concurrent runs of the hub talking to the same db. Turning
    # this off gives us a major performance boost
    session_factory = sessionmaker(bind=engine, expire_on_commit=expire_on_commit)
    return session_factory
