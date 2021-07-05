"""Group handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from tornado import web

from .. import orm
from ..scopes import needs_scope
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

    def find_group(self, group_name):
        """Find and return a group by name.

        Raise 404 if not found.
        """
        group = orm.Group.find(self.db, name=group_name)
        if group is None:
            raise web.HTTPError(404, "No such group: %s", group_name)
        return group


class GroupListAPIHandler(_GroupAPIHandler):
    @needs_scope('read:groups', 'read:groups:name', 'read:roles:groups')
    def get(self):
        """List groups"""
        query = self.db.query(orm.Group)
        offset, limit = self.get_api_pagination()
        query = query.offset(offset).limit(limit)
        scope_filter = self.get_scope_filter('read:groups')
        data = [self.group_model(g) for g in query if scope_filter(g, kind='group')]
        self.write(json.dumps(data))

    @needs_scope('admin:groups')
    async def post(self):
        """POST creates Multiple groups"""
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

    @needs_scope('read:groups', 'read:groups:name', 'read:roles:groups')
    def get(self, group_name):
        group = self.find_group(group_name)
        self.write(json.dumps(self.group_model(group)))

    @needs_scope('admin:groups')
    async def post(self, group_name):
        """POST creates a group by name"""
        model = self.get_json_body()
        if model is None:
            model = {}
        else:
            self._check_group_model(model)

        existing = orm.Group.find(self.db, name=group_name)
        if existing is not None:
            raise web.HTTPError(409, "Group %s already exists" % group_name)

        usernames = model.get('users', [])
        # check that users exist
        users = self._usernames_to_users(usernames)

        # create the group
        self.log.info("Creating new group %s with %i users", group_name, len(users))
        self.log.debug("Users: %s", usernames)
        group = orm.Group(name=group_name, users=users)
        self.db.add(group)
        self.db.commit()
        self.write(json.dumps(self.group_model(group)))
        self.set_status(201)

    @needs_scope('admin:groups')
    def delete(self, group_name):
        """Delete a group by name"""
        group = self.find_group(group_name)
        self.log.info("Deleting group %s", group_name)
        self.db.delete(group)
        self.db.commit()
        self.set_status(204)


class GroupUsersAPIHandler(_GroupAPIHandler):
    """Modify a group's user list"""

    @needs_scope('groups')
    def post(self, group_name):
        """POST adds users to a group"""
        group = self.find_group(group_name)
        data = self.get_json_body()
        self._check_group_model(data)
        if 'users' not in data:
            raise web.HTTPError(400, "Must specify users to add")
        self.log.info("Adding %i users to group %s", len(data['users']), group_name)
        self.log.debug("Adding: %s", data['users'])
        for user in self._usernames_to_users(data['users']):
            if user not in group.users:
                group.users.append(user)
            else:
                self.log.warning("User %s already in group %s", user.name, group_name)
        self.db.commit()
        self.write(json.dumps(self.group_model(group)))

    @needs_scope('groups')
    async def delete(self, group_name):
        """DELETE removes users from a group"""
        group = self.find_group(group_name)
        data = self.get_json_body()
        self._check_group_model(data)
        if 'users' not in data:
            raise web.HTTPError(400, "Must specify users to delete")
        self.log.info("Removing %i users from group %s", len(data['users']), group_name)
        self.log.debug("Removing: %s", data['users'])
        for user in self._usernames_to_users(data['users']):
            if user in group.users:
                group.users.remove(user)
            else:
                self.log.warning(
                    "User %s already not in group %s", user.name, group_name
                )
        self.db.commit()
        self.write(json.dumps(self.group_model(group)))


default_handlers = [
    (r"/api/groups", GroupListAPIHandler),
    (r"/api/groups/([^/]+)", GroupAPIHandler),
    (r"/api/groups/([^/]+)/users", GroupUsersAPIHandler),
]
