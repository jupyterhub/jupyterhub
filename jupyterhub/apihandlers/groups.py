"""Group handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from tornado import web

from .. import orm
from ..utils import admin_only
from .base import APIHandler


class _GroupAPIHandler(APIHandler):
    def _usernames_to_users(self, usernames):
        """Turn a list of usernames into user objects"""
        users = []
        for username in usernames:
            username = self.authenticator.normalize_username(username)
            user = self.find_user(username)
            if user is None:
                raise web.HTTPError(400, "No such user: %s" % username)
            users.append(user.orm_user)
        return users

    def find_group(self, name):
        """Find and return a group by name.

        Raise 404 if not found.
        """
        group = orm.Group.find(self.db, name=name)
        if group is None:
            raise web.HTTPError(404, "No such group: %s", name)
        return group


class GroupListAPIHandler(_GroupAPIHandler):
    @admin_only
    def get(self):
        """List groups"""
        data = [self.group_model(g) for g in self.db.query(orm.Group)]
        self.write(json.dumps(data))

    @admin_only
    async def post(self):
        """POST creates Multiple groups """
        model = self.get_json_body()
        if not model or not isinstance(model, dict) or not model.get('groups'):
            raise web.HTTPError(400, "Must specify at least one group to create")

        groupnames = model.pop("groups", [])
        self._check_group_model(model)

        created = []
        for name in groupnames:
            existing = orm.Group.find(self.db, name=name)
            if existing is not None:
                raise web.HTTPError(409, "Group %s already exists" % name)

            usernames = model.get('users', [])
            # check that users exist
            users = self._usernames_to_users(usernames)
            # create the group
            self.log.info("Creating new group %s with %i users", name, len(users))
            self.log.debug("Users: %s", usernames)
            group = orm.Group(name=name, users=users)
            self.db.add(group)
            self.db.commit()
            created.append(group)
        self.write(json.dumps([self.group_model(group) for group in created]))
        self.set_status(201)


class GroupAPIHandler(_GroupAPIHandler):
    """View and modify groups by name"""

    @admin_only
    def get(self, name):
        group = self.find_group(name)
        self.write(json.dumps(self.group_model(group)))

    @admin_only
    async def post(self, name):
        """POST creates a group by name"""
        model = self.get_json_body()
        if model is None:
            model = {}
        else:
            self._check_group_model(model)

        existing = orm.Group.find(self.db, name=name)
        if existing is not None:
            raise web.HTTPError(409, "Group %s already exists" % name)

        usernames = model.get('users', [])
        # check that users exist
        users = self._usernames_to_users(usernames)

        # create the group
        self.log.info("Creating new group %s with %i users", name, len(users))
        self.log.debug("Users: %s", usernames)
        group = orm.Group(name=name, users=users)
        self.db.add(group)
        self.db.commit()
        self.write(json.dumps(self.group_model(group)))
        self.set_status(201)

    @admin_only
    def delete(self, name):
        """Delete a group by name"""
        group = self.find_group(name)
        self.log.info("Deleting group %s", name)
        self.db.delete(group)
        self.db.commit()
        self.set_status(204)


class GroupUsersAPIHandler(_GroupAPIHandler):
    """Modify a group's user list"""

    @admin_only
    def post(self, name):
        """POST adds users to a group"""
        group = self.find_group(name)
        data = self.get_json_body()
        self._check_group_model(data)
        if 'users' not in data:
            raise web.HTTPError(400, "Must specify users to add")
        self.log.info("Adding %i users to group %s", len(data['users']), name)
        self.log.debug("Adding: %s", data['users'])
        for user in self._usernames_to_users(data['users']):
            if user not in group.users:
                group.users.append(user)
            else:
                self.log.warning("User %s already in group %s", user.name, name)
        self.db.commit()
        self.write(json.dumps(self.group_model(group)))

    @admin_only
    async def delete(self, name):
        """DELETE removes users from a group"""
        group = self.find_group(name)
        data = self.get_json_body()
        self._check_group_model(data)
        if 'users' not in data:
            raise web.HTTPError(400, "Must specify users to delete")
        self.log.info("Removing %i users from group %s", len(data['users']), name)
        self.log.debug("Removing: %s", data['users'])
        for user in self._usernames_to_users(data['users']):
            if user in group.users:
                group.users.remove(user)
            else:
                self.log.warning("User %s already not in group %s", user.name, name)
        self.db.commit()
        self.write(json.dumps(self.group_model(group)))


default_handlers = [
    (r"/api/groups", GroupListAPIHandler),
    (r"/api/groups/([^/]+)", GroupAPIHandler),
    (r"/api/groups/([^/]+)/users", GroupUsersAPIHandler),
]
