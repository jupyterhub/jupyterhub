"""Group handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from sqlalchemy import and_, or_
from tornado import web

from .. import orm
from ..scopes import Scope, needs_scope
from ..utils import utcnow
from .base import APIHandler


class _ShareAPIHandler(APIHandler):
    def server_model(self, spawner):
        """Truncated server model for use in shares
        
        - Adds "user" field (just name for now)
        - Limits fields to "name", "url", "ready", "active"
          from standard server model
        """
        full_model = super().server_model(spawner)
        # filter out subset of fields
        server_model = {
            "user": {
                name: spawner.user.name,
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
            "created_at": share.created_at,
        }
    
    def share_code_model(self, share_code):
        """Compute the REST API model for a share code"""
        return {
            "server": self.server_model(share_code.spawner),
            "scopes": share_code.scopes,
            "code": share_code.code,
            "created_at": share_code.created_at,
            "expires_at": share_code.expires_at,
        }
        

class ShareListAPIHandler(_ShareAPIHandler):

    @needs_scope("read:shares")
    def get(self, user_name, server_name):
        """List all shares for a given owner"""
        query = full_query = (
            self.db.query(orm.Share)
            .outerjoin(orm.User, orm.Share.user)
            .outerjoin(orm.Spawner, orm.Share.spawner)
        )
        
        if not user_name:
            # get all shares
            # not implemented
            raise NotImplementedError()
        else:
            # all shares for one user
            query = query.filter(orm.Share.owner.has(name=user_name))
        
        # permission filters for single all-users list of shares
        # sub_scope = self.parsed_scopes['read:shares']
        # if sub_scope != Scope.ALL:
        #     filters = []
        #     # filter groups
        #     if 'group' in sub_scope:
        #         # filter groups
        #         query = query.outerjoin(orm.Group, orm.User.groups)
        #         filters.append(orm.Group.name.in_(set(sub_scope['group'])))
        #     if 'user' in sub_scope:
        #         # filter users
        #         filters.append(orm.User.name.in_(set(sub_scope['user'])))
        #     if 'server' in sub_scope:
        #         # filter servers
        #         for user_server in sub_scope['server']:
        #             username, _, servername = user_server.partition("/")
        #             filters.append(
        #                 and_(orm.User.name == username, orm.Spawner.name ==     servername)
        #             )
        #     
        #     if filters:
        #         query = query.filter(or_(*filters))
        
        scope_filter = self.get_scope_filter("read:shares")
        offset, limit = self.get_api_pagination()

        total_count = query.count()
        query = query.order_by(orm.Share.id.asc()).offset(offset).limit(limit)
        share_list = [self.share_model(share) for share in query]
        model = self.paginated_model(group_list, offset, limit, total_count)
        self.write(json.dumps(model))

class ShareCodeListAPIHandler(_ShareAPIHandler):

    @needs_scope("read:share-codes")
    def get(self, user_name, server_name):
        raise NotImplementedError()

class UserShareListAPIHandler(ShareListAPIHandler):
    """List shares granted to a user"""
    
    @needs_scope("read:users:shares")
    def get(self, user_name):
        raise NotImplementedError()

class GroupShareListAPIHandler(ShareListAPIHandler):
    """List shares granted to a user"""
    
    @needs_scope("read:groups:shares")
    def get(self, group_name):
        raise NotImplementedError()
        
class ServerShareAPIHandler(_ShareAPIHandler):
    """Endpoint for shares of a single server
    
    This is where permissions are granted and revoked
    """
    @needs_scope('read:shares')
    async def get(self, user_name, server_name):
        # list shares for the target server
        query = self.db.query(orm.Share)
        
        raise NotImplementedError()
    
    def _check_share_request_model(self, model):
        """
        Check the share-request model
        
        Validates and normalizes the model
        
        all keys will be populated with default values.
        """
        
        if not model or not isinstance(model, dict):
            raise web.HTTPError(400, "Must specify users or server")
        
        allowed_keys = {"scopes", "grant", "revoke"}
        disallowed_keys = set(model.keys()).difference(allowed_keys)
        if disallowed_keys:
            raise web.HTTPError(400, f"Only {allowed_keys} allowed, got {disallowed_keys}")
        # TODO: check grant and revoke
        if not set(model.keys()).issubset({"grant", "revoke"}):
            raise web.HTTPError(400, f"Must specify at least one of 'grant' or 'revoke'")
        for key in ("grant", "revoke"):
            if key in model:
                grant_model = model[key]
                if not isinstance(model, dict):
                    raise web.HTTPError(400, f"{key} must be a dict, not {grant_model}")
                disallowed_keys = set(grant_model.keys()).difference({"users", "groups"})
                if disallowed_keys:
                    raise web.HTTPError(400, f"{key} only accepts 'users' and 'groups', not {disallowed_keys}")
                for grant_list_key in ("users", "groups"):
                    if grant_list_key not in grant_model:
                        continue
                    to_grant = grant_model[grant_list_key]
                    if not isinstance(to_grant, list) and not all(
                        isinstance(name, str) for name in to_grant
                    ):
                    raise web.HTTPError(400, f"{key}[{grant_list_key}] must be a list of names, not {to_grant}")

    @needs_scope('shares')
    async def patch(self, user_name, server_name):
        """PATCH modifies shares for a given server"""
        model = self.get_json_body()
        self._check_share_model(model)
        
        scopes = model.get("scopes")
        # check scopes
        if not scopes:
            scopes = ["access:servers!server={user_name}/{server_name}"]
            
        # TODO: check allowed/valid scopes
        
        # resolve target spawner
        # TODO: check if it exists
        target_user = self.find_user(user_name)
        spawner = targer_user.orm_spawners[server_name]
        
        if "grant" in model:
            now = utcnow()
            to_grant = model["grant"]
            kwargs = dict(
                created_at=now,
                spawner=spawner,
                scopes=scopes,
            )
            # FIXME: depending on how we handle this,
            # the share API allows discovery of users and groups
            # TODO: check valid usernames?
            # as it is now, invalid names simply have no effect
            # (e.g. check in_ query count has length == to_grant list)
            if to_grant.get("users"):
                for user in self.db.query(orm.User).filter(orm.User.name.in_(to_grant["users"])):
                    orm.Share.grant(self.db, spawner, user, scopes)
            if to_grant.get("groups"):
                for group in self.db.query(orm.Group).filter(orm.Group.name.in_(to_grant["groups"])):
                    orm.Share.grant(self.db, spawner, group, scopes)

        if "revoke" in model:
            to_revoke_query = self.db.query(orm.Share).filter_by(spawner_id=spawner.id)
            to_revoke = model["revoke"]
            if to_revoke.get("users"):
                for share in to_revoke_query.filter(orm.Share.owner
            for share in to_revoke_query:
                self.log.info(f"Deleting share {share}")
                self.db.delete(share)
                
            to_revoke = model["revoke"]
            # query and delete Shares with user and/or group
        
        # this modifies permissions, so there isn't a single model to return
        # so return nothing
        self.set_status(201)





default_handlers = [
    # TODO: not implementing single all-shared endpoint yet
    # too hard
    # (r"/api/shares", ShareListAPIHandler),
    (r"/api/shares/([^/]+)", ShareListAPIHandler),
    (r"/api/shares/([^/]+)/([^/]*)", ServerShareAPIHandler),
    (r"/api/users/([^/]+)/shares", UserShareListAPIHandler),
    (r"/api/groups/([^/]+)/shares", GroupShareListAPIHandler),
]
