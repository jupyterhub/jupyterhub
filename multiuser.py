#!/usr/bin/env python

import os
import re
import socket
import sys
import uuid
from collections import defaultdict
from subprocess import Popen

import json
import requests
import time

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.log import app_log
from tornado.escape import url_escape
from tornado.httputil import url_concat
from tornado.web import RequestHandler, Application
from tornado import web

from tornado.options import define, options

from IPython.utils.traitlets import HasTraits, Any, Unicode, Integer

def random_port():
    """get a single random port"""
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

auth_header_pat = re.compile(r'^token\s+([^\s]+)$')

def token_authorized(method):
    def check_token(self, *args, **kwargs):
        auth_header = self.request.headers.get('Authorization', '')
        match = auth_header_pat.match(auth_header)
        if not match:
            raise web.HTTPError(403)
        token = match.group(1)
        app_log.info("api token: %r", token)
        session = self.user_manager.user_for_api_token(token)
        if session is None:
            raise web.HTTPError(403)
        self.request_session = session
        return method(self, *args, **kwargs)
    return check_token


class UserSession(HasTraits):
    env_prefix = Unicode('IP_')
    process = Any()
    port = Integer()
    user = Unicode()
    
    url_prefix = Unicode()
    def _url_prefix_default(self):
        return '/user/%s' % self.user
    
    api_token = Unicode()
    def _api_token_default(self):
        return str(uuid.uuid4())
    
    cookie_token = Unicode()
    def _cookie_token_default(self):
        return str(uuid.uuid4())
    
    def _env_key(self, d, key, value):
        d['%s%s' % (self.env_prefix, key)] = value
    
    @property
    def env(self):
        env = os.environ.copy()
        # self._env_key(env, 'PORT', str(self.port))
        # self._env_key(env, 'USER', self.user)
        # self._env_key(env, 'URL_PREFIX', self.url_prefix)
        self._env_key(env, 'API_TOKEN', self.api_token)
        return env
    
    @property
    def auth_data(self):
        return dict(
            user=self.user,
        )
    
    def start(self):
        assert self.process is None or self.process.poll() is not None
        self.process = Popen([sys.executable, 'singleuser.py', '--user=%s' % self.user, '--port=%i' % self.port], env=self.env)
    
    def running(self):
        if self.process is None:
            return False
        if self.process.poll() is not None:
            self.process = None
            return False
        return True
    
    def stop(self):
        if self.process is None:
            return
        
        if self.process.poll() is None:
            self.process.terminate()
        self.process = None
    

class SingleUserManager(object):
    
    routes_t = 'http://localhost:8000/api/routes{uri}'
    single_user_t = 'http://localhost:{port}'
    
    def __init__(self):
        self.users = defaultdict(UserSession)
        self.by_api_token = {}
        self.by_cookie_token = {}
    
    def _wait_for_port(self, port, timeout=2):
        tic = time.time()
        while time.time() - tic < timeout:
            try:
                socket.create_connection(('localhost', port))
            except socket.error:
                time.sleep(0.1)
            else:
                break
    
    def spawn(self, user):
        if user in self.users:
            session = self.users[user]
        else:
            session = self.users[user] = UserSession(user=user)
        assert not session.running()
        session.port = port = random_port()
        session.start()
        
        r = requests.post(
            self.routes_t.format(uri=session.url_prefix),
            data=json.dumps(dict(
                target=self.single_user_t.format(port=port),
                user=user,
            )),
        )
        self._wait_for_port(port)
        r.raise_for_status()
    
    def user_for_api_token(self, token):
        for session in self.users.values():
            if session.api_token == token:
                return session
    
    def user_for_cookie_token(self, token):
        for session in self.users.values():
            if session.cookie_token == token:
                return session
    
    def exists(self, user):
        if user in self.users:
            if self.users[user].process.poll() is None:
                return True
            else:
                session = self.users.pop(user)
                r = requests.delete(
                    self.routes_t.format(uri=session.url_prefix),
                )
        
        return False
    
    def shutdown(self, user):
        assert user in self.users
        session = self.users.pop(user)
        session.stop()
        r = requests.delete(self.routes_url,
            data=json.dumps(user=user, port=session.port),
        )
        r.raise_for_status()

class BaseHandler(RequestHandler):
    cookie_name = 'multiusertest'
    
    def get_current_user(self):
        token = self.get_cookie(self.cookie_name, '')
        if token:
            session = self.user_manager.user_for_cookie_token(token)
            if session:
                return session.user
        
    @property
    def user_manager(self):
        return self.settings['user_manager']
    
    def clear_login_cookie(self):
        self.clear_cookie(self.cookie_name)
    
class MainHandler(BaseHandler):
    @web.authenticated
    def get(self):
        self.redirect("/user/%s" % self.get_current_user())

class UserHandler(BaseHandler):
    @web.authenticated
    def get(self, user):
        self.write("multi-user at single-user url: %s" % user)
        if self.get_current_user() == user:
            self.user_manager.spawn(user)
            self.redirect('')
        else:
            self.clear_login_cookie()
            self.redirect(url_concat(self.settings['login_url'], {
                'next' : '/user/%s' % user
            }))

class AuthorizationsHandler(BaseHandler):
    @token_authorized
    def get(self, token):
        app_log.info('cookie token: %r', token)
        session = self.user_manager.user_for_cookie_token(token)
        if session is None:
            raise web.HTTPError(404)
        self.write(json.dumps({
            'user' : session.user,
        }))

class LogoutHandler(BaseHandler):
    
    def get(self):
        self.clear_login_cookie()
        self.write("logged out")

class LoginHandler(BaseHandler):

    def _render(self, message=None, user=None):
        self.render('login.html',
                next=url_escape(self.get_argument('next', default='')),
                user=user,
                message=message,
        )

    def get(self):
        if self.get_current_user():
            self.redirect(self.get_argument('next', default='/'))
        else:
            user = self.get_argument('user', default='')
            self._render(user=user)

    def post(self):
        user = self.get_argument('user', default='')
        pwd = self.get_argument('password', default=u'')
        next_url = self.get_argument('next', default='') or '/user/%s' % user
        if user and pwd == 'password':
            if user not in self.user_manager.users:
                session = self.user_manager.users[user] = UserSession(user=user)
            else:
                session = self.user_manager.users[user]
            cookie_token = session.cookie_token
            self.set_cookie(self.cookie_name, cookie_token)
        else:
            self._render(
                message={'error': 'Invalid username or password'},
                user=user,
            )
            return

        self.redirect(next_url)

def main():
    define("port", default=8001, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    application = Application([
        (r"/", MainHandler),
        (r"/login", LoginHandler),
        # (r"/shutdown/([^/]+)", ShutdownHandler),
        # (r"/start/([^/]+)", StartHandler),
        (r"/user/([^/]+)/?.*", UserHandler),
        (r"/api/authorizations/([^/]+)", AuthorizationsHandler),
    ],
        user_manager=SingleUserManager(),
        cookie_secret='super secret',
        login_url='/login',
    )
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    proxy = Popen(["node", "proxy.js"])
    try:
        tornado.ioloop.IOLoop.instance().start()
    finally:
        proxy.terminate()


if __name__ == "__main__":
    main()
