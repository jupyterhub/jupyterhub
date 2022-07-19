"""Role handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from ossaudiodev import SNDCTL_COPR_SENDMSG

from tornado import web

from .. import orm
from ..scopes import Scope, needs_scope
from .base import APIHandler


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

    @needs_scope('read:roles')
    def get(self, role_name):
        role = self.find_role(role_name)
        print(role)
        self.write(json.dumps(self.role_model(role)))

    @needs_scope('admin:groups')
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
        # check that everything exists
        scopes = model.get('scopes', [])
        servicenames = model.get('services', [])
        usernames = model.get('users', [])
        groupnames = model.pop("groups", [])
        # check if scopes exist
        if scopes:
            # avoid circular import
            from ..scopes import _check_scopes_exist

            try:
                _check_scopes_exist(scopes, who_for=f"role {role_name}")
            except:
                raise web.HTTPError(409, "One of the scopes does not exist")

        services = []
        for name in servicenames:
            existing = orm.Service.find(self.db, name=name)
            # Non existing groups are ignored and won't be created
            if existing is not None:
                services.append(existing)

        users = []
        for name in usernames:
            existing = orm.User.find(self.db, name=name)
            # Non existing groups are ignored and won't be created
            if existing is not None:
                users.append(existing)

        groups = []
        for name in groupnames:
            existing = orm.Group.find(self.db, name=name)
            # Non existing groups are ignored and won't be created
            if existing is not None:
                groups.append(existing)

        # create the role
        self.log.info("Creating new role %s with %i scopes", role_name, len(scopes))
        self.log.debug("Scopes: %s", scopes)
        role = orm.Role(
            name=role_name, scopes=scopes, groups=groups, services=services, users=users
        )
        print(role)
        self.db.add(role)
        self.db.commit()
        self.write(json.dumps(self.role_model(role)))
        self.set_status(201)

    @needs_scope('admin:groups')
    def put(self, role_name):
        """PUT edits a role"""
        model = self.get_json_body()
        if model is None:
            model = {}
        else:
            self._check_role_model(model)

        existing = orm.Role.find(self.db, name=role_name)
        if existing is None:
            raise web.HTTPError(409, "Role %s does not exist" % role_name)
        # check that everything exists
        scopes = model.get('scopes', [])
        servicenames = model.get('services', [])
        usernames = model.get('users', [])
        groupnames = model.pop("groups", [])
        # check if scopes exist
        if scopes:
            # avoid circular import
            from ..scopes import _check_scopes_exist

            try:
                _check_scopes_exist(scopes, who_for=f"role {role_name}")
            except:
                raise web.HTTPError(409, "One of the scopes does not exist")
        services = []
        for name in servicenames:
            existing = orm.Service.find(self.db, name=name)
            # Non existing groups are ignored and won't be created
            if existing is not None:
                services.append(existing)
        users = []
        for name in usernames:
            existing = orm.User.find(self.db, name=name)
            # Non existing groups are ignored and won't be created
            if existing is not None:
                users.append(existing)
        groups = []
        for name in groupnames:
            existing = orm.Group.find(self.db, name=name)
            # Non existing groups are ignored and won't be created
            if existing is not None:
                groups.append(existing)

        # create the role
        self.log.info("Editing role %s with %i scopes", role_name, len(scopes))
        self.log.debug("Scopes: %s", scopes)
        role = self.find_role(role_name)
        role.scopes = scopes
        role.groups = groups
        role.services = services
        role.users = users
        print(role)
        self.db.commit()
        self.write(json.dumps(self.role_model(role)))
        self.set_status(201)

    @needs_scope('delete:groups')
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
