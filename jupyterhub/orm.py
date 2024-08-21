"""sqlalchemy ORM tools for the state of the constellation of processes"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import enum
import json
import numbers
import secrets
from base64 import decodebytes, encodebytes
from datetime import timedelta
from functools import lru_cache, partial
from itertools import chain

import alembic.command
import alembic.config
import sqlalchemy
from alembic.script import ScriptDirectory
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Unicode,
    create_engine,
    event,
    exc,
    inspect,
    or_,
    select,
    text,
)
from sqlalchemy.orm import (
    Session,
    declarative_base,
    declared_attr,
    interfaces,
    joinedload,
    object_session,
    relationship,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import LargeBinary, Text, TypeDecorator
from tornado.log import app_log

from .utils import compare_token, hash_token, new_token, random_port, utcnow

# top-level variable for easier mocking in tests
utcnow = partial(utcnow, with_tz=False)


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


class JSONList(JSONDict):
    """Represents an immutable structure as a json-encoded string (to be used for list type columns).

    Accepts list, tuple, sets for assignment

    Always read as a list

    Usage::

        JSONList(JSONDict)

    """

    def process_bind_param(self, value, dialect):
        if isinstance(value, (list, tuple)):
            value = json.dumps(value)
        if isinstance(value, set):
            # serialize sets as ordered lists
            value = json.dumps(sorted(value))

        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        else:
            value = json.loads(value)
        return value


meta = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

Base = declarative_base(metadata=meta)
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

    service = relationship("Service", back_populates="server", uselist=False)
    spawner = relationship("Spawner", back_populates="server", uselist=False)

    def __repr__(self):
        return f"<Server({self.ip}:{self.port})>"


# lots of things have roles
# mapping tables are the same for all of them

_role_associations = {}

for entity in (
    'user',
    'group',
    'service',
):
    table = Table(
        f'{entity}_role_map',
        Base.metadata,
        Column(
            f'{entity}_id',
            ForeignKey(f'{entity}s.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        Column(
            'role_id',
            ForeignKey('roles.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        Column('managed_by_auth', Boolean, default=False, nullable=False),
    )

    _role_associations[entity] = type(
        entity.title() + 'RoleMap', (Base,), {'__table__': table}
    )


class Role(Base):
    """User Roles"""

    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Unicode(255), unique=True)
    description = Column(Unicode(1023))
    scopes = Column(JSONList, default=[])

    users = relationship('User', secondary='user_role_map', back_populates='roles')
    services = relationship(
        'Service', secondary='service_role_map', back_populates='roles'
    )
    groups = relationship('Group', secondary='group_role_map', back_populates='roles')

    managed_by_auth = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name} ({self.description}) - scopes: {self.scopes}>"

    @classmethod
    def find(cls, db, name):
        """Find a role by name.
        Returns None if not found.
        """
        return db.query(cls).filter(cls.name == name).first()


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
    users = relationship('User', secondary='user_group_map', back_populates='groups')
    properties = Column(JSONDict, default={})
    roles = relationship(
        'Role', secondary='group_role_map', back_populates='groups', lazy="selectin"
    )

    shared_with_me = relationship(
        "Share",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # used in some model fields to differentiate 'whoami'
    kind = "group"

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}>"

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

    roles = relationship(
        'Role',
        secondary='user_role_map',
        back_populates='users',
        lazy="selectin",
    )

    _orm_spawners = relationship(
        "Spawner", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def orm_spawners(self):
        return {s.name: s for s in self._orm_spawners}

    admin = Column(Boolean(create_constraint=False), default=False)
    created = Column(DateTime, default=utcnow)
    last_activity = Column(DateTime, nullable=True)

    api_tokens = relationship(
        "APIToken", back_populates="user", cascade="all, delete-orphan"
    )
    groups = relationship(
        "Group",
        secondary='user_group_map',
        back_populates="users",
        lazy="selectin",
    )
    oauth_codes = relationship(
        "OAuthCode", back_populates="user", cascade="all, delete-orphan"
    )

    # sharing relationships
    shares = relationship(
        "Share",
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="Share.owner_id",
    )
    share_codes = relationship(
        "ShareCode",
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="ShareCode.owner_id",
    )
    shared_with_me = relationship(
        "Share",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Share.user_id",
        lazy="selectin",
    )

    @property
    def all_shared_with_me(self):
        """return all shares shared with me,

        including via group
        """

        return list(
            chain(
                self.shared_with_me,
                *[group.shared_with_me for group in self.groups],
            )
        )

    cookie_id = Column(Unicode(255), default=new_token, nullable=False, unique=True)
    # User.state is actually Spawner state
    # We will need to figure something else out if/when we have multiple spawners per user
    state = Column(JSONDict)
    # Authenticators can store their state here:
    # Encryption is handled elsewhere
    encrypted_auth_state = Column(LargeBinary)

    # used in some model fields to differentiate whether an owner or actor
    # is a user or service
    kind = "user"

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.name} {sum(bool(s.server) for s in self._orm_spawners)}/{len(self._orm_spawners)} running)>"

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
    """ "State about a Spawner"""

    __tablename__ = 'spawners'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    user = relationship("User", back_populates="_orm_spawners")

    server_id = Column(Integer, ForeignKey('servers.id', ondelete='SET NULL'))
    server = relationship(
        Server,
        back_populates="spawner",
        lazy="joined",
        single_parent=True,
        cascade="all, delete-orphan",
    )

    shares = relationship(
        "Share", back_populates="spawner", cascade="all, delete-orphan"
    )
    share_codes = relationship(
        "ShareCode", back_populates="spawner", cascade="all, delete-orphan"
    )

    state = Column(JSONDict)
    name = Column(Unicode(255))

    started = Column(DateTime)
    last_activity = Column(DateTime, nullable=True)
    user_options = Column(JSONDict)

    # added in 2.0
    oauth_client_id = Column(
        Unicode(255),
        ForeignKey(
            'oauth_clients.identifier',
            ondelete='SET NULL',
        ),
    )
    oauth_client = relationship(
        'OAuthClient',
        back_populates="spawner",
        cascade="all, delete-orphan",
        single_parent=True,
    )

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
    admin = Column(Boolean(create_constraint=False), default=False)
    roles = relationship(
        'Role', secondary='service_role_map', back_populates='services', lazy="selectin"
    )

    url = Column(Unicode(2047), nullable=True)

    oauth_client_allowed_scopes = Column(JSONList, nullable=True)

    info = Column(JSONDict, nullable=True)

    display = Column(Boolean, nullable=True)

    oauth_no_confirm = Column(Boolean, nullable=True)

    command = Column(JSONList, nullable=True)

    cwd = Column(Unicode(4095), nullable=True)

    environment = Column(JSONDict, nullable=True)

    user = Column(Unicode(255), nullable=True)

    from_config = Column(Boolean, default=True)

    api_tokens = relationship(
        "APIToken", back_populates="service", cascade="all, delete-orphan"
    )

    # service-specific interface
    _server_id = Column(Integer, ForeignKey('servers.id', ondelete='SET NULL'))
    server = relationship(
        Server,
        back_populates="service",
        single_parent=True,
        cascade="all, delete-orphan",
    )
    pid = Column(Integer)

    # added in 2.0
    oauth_client_id = Column(
        Unicode(255),
        ForeignKey(
            'oauth_clients.identifier',
            ondelete='SET NULL',
        ),
    )

    oauth_client = relationship(
        'OAuthClient',
        back_populates="service",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    # used in some model fields to differentiate 'whoami'
    kind = "service"

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

    now = utcnow  # function, must return float timestamp or datetime
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

    @property
    def expired(self):
        """Is this object expired?"""
        if not self.expires_at:
            return False
        else:
            return self.expires_in <= 0

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
        raise AttributeError(f"{self.__class__.__name__}.token is write-only")

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
                f"{cls.__name__}.token must be at least {cls.min_length} characters, got {len(token)}: {token[: cls.prefix_length]}..."
            )
        found = cls.find(db, token)
        if found:
            raise ValueError(
                f"Collision on {cls.__name__}: {token[: cls.prefix_length]}..."
            )

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
        prefix_match = db.query(cls).filter_by(prefix=prefix)
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
        prefix_match = cls.find_prefix(db, token).options(
            joinedload(cls.user), joinedload(cls.service)
        )

        for orm_token in prefix_match:
            if orm_token.match(token):
                return orm_token


class _Share:
    """Common columns for Share and ShareCode"""

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    # TODO: owner_id and spawner_id columns don't need `@declared_attr` when we can require sqlalchemy 2

    # the owner of the shared server
    # this is redundant with spawner.user, but saves a join
    @declared_attr
    def owner_id(self):
        return Column(Integer, ForeignKey('users.id', ondelete="CASCADE"))

    @declared_attr
    def owner(self):
        # table name happens to be appropriate 'shares', 'share_codes'
        # could be another, more explicit attribute, but the values would be the same
        return relationship(
            "User",
            back_populates=self.__tablename__,
            foreign_keys=[self.owner_id],
            lazy="selectin",
        )

    # the spawner the share is for
    @declared_attr
    def spawner_id(self):
        return Column(Integer, ForeignKey('spawners.id', ondelete="CASCADE"))

    @declared_attr
    def spawner(self):
        return relationship(
            "Spawner",
            back_populates=self.__tablename__,
            lazy="selectin",
        )

    # the permissions granted (!server filter will always be applied)
    scopes = Column(JSONList)
    expires_at = Column(DateTime, nullable=True)

    @classmethod
    def apply_filter(cls, scopes, spawner):
        """Apply our filter, ensures all scopes have appropriate !server filter

        Any other filters will raise ValueError.
        """
        return cls._apply_filter(frozenset(scopes), spawner.user.name, spawner.name)

    @staticmethod
    @lru_cache
    def _apply_filter(scopes, owner_name, server_name):
        """
        implementation of Share.apply_filter

        Static method so @lru_cache is persisted across instances
        """
        filtered_scopes = []
        server_filter = f"server={owner_name}/{server_name}"
        for scope in scopes:
            base_scope, _, filter = scope.partition("!")
            if filter and filter != server_filter:
                raise ValueError(
                    f"!{filter} not allowed on sharing {scope}, only !{server_filter}"
                )
            filtered_scopes.append(f"{base_scope}!{server_filter}")
        return frozenset(filtered_scopes)


class Share(_Share, Expiring, Base):
    """A single record of a sharing permission

    granted by one user to another user (or group)

    Restricted to a single server.
    """

    __tablename__ = "shares"

    # who the share is granted to (user or group)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True)
    user = relationship(
        "User", back_populates="shared_with_me", foreign_keys=[user_id], lazy="selectin"
    )

    group_id = Column(
        Integer, ForeignKey('groups.id', ondelete="CASCADE"), nullable=True
    )
    group = relationship("Group", back_populates="shared_with_me", lazy="selectin")

    def __repr__(self):
        if self.user:
            kind = "user"
            name = self.user.name
        elif self.group:
            kind = "group"
            name = self.group.name
        else:  # pragma: no cover
            kind = "deleted"
            name = "unknown"

        if self.owner and self.spawner:
            server_name = f"{self.owner.name}/{self.spawner.name}"
        else:  # pragma: n cover
            server_name = "unknown/deleted"

        return f"<{self.__class__.__name__}(server={server_name}, scopes={self.scopes}, {kind}={name})>"

    @staticmethod
    def _share_with_key(share_with):
        """Get the field name for share with

        either group_id or user_id, depending on type of share_with

        raises TypeError if neither User nor Group
        """
        if isinstance(share_with, User):
            return "user_id"
        elif isinstance(share_with, Group):
            return "group_id"
        else:
            raise TypeError(
                f"Can only share with orm.User or orm.Group, not {share_with!r}"
            )

    @classmethod
    def find(cls, db, spawner, share_with):
        """Find an existing

        Shares are unique for a given (spawner, user)
        """

        filter_by = {
            cls._share_with_key(share_with): share_with.id,
            "spawner_id": spawner.id,
            "owner_id": spawner.user.id,
        }
        return db.query(Share).filter_by(**filter_by).one_or_none()

    @staticmethod
    def _get_log_name(spawner, share_with):
        """construct log snippet to refer to the share"""
        return (
            f"{share_with.kind}:{share_with.name} on {spawner.user.name}/{spawner.name}"
        )

    @property
    def _log_name(self):
        return self._get_log_name(self.spawner, self.user or self.group)

    @classmethod
    def grant(cls, db, spawner, share_with, scopes=None):
        """Grant shared permissions for a server

        Updates existing Share if there is one,
        otherwise creates a new Share
        """
        if scopes is None:
            scopes = frozenset(
                [f"access:servers!server={spawner.user.name}/{spawner.name}"]
            )
        scopes = cls._apply_filter(frozenset(scopes), spawner.user.name, spawner.name)

        if not scopes:
            raise ValueError("Must specify scopes to grant.")

        # 1. lookup existing share and update
        share = cls.find(db, spawner, share_with)
        share_with_log = cls._get_log_name(spawner, share_with)
        if share is not None:
            # update existing permissions in-place
            # extend permissions
            existing_scopes = set(share.scopes)
            added_scopes = set(scopes).difference(existing_scopes)
            if not added_scopes:
                app_log.info(f"No new scopes for {share_with_log}")
                return share
            new_scopes = sorted(existing_scopes | added_scopes)
            app_log.info(f"Granting scopes {sorted(added_scopes)} for {share_with_log}")
            share.scopes = new_scopes
            db.commit()
        else:
            # no share for (spawner, share_with), create a new one
            app_log.info(f"Sharing scopes {sorted(scopes)} for {share_with_log}")
            share = cls(
                created_at=cls.now(),
                # copy shared fields
                owner=spawner.user,
                spawner=spawner,
                scopes=sorted(scopes),
            )
            if share_with.kind == "user":
                share.user = share_with
            elif share_with.kind == "group":
                share.group = share_with
            else:
                raise TypeError(f"Expected user or group, got {share_with!r}")
            db.add(share)
            db.commit()
        return share

    @classmethod
    def revoke(cls, db, spawner, share_with, scopes=None):
        """Revoke permissions for share_with on `spawner`

        If scopes are not specified, all scopes are revoked
        """
        share = cls.find(db, spawner, share_with)
        if share is None:
            _log_name = cls._get_log_name(spawner, share_with)
            app_log.info(f"No permissions to revoke from {_log_name}")
            return
        else:
            _log_name = share._log_name

        if scopes is None:
            app_log.info(f"Revoked all permissions from {_log_name}")
            db.delete(share)
            db.commit()
            return None

        # update scopes
        new_scopes = [scope for scope in share.scopes if scope not in scopes]
        revoked_scopes = [scope for scope in scopes if scope in set(share.scopes)]
        if new_scopes == share.scopes:
            app_log.info(f"No change in scopes for {_log_name}")
            return share
        elif not new_scopes:
            # revoked all scopes, delete the Share
            app_log.info(f"Revoked all permissions from {_log_name}")
            db.delete(share)
            db.commit()
        else:
            app_log.info(f"Revoked {revoked_scopes} from {_log_name}")
            share.scopes = new_scopes
            db.commit()

        if new_scopes:
            return share
        else:
            return None


class ShareCode(_Share, Hashed, Base):
    """A code that can be exchanged for a Share

    Ultimately, the same as a Share, but has a 'code'
    instead of a user or group that it is shared with.
    The code can be exchanged to create or update an actual Share.
    """

    __tablename__ = "share_codes"

    hashed = Column(Unicode(255), unique=True)
    prefix = Column(Unicode(16), index=True)
    exchange_count = Column(Integer, default=0)
    last_exchanged_at = Column(DateTime, nullable=True, default=None)

    _code_bytes = 32
    default_expires_in = 86400

    def __repr__(self):
        if self.owner and self.spawner:
            server_name = f"{self.owner.name}/{self.spawner.name}"
        else:
            server_name = "unknown/deleted"

        return f"<{self.__class__.__name__}(server={server_name}, scopes={self.scopes}, expires_at={self.expires_at})>"

    @classmethod
    def new(
        cls,
        db,
        spawner,
        *,
        scopes,
        expires_in=None,
        **kwargs,
    ):
        """Create a new ShareCode"""
        app_log.info(f"Creating share code for {spawner.user.name}/{spawner.name}")
        # verify scopes have the necessary filter
        kwargs["scopes"] = sorted(cls.apply_filter(scopes, spawner))
        if not expires_in:
            expires_in = cls.default_expires_in
        kwargs["expires_at"] = utcnow() + timedelta(seconds=expires_in)
        kwargs["spawner"] = spawner
        kwargs["owner"] = spawner.user
        code = secrets.token_urlsafe(cls._code_bytes)

        # create the ShareCode
        share_code = cls(**kwargs)
        # setting Hashed.token property sets the `hashed` column in the db
        share_code.token = code
        # actually put it in the db
        db.add(share_code)
        db.commit()
        return (share_code, code)

    @classmethod
    def find(cls, db, code, *, spawner=None):
        """Lookup a single ShareCode by code"""
        prefix_match = cls.find_prefix(db, code)
        if spawner:
            prefix_match = prefix_match.filter_by(spawner_id=spawner.id)
        for share_code in prefix_match:
            if share_code.match(code):
                return share_code

    def exchange(self, share_with):
        """exchange a ShareCode for a Share

        share_with can be a User or a Group.
        """
        db = inspect(self).session
        share_code_log = f"Share code {self.prefix}..."
        if self.expired:
            db.delete(self)
            db.commit()
            raise ValueError(f"{share_code_log} expired")

        share_with_log = f"{share_with.kind}:{share_with.name} on {self.owner.name}/{self.spawner.name}"
        app_log.info(f"Exchanging {share_code_log} for {share_with_log}")
        share = Share.grant(db, self.spawner, share_with, self.scopes)
        # note: we count exchanges, even if they don't modify the permissions
        # (e.g. one user exchanging the same code twice)
        self.exchange_count += 1
        self.last_exchanged_at = self.now()
        db.commit()
        return share


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


class APIToken(Hashed, Base):
    """An API token"""

    __tablename__ = 'api_tokens'

    user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete="CASCADE"),
        nullable=True,
    )
    service_id = Column(
        Integer,
        ForeignKey('services.id', ondelete="CASCADE"),
        nullable=True,
    )

    user = relationship("User", back_populates="api_tokens")
    service = relationship("Service", back_populates="api_tokens")
    oauth_client = relationship("OAuthClient", back_populates="access_tokens")

    id = Column(Integer, primary_key=True)
    hashed = Column(Unicode(255), unique=True)
    prefix = Column(Unicode(16), index=True)

    @property
    def api_id(self):
        return 'a%i' % self.id

    @property
    def owner(self):
        return self.user or self.service

    # added in 2.0
    client_id = Column(
        Unicode(255),
        ForeignKey(
            'oauth_clients.identifier',
            ondelete='CASCADE',
        ),
    )

    # FIXME: refresh_tokens not implemented
    # should be a relation to another token table
    # refresh_token = Column(
    #     Integer,
    #     ForeignKey('refresh_tokens.id', ondelete="CASCADE"),
    #     nullable=True,
    # )

    # the browser session id associated with a given token,
    # if issued during oauth to be stored in a cookie
    session_id = Column(Unicode(255), nullable=True)

    # token metadata for bookkeeping
    now = utcnow  # for expiry
    created = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, default=None, nullable=True)
    last_activity = Column(DateTime)
    note = Column(Unicode(1023))
    scopes = Column(JSONList, default=[])

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
        return f"<{self.__class__.__name__}('{self.prefix}...', {kind}='{name}', client_id={self.client_id!r})>"

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
            raise ValueError(f"kind must be 'user', 'service', or None, not {kind!r}")
        for orm_token in prefix_match:
            if orm_token.match(token):
                if not orm_token.client_id:
                    app_log.warning(
                        "Deleting stale oauth token for %s with no client",
                        orm_token.user and orm_token.user.name,
                    )
                    db.delete(orm_token)
                    db.commit()
                    return
                return orm_token

    @classmethod
    def new(
        cls,
        token=None,
        *,
        user=None,
        service=None,
        roles=None,
        scopes=None,
        note='',
        generated=True,
        session_id=None,
        expires_in=None,
        client_id=None,
        oauth_client=None,
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

        # avoid circular import
        from .roles import roles_to_scopes

        if scopes is not None and roles is not None:
            raise ValueError(
                "Can only assign one of scopes or roles when creating tokens."
            )

        elif scopes is None and roles is None:
            # this is the default branch
            # use the default 'token' role to specify default permissions for API tokens
            default_token_role = Role.find(db, 'token')
            if not default_token_role:
                scopes = ["inherit"]
            else:
                scopes = roles_to_scopes([default_token_role])
        elif roles is not None:
            # evaluate roles to scopes immediately
            # TODO: should this be deprecated, or not?
            # warnings.warn(
            #     "Setting roles on tokens is deprecated in JupyterHub 3.0. Use scopes.",
            #     DeprecationWarning,
            #     stacklevel=3,
            # )
            orm_roles = []
            for rolename in roles:
                role = Role.find(db, name=rolename)
                if role is None:
                    raise ValueError(f"No such role: {rolename}")
                orm_roles.append(role)
            scopes = roles_to_scopes(orm_roles)

        if oauth_client is None:
            # lookup oauth client by identifier
            if client_id is None:
                # default: global 'jupyterhub' client
                client_id = "jupyterhub"
            oauth_client = db.query(OAuthClient).filter_by(identifier=client_id).one()
        if client_id is None:
            client_id = oauth_client.identifier

        # avoid circular import
        from .scopes import _check_scopes_exist, _check_token_scopes

        _check_scopes_exist(scopes, who_for="token")
        _check_token_scopes(scopes, owner=user or service, oauth_client=oauth_client)

        # two stages to ensure orm_token.generated has been set
        # before token setter is called
        orm_token = cls(
            generated=generated,
            note=note or '',
            client_id=client_id,
            session_id=session_id,
            scopes=list(scopes),
        )
        db.add(orm_token)
        orm_token.token = token
        if user:
            assert user.id is not None
            orm_token.user = user
        else:
            assert service.id is not None
            orm_token.service = service
        if expires_in:
            if not isinstance(expires_in, numbers.Real):
                raise TypeError(
                    f"expires_in must be a positive integer or null, not {expires_in!r}"
                )
            expires_in = int(expires_in)
            # tokens must always expire in the future
            if expires_in < 1:
                raise ValueError(
                    f"expires_in must be a positive integer or null, not {expires_in!r}"
                )

            orm_token.expires_at = cls.now() + timedelta(seconds=expires_in)

        db.commit()
        return token

    def update_scopes(self, new_scopes):
        """Set new scopes, checking that they are allowed"""
        from .scopes import _check_scopes_exist, _check_token_scopes

        _check_scopes_exist(new_scopes, who_for="token")
        _check_token_scopes(
            new_scopes, owner=self.owner, oauth_client=self.oauth_client
        )
        self.scopes = new_scopes


class OAuthCode(Expiring, Base):
    __tablename__ = 'oauth_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        Unicode(255), ForeignKey('oauth_clients.identifier', ondelete='CASCADE')
    )
    client = relationship(
        "OAuthClient",
        back_populates="codes",
    )
    code = Column(Unicode(36))
    expires_at = Column(Integer)
    redirect_uri = Column(Unicode(1023))
    session_id = Column(Unicode(255))
    # state = Column(Unicode(1023))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    user = relationship(
        "User",
        back_populates="oauth_codes",
    )

    scopes = Column(JSONList, default=[])

    @staticmethod
    def now():
        return utcnow(with_tz=True).timestamp()

    @classmethod
    def find(cls, db, code):
        return (
            db.query(cls)
            .filter(cls.code == code)
            .filter(or_(cls.expires_at == None, cls.expires_at >= cls.now()))
            .options(
                # load user with the code
                joinedload(cls.user, innerjoin=True),
            )
            .first()
        )

    def __repr__(self):
        return (
            f"<{self.__class__.__name__}(id={self.id}, client_id={self.client_id!r})>"
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

    spawner = relationship(
        "Spawner",
        back_populates="oauth_client",
        uselist=False,
    )
    service = relationship(
        "Service",
        back_populates="oauth_client",
        uselist=False,
    )
    access_tokens = relationship(
        APIToken, back_populates='oauth_client', cascade='all, delete-orphan'
    )
    codes = relationship(
        OAuthCode, back_populates='client', cascade='all, delete-orphan'
    )

    # these are the scopes an oauth client is allowed to request
    # *not* the scopes of the client itself
    allowed_scopes = Column(JSONList, default=[])

    def __repr__(self):
        return f"<{self.__class__.__name__}(identifier={self.identifier!r})>"


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

    # listeners are normally registered as a decorator,
    # but we need two different signatures to avoid SAWarning:
    #    The argument signature for the "ConnectionEvents.engine_connect" event listener has changed
    # while we support sqla 1.4 and 2.0.
    # @event.listens_for(engine, "engine_connect")
    def ping_connection(connection):
        # turn off "close with result".  This flag is only used with
        # "connectionless" execution, otherwise will be False in any case
        save_should_close_with_result = connection.should_close_with_result
        connection.should_close_with_result = False

        try:
            # run a SELECT 1. use a core select() so that
            # the SELECT of a scalar value without a table is
            # appropriately formatted for the backend
            with connection.begin() as transaction:
                connection.scalar(select(1))
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
                with connection.begin() as transaction:
                    connection.scalar(select(1))
            else:
                raise
        finally:
            # restore "close with result"
            connection.should_close_with_result = save_should_close_with_result

    # sqla v1/v2 compatible invocation of @event.listens_for:
    def ping_connection_v1(connection, branch=None):
        """sqlalchemy < 2.0 compatibility"""
        return ping_connection(connection)

    if int(sqlalchemy.__version__.split(".", 1)[0]) >= 2:
        listener = ping_connection
    else:
        listener = ping_connection_v1
    event.listens_for(engine, "engine_connect")(listener)


def check_db_revision(engine):
    """Check the JupyterHub database revision

    After calling this function, an alembic tag is guaranteed to be stored in the db.

    - Checks the alembic tag and raises a ValueError if it's not the current revision
    - If no tag is stored (Bug in Hub prior to 0.8),
      guess revision based on db contents and tag the revision.
    - Empty databases are tagged with the current revision
    """
    # Check database schema version
    current_table_names = set(inspect(engine).get_table_names())
    my_table_names = set(Base.metadata.tables.keys())

    from .dbutil import _temp_alembic_ini

    # alembic needs the password if it's in the URL
    engine_url = engine.url.render_as_string(hide_password=False)

    with _temp_alembic_ini(engine_url) as ini:
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
    with engine.begin() as connection:
        alembic_revision = connection.execute(
            text('SELECT version_num FROM alembic_version')
        ).first()[0]
    if alembic_revision == head:
        app_log.debug("database schema version found: %s", alembic_revision)
    else:
        raise DatabaseSchemaMismatch(
            f"Found database schema version {alembic_revision} != {head}. "
            "Backup your database and run `jupyterhub upgrade-db`"
            " to upgrade to the latest schema."
        )


def mysql_large_prefix_check(engine):
    """Check mysql has innodb_large_prefix set"""
    if not str(engine.url).startswith('mysql'):
        return False
    with engine.begin() as connection:
        variables = dict(
            connection.execute(
                text(
                    'show variables where variable_name like '
                    '"innodb_large_prefix" or '
                    'variable_name like "innodb_file_format";'
                )
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

    kwargs.setdefault("future", True)

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


def get_class(resource_name):
    """Translates resource string names to ORM classes"""
    class_dict = {
        'users': User,
        'services': Service,
        'tokens': APIToken,
        'groups': Group,
    }
    if resource_name not in class_dict:
        raise ValueError(
            f'Kind must be one of {", ".join(class_dict)}, not {resource_name}'
        )
    return class_dict[resource_name]
