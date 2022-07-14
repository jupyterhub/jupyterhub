"""Role handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from tornado import web

from .. import orm
from ..scopes import Scope, needs_scope
from .base import APIHandler

def convertTuple(tup):
        str = ''
        for item in tup:
            str = str + item
        return str

class _RoleAPIHandler(APIHandler):
  
    def find_role(self, role_name):
        """Find and return a role by name.

        Raise 404 if not found.
        """
        role = orm.Role.find(self.db, name=role_name)
        if role is None:
            raise web.HTTPError(404, "No such role: %s", role_name)
        return role


class RoleAPIHandler(_RoleAPIHandler):
    """View and modify roles by name"""
    
    @needs_scope('read:roles', 'read:roles:name')
    def get(self, role_name):
        role = self.find_role(role_name)
        self.write(json.dumps(self.role_model(role)))

    @needs_scope('admin:roles')
    async def post(self, role_name):
        """POST creates a role"""
        model = self.get_json_body()
        if model is None:
            model = {}
        else:
            self._check_role_model(model)

        existing = orm.Role.find(self.db, name=role_name)
        if existing is not None:
            raise web.HTTPError(409, "Role %s already exists" % role_name)

        scopes = model.get('scopes', [])
        # check that groups exist
        groupnames = model.pop("groups", [])
        groups=[]
        for name in groupnames:
            existing = orm.Group.find(self.db, name=name)
            if existing is not None:
                groups.append(existing)
            else:
                print(Exception)
        # create the role
        self.log.info("Creating new role %s with %i scopes", role_name, len(scopes))
        self.log.debug("Scopes: %s", scopes)
        role = orm.Role(name=role_name, scopes=scopes, groups = groups)
        self.db.add(role)
        self.db.commit()
        self.write(json.dumps(self.role_model(role)))
        self.set_status(201)
    
        
    @needs_scope('delete:roles')
    def delete(self, role_name):
        """Delete a role by name"""
        role = self.find_role(role_name)
        self.log.info("Deleting role %s", role_name)
        self.db.delete(role)
        self.db.commit()
        self.set_status(204)



default_handlers = [
    (r"/api/roles/([^/]+)", RoleAPIHandler),
]
