"""User handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from tornado import gen, web

from .. import orm
from ..utils import admin_only
from .base import APIHandler


class UserListAPIHandler(APIHandler):
    @admin_only
    def get(self):
        users = [ self._user_from_orm(u) for u in self.db.query(orm.User) ]
        data = [ self.user_model(u) for u in users ]
        self.write(json.dumps(data))
    
    @admin_only
    @gen.coroutine
    def post(self):
        data = self.get_json_body()
        if not data or not isinstance(data, dict) or not data.get('usernames'):
            raise web.HTTPError(400, "Must specify at least one user to create")
        
        usernames = data.pop('usernames')
        self._check_user_model(data)
        # admin is set for all users
        # to create admin and non-admin users requires at least two API requests
        admin = data.get('admin', False)
        
        to_create = []
        invalid_names = []
        for name in usernames:
            name = self.authenticator.normalize_username(name)
            if not self.authenticator.validate_username(name):
                invalid_names.append(name)
                continue
            user = self.find_user(name)
            if user is not None:
                self.log.warning("User %s already exists" % name)
            else:
                to_create.append(name)
        
        if invalid_names:
            if len(invalid_names) == 1:
                msg = "Invalid username: %s" % invalid_names[0]
            else:
                msg = "Invalid usernames: %s" % ', '.join(invalid_names)
            raise web.HTTPError(400, msg)
        
        if not to_create:
            raise web.HTTPError(400, "All %i users already exist" % len(usernames))
        
        created = []
        for name in to_create:
            user = self.user_from_username(name)
            if admin:
                user.admin = True
                self.db.commit()
            try:
                yield gen.maybe_future(self.authenticator.add_user(user))
            except Exception as e:
                self.log.error("Failed to create user: %s" % name, exc_info=True)
                del self.users[user]
                raise web.HTTPError(400, "Failed to create user %s: %s" % (name, str(e)))
            else:
                created.append(user)
        
        self.write(json.dumps([ self.user_model(u) for u in created ]))
        self.set_status(201)


def admin_or_self(method):
    """Decorator for restricting access to either the target user or admin"""
    def m(self, name):
        current = self.get_current_user()
        if current is None:
            raise web.HTTPError(403)
        if not (current.name == name or current.admin):
            raise web.HTTPError(403)
        
        # raise 404 if not found
        if not self.find_user(name):
            raise web.HTTPError(404)
        return method(self, name)
    return m

class UserAPIHandler(APIHandler):
    
    @admin_or_self
    def get(self, name):
        user = self.find_user(name)
        self.write(json.dumps(self.user_model(user)))
    
    @admin_only
    @gen.coroutine
    def post(self, name):
        data = self.get_json_body()
        user = self.find_user(name)
        if user is not None:
            raise web.HTTPError(400, "User %s already exists" % name)
        
        user = self.user_from_username(name)
        if data:
            self._check_user_model(data)
            if 'admin' in data:
                user.admin = data['admin']
                self.db.commit()
        
        try:
            yield gen.maybe_future(self.authenticator.add_user(user))
        except Exception:
            self.log.error("Failed to create user: %s" % name, exc_info=True)
            # remove from registry
            del self.users[user]
            raise web.HTTPError(400, "Failed to create user: %s" % name)
        
        self.write(json.dumps(self.user_model(user)))
        self.set_status(201)
    
    @admin_only
    @gen.coroutine
    def delete(self, name):
        user = self.find_user(name)
        if user is None:
            raise web.HTTPError(404)
        if user.name == self.get_current_user().name:
            raise web.HTTPError(400, "Cannot delete yourself!")
        if user.stop_pending:
            raise web.HTTPError(400, "%s's server is in the process of stopping, please wait." % name)
        if user.running:
            yield self.stop_single_user(user)
            if user.stop_pending:
                raise web.HTTPError(400, "%s's server is in the process of stopping, please wait." % name)
        
        yield gen.maybe_future(self.authenticator.delete_user(user))
        # remove from registry
        del self.users[user]
        
        self.set_status(204)
    
    @admin_only
    def patch(self, name):
        user = self.find_user(name)
        if user is None:
            raise web.HTTPError(404)
        data = self.get_json_body()
        self._check_user_model(data)
        for key, value in data.items():
            setattr(user, key, value)
        self.db.commit()
        self.write(json.dumps(self.user_model(user)))


class UserServerAPIHandler(APIHandler):
    @gen.coroutine
    @admin_or_self
    def post(self, name):
        user = self.find_user(name)
        if user.running:
            # include notify, so that a server that died is noticed immediately
            state = yield user.spawner.poll_and_notify()
            if state is None:
                raise web.HTTPError(400, "%s's server is already running" % name)

        options = self.get_json_body()
        yield self.spawn_single_user(user, options=options)
        status = 202 if user.spawn_pending else 201
        self.set_status(status)

    @gen.coroutine
    @admin_or_self
    def delete(self, name):
        user = self.find_user(name)
        if user.stop_pending:
            self.set_status(202)
            return
        if not user.running:
            raise web.HTTPError(400, "%s's server is not running" % name)
        # include notify, so that a server that died is noticed immediately
        status = yield user.spawner.poll_and_notify()
        if status is not None:
            raise web.HTTPError(400, "%s's server is not running" % name)
        yield self.stop_single_user(user)
        status = 202 if user.stop_pending else 204
        self.set_status(status)

class UserAdminAccessAPIHandler(APIHandler):
    """Grant admins access to single-user servers
    
    This handler sets the necessary cookie for an admin to login to a single-user server.
    """
    @admin_only
    def post(self, name):
        current = self.get_current_user()
        self.log.warning("Admin user %s has requested access to %s's server",
            current.name, name,
        )
        if not self.settings.get('admin_access', False):
            raise web.HTTPError(403, "admin access to user servers disabled")
        user = self.find_user(name)
        if user is None:
            raise web.HTTPError(404)
        if not user.running:
            raise web.HTTPError(400, "%s's server is not running" % name)
        self.set_server_cookie(user)
        current.other_user_cookies.add(name)


default_handlers = [
    (r"/api/users", UserListAPIHandler),
    (r"/api/users/([^/]+)", UserAPIHandler),
    (r"/api/users/([^/]+)/server", UserServerAPIHandler),
    (r"/api/users/([^/]+)/admin-access", UserAdminAccessAPIHandler),
]
