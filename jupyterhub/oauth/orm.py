"""SQLAlchemy declarations for OAuth2 data stores"""
from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy import (
    inspect,
    Column, Integer, ForeignKey, Unicode, Boolean,
    DateTime, Enum,
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.sql.expression import bindparam
from sqlalchemy import create_engine, Table
from ..orm import Base

import enum

class GrantType(enum.Enum):
    authorization_code = 'authorization_code'
    implicit = 'implicit'
    password = 'password'
    client_credentials = 'client_credentials'
    refresh_token = 'refresh_token'


class OAuthAccessToken(Base):
    __tablename__ = 'oauth_access_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Unicode(1023))
    grant_type = Column(Enum(GrantType), nullable=False)
    token = Column(Unicode(36))
    expires_at = Column(Integer)
    refresh_token = Column(Unicode(36))
    refresh_expires_at = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id'))


class OAuthCode(Base):
    __tablename__ = 'oauth_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Unicode(1023))
    code = Column(Unicode(36))
    expires_at = Column(Integer)
    redirect_uri = Column(Unicode(1023))
    user_id = Column(Integer, ForeignKey('users.id'))


class OAuthClient(Base):
    __tablename__ = 'oauth_clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(Unicode(1023))
    secret = Column(Unicode(1023))
    redirect_uri = Column(Unicode(1023))

