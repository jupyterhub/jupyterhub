"""Authorization handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from tornado import gen, web

from .. import orm
from ..utils import admin_only, authenticated_403
from .base import APIHandler

class BaseUserHandler(APIHandler):
    
    def user_model(self, user):
        return {
            'name': user.name,
            'admin': user.admin,
            'server': user.server.base_url if user.server else None,
            'last_activity': user.last_activity.isoformat(),
        }
    
    _model_types = {
        'name': str,
        'admin': bool,
    }
    
    def _check_user_model(self, model):
        if not isinstance(model, dict):
            raise web.HTTPError(400, "Invalid JSON data: %r" % model)
        if not set(model).issubset(set(self._model_types)):
            raise web.HTTPError(400, "Invalid JSON keys: %r" % model)
        for key, value in model.items():
            if not isinstance(value, self._model_types[key]):
                raise web.HTTPError(400, "user.%s must be %s, not: %r" % (
                    key, self._model_types[key], type(value)
                ))

class UserListAPIHandler(BaseUserHandler):
    @admin_only
    def get(self):
        users = self.db.query(orm.User)
        data = [ self.user_model(u) for u in users ]
        self.write(json.dumps(data))


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

class UserAPIHandler(BaseUserHandler):
    
    @admin_or_self
    def get(self, name):
        user = self.find_user(name)
        self.write(json.dumps(self.user_model(user)))
    
    @admin_only
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
            self.authenticator.add_user(user)
        except Exception:
            self.log.error("Failed to create user: %s" % name, exc_info=True)
            self.db.delete(user)
            self.db.commit()
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
        if user.spawner is not None:
            yield self.stop_single_user(user)
        
        self.authenticator.delete_user(user)
        
        # remove from the db
        self.db.delete(user)
        self.db.commit()
        
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


class UserServerAPIHandler(BaseUserHandler):
    @gen.coroutine
    @admin_or_self
    def post(self, name):
        user = self.find_user(name)
        if user.spawner:
            state = yield user.spawner.poll()
            if state is None:
                raise web.HTTPError(400, "%s's server is already running" % name)

        yield self.spawn_single_user(user)
        self.set_status(201)

    @gen.coroutine
    @admin_or_self
    def delete(self, name):
        user = self.find_user(name)
        if user.spawner is None:
            raise web.HTTPError(400, "%s's server is not running" % name)
        yield self.stop_single_user(user)
        self.set_status(204)

default_handlers = [
    (r"/api/users", UserListAPIHandler),
    (r"/api/users/([^/]+)", UserAPIHandler),
    (r"/api/users/([^/]+)/server", UserServerAPIHandler),
]
