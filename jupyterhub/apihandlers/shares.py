"""Group handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlalchemy import or_
from tornado import web

from .. import orm
from ..scopes import _check_scope_access, _check_scopes_exist, needs_scope
from ..utils import isoformat
from .base import APIHandler
from .groups import _GroupAPIHandler


class ShareGrantRequest(BaseModel):
    """Validator for requests to grant sharing permission"""

    model_config = ConfigDict(extra='forbid')
    scopes: Optional[List[str]] = None
    user: Optional[str] = None
    group: Optional[str] = None

    @field_validator("scopes")
    @classmethod
    def _check_scopes_exist(cls, scopes):
        _check_scopes_exist(scopes)

    @model_validator(mode='after')
    def user_group_exclusive(self):
        if self.user and self.group:
            raise ValueError("Expected exactly one of `user` or `group`, not both.")
        if self.user is None and self.group is None:
            raise ValueError("Specify exactly one of `user` or `group`")
        return self


class ShareRevokeRequest(BaseModel):
    """Validator for `revoke` field of requests to revoke shares"""

    model_config = ConfigDict(extra='forbid')
    scopes: Optional[List[str]] = None
    user: Optional[str] = None
    group: Optional[str] = None

    @field_validator("scopes")
    @classmethod
    def _check_scopes_exist(cls, scopes):
        _check_scopes_exist(scopes)

    @model_validator(mode='after')
    def user_group_exclusive(self):
        if self.user and self.group:
            raise ValueError("Expected exactly one of `user` or `group`, not both.")
        if self.user is None and self.group is None:
            raise ValueError("Specify exactly one of `user` or `group`")
        return self


class _ShareAPIHandler(APIHandler):
    def server_model(self, spawner):
        """Truncated server model for use in shares

        - Adds "user" field (just name for now)
        - Limits fields to "name", "url", "ready", "active"
          from standard server model
        """
        user = self.users[spawner.user]
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
        for key in ["name", "url", "ready", "active"]:
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
            "created_at": isoformat(share.created_at),
        }

    def share_code_model(self, share_code):
        """Compute the REST API model for a share code"""
        return {
            "server": self.server_model(share_code.spawner),
            "scopes": share_code.scopes,
            "code": share_code.code,
            "created_at": isoformat(share_code.created_at),
            "expires_at": isoformat(share_code.expires_at),
        }

    def _init_share_query(self):
        """Initialize a query for Shares

        before applying filters

        A method so we can consolidate joins, etc.
        """
        query = (
            self.db.query(orm.Share)
            .outerjoin(orm.User, orm.Share.user)
            .outerjoin(orm.User, orm.Share.owner)
            .join(orm.Spawner, orm.Share.spawner)
        )
        return query

    def _share_list_model(self, query):
        """Finish a share query, returning the _model_"""
        offset, limit = self.get_api_pagination()

        total_count = query.count()
        query = query.order_by(orm.Share.id.asc()).offset(offset).limit(limit)
        share_list = [self.share_model(share) for share in query]
        return self.paginated_model(share_list, offset, limit, total_count)

    def _lookup_spawner(self, user_name, server_name, raise_404=True):
        """Lookup orm.Spawner for user_name/server_name

        raise 404 if not found
        """
        user = self.find_user(user_name)
        if user and server_name in user.orm_spawners:
            return user.orm_spawners[server_name]
        if raise_404:
            raise web.HTTPError(404, f"No such server: {user.name}/{server_name}")
        else:
            return None


class UserShareListAPIHandler(_ShareAPIHandler):
    """List shares a user has access to

    includes access granted via group membership
    """

    @needs_scope("read:users:shares")
    def get(self, user_name):
        query = self._init_share_query()
        user = self.find_user(user_name)
        if user is None:
            raise web.HTTPError(404, f"No such user: {user_name}")
        filter = orm.Share.user == user
        if user.groups:
            filter = or_(orm.Share.user == user, orm.Share.group in user.groups)
        query = query.filter(filter)
        # TODO: should this include access granted via group?
        self.finish(self._share_list_model(query))


class GroupShareListAPIHandler(_ShareAPIHandler, _GroupAPIHandler):
    """List shares granted to a group"""

    @needs_scope("read:groups:shares")
    def get(self, group_name):
        group = self.find_group(group_name)
        query = self._init_share_query()
        query = query.filter(orm.Share.group == group)
        self.finish(self._share_list_model(query))


class GroupShareServerAPIHandler(_ShareAPIHandler, _GroupAPIHandler):
    @needs_scope("groups:shares")
    def delete(self, group_name, _user_name, _server_name):
        group = self.find_group(group_name)
        spawner = self._lookup_spawner(_user_name, _server_name, raise_404=False)
        share = None
        if spawner:
            share = orm.Share.find(self.db, spawner, share_with=group)
        if share is not None:
            self.db.delete(share)
            self.set_status(204)
        else:
            raise web.HTTPError(
                404,
                f"No such share for group {group_name} on {_user_name}/{_server_name}",
            )


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
        if server_name is None:
            raise NotImplementedError("Haven't implemented listing user shares")
        spawner = self._lookup_spawner(user_name, server_name)

        query = query.filter_by(spawner_id=spawner.id)
        self.finish(self._share_list_model(query))

    @needs_scope('admin:shares')
    async def post(self, user_name, server_name):
        """PATCH modifies shares for a given server"""
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

        # resolve target spawner
        spawner = self._lookup_spawner(user_name, server_name)

        # validate that scopes may be granted by requesting user
        orm.Share.verify_scopes(scopes, self.current_user, spawner)

        if request.user:
            if not _check_scope_access(self, "read:users:name", user=request.user):
                raise web.HTTPError(
                    403, "Need scope 'read:users:name' to share with users by name"
                )
            share_with = self.find_user(request.user)
            if share_with is None:
                raise web.HTTPError(400, f"No such user: {request.user}")
            share_with = share_with.orm_user
        elif request.group:
            if not _check_scope_access(self, "read:groups:name", group=request.group):
                raise web.HTTPError(
                    403, "Need scope 'read:groups:name' to share with groups by name"
                )
            share_with = orm.Group.find(self.db, name=request.group)
            if share_with is None:
                raise web.HTTPError(400, f"No such group: {request.group}")

        share = orm.Share.grant(self.db, spawner, share_with, scopes=scopes)
        self.finish(json.dumps(self.share_model(share)))

    @needs_scope('admin:shares')
    async def patch(self, user_name, server_name):
        """PATCH revokes single shares for a given server"""
        model = self.get_json_body() or {}
        try:
            request = ShareRevokeRequest(**model)
        except ValidationError as e:
            raise web.HTTPError(400, str(e))

        # TODO: check allowed/valid scopes

        scopes = request.scopes
        # check scopes
        if not scopes:
            # default scopes
            scopes = [f"access:servers!server={user_name}/{server_name}"]
        # TODO: check allowed/valid scopes
        scopes = set(scopes)

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

    @needs_scope('admin:shares')
    async def delete(self, user_name, server_name):
        spawner = self._lookup_spawner(user_name, server_name)
        spawner.shares = []
        self.db.commit()
        self.set_status(204)


default_handlers = [
    # TODO: not implementing single all-shared endpoint yet, too hard
    # (r"/api/shares", ShareListAPIHandler),
    # general management of shares
    # (r"/api/shares/([^/]+)", ServerShareAPIHandler),
    (r"/api/shares/([^/]+)/([^/]*)", ServerShareAPIHandler),
    # list shared_with_me for users/groups
    (r"/api/users/([^/]+)/shared", UserShareListAPIHandler),
    (r"/api/groups/([^/]+)/shared", GroupShareListAPIHandler),
    # single-share endpoint (only for easy revocation, for now)
    # (r"/api/users/([^/]+)/shared/([^/]+)/([^/]*)", UserShareAPIHandler),
    # (r"/api/groups/([^/]+)/shared/([^/]+)/([^/]*)", GroupShareAPIHandler),
]
