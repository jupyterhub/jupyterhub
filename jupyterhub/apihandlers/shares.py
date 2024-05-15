"""Handlers for Shares and Share Codes"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import re
from typing import List, Optional
from urllib.parse import urlunparse

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    conint,
    field_validator,
    model_validator,
)
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from tornado import web
from tornado.httputil import url_concat

from .. import orm
from ..scopes import _check_scopes_exist, needs_scope
from ..utils import isoformat
from .base import APIHandler
from .groups import _GroupAPIHandler

_share_code_id_pat = re.compile(r"sc_(\d+)")


class BaseShareRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scopes: Optional[List[str]] = None

    @field_validator("scopes")
    @classmethod
    def _check_scopes_exist(cls, scopes):
        if not scopes:
            return None
        _check_scopes_exist(scopes, who_for="share")
        return scopes


class ShareGrantRequest(BaseShareRequest):
    """Validator for requests to grant sharing permission"""

    # directly granted shares don't expire
    # since Shares are _modifications_ of permissions,
    # expiration can get weird
    # if it's going to expire, it must expire in
    # at least one minute and at most 10 years (avoids nonsense values)
    # expires_in: conint(ge=60, le=10 * 525600 * 60) | None = None
    user: Optional[str] = None
    group: Optional[str] = None

    @model_validator(mode='after')
    def user_group_exclusive(self):
        if self.user and self.group:
            raise ValueError("Expected exactly one of `user` or `group`, not both.")
        if self.user is None and self.group is None:
            raise ValueError("Specify exactly one of `user` or `group`")
        return self


class ShareRevokeRequest(ShareGrantRequest):
    """Validator for requests to revoke sharing permission"""

    # currently identical to ShareGrantRequest


class ShareCodeGrantRequest(BaseShareRequest):
    """Validator for requests to create sharing codes"""

    # must be at least one minute, at most one year, default to one day
    expires_in: conint(ge=60, le=525600 * 60) = 86400


class _ShareAPIHandler(APIHandler):
    def server_model(self, spawner):
        """Truncated server model for use in shares

        - Adds "user" field (just name for now)
        - Limits fields to "name", "url", "full_url", "ready"
          from standard server model
        """
        user = self.users[spawner.user.id]
        if spawner.name in user.spawners:
            # use Spawner wrapper if it's active
            spawner = user.spawners[spawner.name]
        full_model = super().server_model(spawner, user=user)
        # filter out subset of fields
        server_model = {
            "user": {
                "name": spawner.user.name,
            }
        }
        # subset keys for sharing
        for key in ["name", "url", "full_url", "ready"]:
            if key in full_model:
                server_model[key] = full_model[key]

        return server_model

    def share_model(self, share):
        """Compute the REST API model for a share"""
        return {
            "server": self.server_model(share.spawner),
            "scopes": share.scopes,
            "user": {"name": share.user.name} if share.user else None,
            "group": {"name": share.group.name} if share.group else None,
            "kind": "group" if share.group else "user",
            "created_at": isoformat(share.created_at),
        }

    def share_code_model(self, share_code, code=None):
        """Compute the REST API model for a share code"""
        model = {
            "server": self.server_model(share_code.spawner),
            "scopes": share_code.scopes,
            "id": f"sc_{share_code.id}",
            "created_at": isoformat(share_code.created_at),
            "expires_at": isoformat(share_code.expires_at),
            "exchange_count": share_code.exchange_count,
            "last_exchanged_at": isoformat(share_code.last_exchanged_at),
        }
        if code:
            model["code"] = code
            model["accept_url"] = url_concat(
                self.hub.base_url + "accept-share", {"code": code}
            )
            model["full_accept_url"] = None
            public_url = self.settings.get("public_url")
            if public_url:
                model["full_accept_url"] = urlunparse(
                    public_url._replace(path=model["accept_url"])
                )
        return model

    def _init_share_query(self, kind="share"):
        """Initialize a query for Shares

        before applying filters

        A method so we can consolidate joins, etc.
        """
        if kind == "share":
            class_ = orm.Share
        elif kind == "code":
            class_ = orm.ShareCode
        else:
            raise ValueError(
                f"kind must be `share` or `code`, not {kind!r}"
            )  # pragma: no cover

        query = self.db.query(class_).options(
            joinedload(class_.owner).lazyload("*"),
            joinedload(class_.spawner).joinedload(orm.Spawner.user).lazyload("*"),
        )
        if kind == 'share':
            query = query.options(
                joinedload(class_.user).joinedload(orm.User.groups).lazyload("*"),
                joinedload(class_.group).lazyload("*"),
            )
        return query

    def _share_list_model(self, query, kind="share"):
        """Finish a share query, returning the _model_"""
        offset, limit = self.get_api_pagination()
        if kind == "share":
            model_method = self.share_model
        elif kind == "code":
            model_method = self.share_code_model
        else:
            raise ValueError(
                f"kind must be `share` or `code`, not {kind!r}"
            )  # pragma: no cover

        if kind == "share":
            class_ = orm.Share
        elif kind == "code":
            class_ = orm.ShareCode

        total_count = query.count()
        query = query.order_by(class_.id.asc()).offset(offset).limit(limit)
        share_list = [model_method(share) for share in query if not share.expired]
        return self.paginated_model(share_list, offset, limit, total_count)

    def _lookup_spawner(self, user_name, server_name, raise_404=True):
        """Lookup orm.Spawner for user_name/server_name

        raise 404 if not found
        """
        user = self.find_user(user_name)
        if user and server_name in user.orm_spawners:
            return user.orm_spawners[server_name]
        if raise_404:
            raise web.HTTPError(404, f"No such server: {user_name}/{server_name}")
        else:
            return None


class UserShareListAPIHandler(_ShareAPIHandler):
    """List shares a user has access to

    includes access granted via group membership
    """

    @needs_scope("read:users:shares")
    def get(self, user_name):
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404, f"No such user: {user_name}")
        query = self._init_share_query()
        filter = orm.Share.user == user
        if user.groups:
            filter = or_(
                orm.Share.user == user,
                orm.Share.group_id.in_([group.id for group in user.groups]),
            )
        query = query.filter(filter)
        self.finish(json.dumps(self._share_list_model(query)))


class UserShareAPIHandler(_ShareAPIHandler):
    def _lookup_share(self, user_name, owner_name, server_name):
        """Lookup the Share this URL represents

        raises 404 if not found
        """
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(
                404,
                f"No such share for user {user_name} on {owner_name}/{server_name}",
            )
        spawner = self._lookup_spawner(owner_name, server_name, raise_404=False)
        share = None
        if spawner:
            share = orm.Share.find(self.db, spawner, share_with=user.orm_user)
        if share is not None:
            return share
        else:
            raise web.HTTPError(
                404,
                f"No such share for user {user_name} on {owner_name}/{server_name}",
            )

    @needs_scope("read:users:shares")
    def get(self, user_name, owner_name, _server_name):
        share = self._lookup_share(user_name, owner_name, _server_name)
        self.finish(json.dumps(self.share_model(share)))

    @needs_scope("users:shares")
    def delete(self, user_name, owner_name, _server_name):
        share = self._lookup_share(user_name, owner_name, _server_name)
        self.db.delete(share)
        self.db.commit()
        self.set_status(204)


class GroupShareListAPIHandler(_ShareAPIHandler, _GroupAPIHandler):
    """List shares granted to a group"""

    @needs_scope("read:groups:shares")
    def get(self, group_name):
        group = self.find_group(group_name)
        query = self._init_share_query()
        query = query.filter(orm.Share.group == group)
        self.finish(json.dumps(self._share_list_model(query)))


class GroupShareAPIHandler(_ShareAPIHandler, _GroupAPIHandler):
    """A single group's access to a single server"""

    def _lookup_share(self, group_name, owner_name, server_name):
        """Lookup the Share this URL represents

        raises 404 if not found
        """
        group = self.find_group(group_name)
        spawner = self._lookup_spawner(owner_name, server_name, raise_404=False)
        share = None
        if spawner:
            share = orm.Share.find(self.db, spawner, share_with=group)
        if share is not None:
            return share
        else:
            raise web.HTTPError(
                404,
                f"No such share for group {group_name} on {owner_name}/{server_name}",
            )

    @needs_scope("read:groups:shares")
    def get(self, group_name, owner_name, _server_name):
        share = self._lookup_share(group_name, owner_name, _server_name)
        self.finish(json.dumps(self.share_model(share)))

    @needs_scope("groups:shares")
    def delete(self, group_name, owner_name, _server_name):
        share = self._lookup_share(group_name, owner_name, _server_name)
        self.db.delete(share)
        self.db.commit()
        self.set_status(204)


class ServerShareAPIHandler(_ShareAPIHandler):
    """Endpoint for shares of a single server

    This is where permissions are granted and revoked
    """

    @needs_scope("read:shares")
    def get(self, user_name, server_name=None):
        """List all shares for a given owner"""

        # TODO: optimize this query
        # we need Share and only the _names_ of users/groups,
        # no any other relationships
        query = self._init_share_query()
        if server_name is not None:
            spawner = self._lookup_spawner(user_name, server_name)
            query = query.filter_by(spawner_id=spawner.id)
        else:
            # lookup owner by id
            row = (
                self.db.query(orm.User.id)
                .where(orm.User.name == user_name)
                .one_or_none()
            )
            if row is None:
                raise web.HTTPError(404)
            owner_id = row[0]
            query = query.filter_by(owner_id=owner_id)
        self.finish(json.dumps(self._share_list_model(query)))

    @needs_scope('shares')
    async def post(self, user_name, server_name=None):
        """POST grants permissions for a given server"""

        if server_name is None:
            # only GET supported `/shares/{user}` without specified server
            raise web.HTTPError(405)

        model = self.get_json_body() or {}
        try:
            request = ShareGrantRequest(**model)
        except ValidationError as e:
            raise web.HTTPError(400, str(e))

        scopes = request.scopes
        # check scopes
        if not scopes:
            # default scopes
            scopes = [f"access:servers!server={user_name}/{server_name}"]

        # validate that scopes may be granted by requesting user
        try:
            scopes = orm.Share._apply_filter(frozenset(scopes), user_name, server_name)
        except ValueError as e:
            raise web.HTTPError(400, str(e))

        # resolve target spawner
        spawner = self._lookup_spawner(user_name, server_name)

        # check permissions
        for scope in scopes:
            if not self.has_scope(scope):
                raise web.HTTPError(
                    403, f"Do not have permission to grant share with scope {scope}"
                )

        if request.user:
            scope = f"read:users:name!user={request.user}"
            if not self.has_scope(scope):
                raise web.HTTPError(
                    403, "Need scope 'read:users:name' to share with users by name"
                )
            share_with = self.find_user(request.user)
            if share_with is None:
                raise web.HTTPError(400, f"No such user: {request.user}")
            share_with = share_with.orm_user
        elif request.group:
            if not self.has_scope(f"read:groups:name!group={request.group}"):
                raise web.HTTPError(
                    403, "Need scope 'read:groups:name' to share with groups by name"
                )
            share_with = orm.Group.find(self.db, name=request.group)
            if share_with is None:
                raise web.HTTPError(400, f"No such group: {request.group}")

        share = orm.Share.grant(self.db, spawner, share_with, scopes=scopes)
        self.finish(json.dumps(self.share_model(share)))

    @needs_scope('shares')
    async def patch(self, user_name, server_name=None):
        """PATCH revokes permissions from single shares for a given server"""

        if server_name is None:
            # only GET supported `/shares/{user}` without specified server
            raise web.HTTPError(405)

        model = self.get_json_body() or {}
        try:
            request = ShareRevokeRequest(**model)
        except ValidationError as e:
            raise web.HTTPError(400, str(e))

        # TODO: check allowed/valid scopes

        scopes = request.scopes

        # resolve target spawner
        spawner = self._lookup_spawner(user_name, server_name)

        if request.user:
            # don't need to check read:user permissions for revocation
            share_with = self.find_user(request.user)
            if share_with is None:
                # No such user is the same as revoking
                self.log.warning(f"No such user: {request.user}")
                self.finish("{}")
                return
            share_with = share_with.orm_user
        elif request.group:
            share_with = orm.Group.find(self.db, name=request.group)
            if share_with is None:
                # No such group behaves the same as revoking no permissions
                self.log.warning(f"No such group: {request.group}")
                self.finish("{}")
                return

        share = orm.Share.revoke(self.db, spawner, share_with, scopes=scopes)
        if share:
            self.finish(json.dumps(self.share_model(share)))
        else:
            # empty dict if share deleted
            self.finish("{}")

    @needs_scope('shares')
    async def delete(self, user_name, server_name=None):
        if server_name is None:
            # only GET supported `/shares/{user}` without specified server
            raise web.HTTPError(405)

        spawner = self._lookup_spawner(user_name, server_name)
        self.log.info(f"Deleting all shares for {user_name}/{server_name}")
        q = self.db.query(orm.Share).filter_by(
            spawner_id=spawner.id,
        )
        res = q.delete()
        self.log.info(f"Deleted {res} shares for {user_name}/{server_name}")
        self.db.commit()
        assert spawner.shares == []
        self.set_status(204)


class ServerShareCodeAPIHandler(_ShareAPIHandler):
    """Endpoint for managing sharing codes of a single server

    These codes can be exchanged for actual sharing permissions by the recipient.
    """

    @needs_scope("read:shares")
    def get(self, user_name, server_name=None):
        """List all share codes for a given owner"""

        query = self._init_share_query(kind="code")
        if server_name is None:
            # lookup owner by id
            row = (
                self.db.query(orm.User.id)
                .where(orm.User.name == user_name)
                .one_or_none()
            )
            if row is None:
                raise web.HTTPError(404)
            owner_id = row[0]

            query = query.filter_by(owner_id=owner_id)
        else:
            spawner = self._lookup_spawner(user_name, server_name)
            query = query.filter_by(spawner_id=spawner.id)
        self.finish(json.dumps(self._share_list_model(query, kind="code")))

    @needs_scope('shares')
    async def post(self, user_name, server_name=None):
        """POST creates a new share code"""

        if server_name is None:
            # only GET supported `/share-codes/{user}` without specified server
            raise web.HTTPError(405)

        model = self.get_json_body() or {}
        try:
            request = ShareCodeGrantRequest(**model)
        except ValidationError as e:
            raise web.HTTPError(400, str(e))

        scopes = request.scopes
        # check scopes
        if not scopes:
            # default scopes
            scopes = [f"access:servers!server={user_name}/{server_name}"]

        try:
            scopes = orm.ShareCode._apply_filter(
                frozenset(scopes), user_name, server_name
            )
        except ValueError as e:
            raise web.HTTPError(400, str(e))

        # validate that scopes may be granted by requesting user
        for scope in scopes:
            if not self.has_scope(scope):
                raise web.HTTPError(
                    403, f"Do not have permission to grant share with scope {scope}"
                )

        # resolve target spawner
        spawner = self._lookup_spawner(user_name, server_name)

        # issue the code
        (share_code, code) = orm.ShareCode.new(
            self.db, spawner, scopes=scopes, expires_in=request.expires_in
        )
        # return the model (including code only this one time when it's created)
        self.finish(json.dumps(self.share_code_model(share_code, code=code)))

    @needs_scope('shares')
    def delete(self, user_name, server_name=None):
        if server_name is None:
            # only GET supported `/share-codes/{user}` without specified server
            raise web.HTTPError(405)

        code = self.get_argument("code", None)
        share_id = self.get_argument("id", None)
        spawner = self._lookup_spawner(user_name, server_name)
        if code:
            # delete one code, identified by the code itself
            share_code = orm.ShareCode.find(self.db, code, spawner=spawner)
            if share_code is None:
                raise web.HTTPError(404, "No matching code found")
            else:
                self.log.info(f"Deleting share code for {user_name}/{server_name}")
                self.db.delete(share_code)
        elif share_id:
            m = _share_code_id_pat.match(share_id)
            four_o_four = f"No code found matching id={share_id}"
            if not m:
                raise web.HTTPError(404, four_o_four)
            share_id = int(m.group(1))
            share_code = (
                self.db.query(orm.ShareCode)
                .filter_by(
                    spawner_id=spawner.id,
                    id=share_id,
                )
                .one_or_none()
            )
            if share_code is None:
                raise web.HTTPError(404, four_o_four)
            else:
                self.log.info(f"Deleting share code for {user_name}/{server_name}")
                self.db.delete(share_code)
        else:
            self.log.info(f"Deleting all share codes for {user_name}/{server_name}")
            deleted = (
                self.db.query(orm.ShareCode)
                .filter_by(
                    spawner_id=spawner.id,
                )
                .delete()
            )
            self.log.info(
                f"Deleted {deleted} share codes for {user_name}/{server_name}"
            )
        self.db.commit()
        self.set_status(204)


default_handlers = [
    # TODO: not implementing single all-shared endpoint yet, too hard
    # (r"/api/shares", ShareListAPIHandler),
    # general management of shares
    (r"/api/shares/([^/]+)", ServerShareAPIHandler),
    (r"/api/shares/([^/]+)/([^/]*)", ServerShareAPIHandler),
    # list shared_with_me for users/groups
    (r"/api/users/([^/]+)/shared", UserShareListAPIHandler),
    (r"/api/groups/([^/]+)/shared", GroupShareListAPIHandler),
    # single-share endpoint (only for easy self-revocation, for now)
    (r"/api/users/([^/]+)/shared/([^/]+)/([^/]*)", UserShareAPIHandler),
    (r"/api/groups/([^/]+)/shared/([^/]+)/([^/]*)", GroupShareAPIHandler),
    # manage sharing codes
    (r"/api/share-codes/([^/]+)", ServerShareCodeAPIHandler),
    (r"/api/share-codes/([^/]+)/([^/]*)", ServerShareCodeAPIHandler),
]
