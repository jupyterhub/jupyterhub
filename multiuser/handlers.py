"""HTTP Handlers for the multi-user server"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import json
import re

from tornado.log import app_log
from tornado.escape import url_escape
from tornado.httputil import url_concat
from tornado.web import RequestHandler
from tornado import web


class BaseHandler(RequestHandler):
    """Base Handler class with access to common methods and properties."""
    @property
    def cookie_name(self):
        return self.settings.get('cookie_name', 'cookie')
    
    @property
    def multiuser_url(self):
        return self.settings.get('multiuser_url', '')
    
    @property
    def multiuser_prefix(self):
        return self.settings.get('multiuser_prefix', '/multiuser/')
    
    def get_current_user(self):
        if 'get_current_user' in self.settings:
            return self.settings['get_current_user']
        
        token = self.get_cookie(self.cookie_name, '')
        if token:
            session = self.user_manager.user_for_cookie_token(token)
            if session:
                return session.user
    
    @property
    def base_url(self):
        return self.settings.setdefault('base_url', '/')
    
    @property
    def user_manager(self):
        return self.settings['user_manager']
    
    def clear_login_cookie(self):
        self.clear_cookie(self.cookie_name)
    
    def spawn_single_user(self, user):
        session = self.user_manager.get_session(user,
            cookie_secret=self.settings['cookie_secret'],
            multiuser_api_url=self.settings['multiuser_api_url'],
            multiuser_prefix=self.settings['multiuser_prefix'],
        )
        self.user_manager.spawn(user)
        return session


class RootHandler(BaseHandler):
    """Redirect from / to /user/foo/ after logging in."""
    @web.authenticated
    def get(self):
        self.redirect("/user/%s/" % self.get_current_user())


class UserHandler(BaseHandler):
    """Respawn single-user server after logging in.
    
    This handler shouldn't be called if the proxy is set up correctly.
    """
    @web.authenticated
    def get(self, user):
        self.log.debug("multi-user at single-user url: %s", user)
        if self.get_current_user() == user:
            self.spawn_single_user(user)
            self.redirect('')
        else:
            self.clear_login_cookie()
            self.redirect(url_concat(self.settings['login_url'], {
                'next' : '/user/%s/' % user
            }))


class LogoutHandler(BaseHandler):
    """Log a user out by clearing their login cookie."""
    def get(self):
        self.clear_login_cookie()
        self.write("logged out")

class LoginHandler(BaseHandler):
    """Render the login page."""

    def _render(self, message=None, user=None):
        self.render('login.html',
                next=url_escape(self.get_argument('next', default='')),
                user=user,
                message=message,
        )

    def get(self):
        if False and self.get_current_user():
            self.redirect(self.get_argument('next', default='/'))
        else:
            user = self.get_argument('user', default='')
            self._render(user=user)

    def post(self):
        user = self.get_argument('user', default='')
        pwd = self.get_argument('password', default=u'')
        next_url = self.get_argument('next', default='') or '/user/%s/' % user
        if user and pwd == 'password':
            if user not in self.user_manager.users:
                session = self.spawn_single_user(user)
            else:
                session = self.user_manager.users[user]
            cookie_token = session.cookie_token
            self.set_cookie(session.cookie_name, cookie_token, path=session.url_prefix)
            self.set_cookie(self.cookie_name, cookie_token, path=self.base_url)
        else:
            self._render(
                message={'error': 'Invalid username or password'},
                user=user,
            )
            return

        self.redirect(next_url)

#------------------------------------------------------------------------------
# API Handlers
#------------------------------------------------------------------------------

# pattern for the authentication token header
auth_header_pat = re.compile(r'^token\s+([^\s]+)$')

def token_authorized(method):
    """decorator for a method authorized by the Authorization header"""
    def check_token(self, *args, **kwargs):
        auth_header = self.request.headers.get('Authorization', '')
        match = auth_header_pat.match(auth_header)
        if not match:
            raise web.HTTPError(403)
        token = match.group(1)
        session = self.user_manager.user_for_api_token(token)
        if session is None:
            raise web.HTTPError(403)
        self.request_session = session
        return method(self, *args, **kwargs)
    check_token.__name__ = method.__name__
    check_token.__doc__ = method.__doc__
    return check_token


class AuthorizationsHandler(BaseHandler):
    @token_authorized
    def get(self, token):
        session = self.user_manager.user_for_cookie_token(token)
        if session is None:
            app_log.debug('cookie tokens: %r',
                { user:s.cookie_token for user,s in self.user_manager.users.items() }
            )
            raise web.HTTPError(404)
        self.write(json.dumps({
            'user' : session.user,
        }))
