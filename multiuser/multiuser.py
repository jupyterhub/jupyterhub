#!/usr/bin/env python

import json
import os
import re
import socket
import signal
import sys
import time
import uuid
from subprocess import Popen

import requests

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.log import app_log
from tornado.escape import url_escape, xhtml_escape
from tornado.httputil import url_concat
from tornado.web import RequestHandler, Application
from tornado import web

from tornado.options import define, options

from IPython.utils.traitlets import Any, Unicode, Integer, Dict
from IPython.config import LoggingConfigurable
from IPython.html import utils

from .headers import HeadersHandler

def random_port():
    """get a single random port"""
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

auth_header_pat = re.compile(r'^token\s+([^\s]+)$')

here = os.path.dirname(__file__)

def token_authorized(method):
    """decorator for a method authorized by the Authorization header"""
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
    check_token.__name__ = method.__name__
    check_token.__doc__ = method.__doc__
    return check_token


class UserSession(LoggingConfigurable):
    env_prefix = Unicode('IPY_')
    process = Any()
    port = Integer()
    user = Unicode()
    cookie_secret = Unicode()
    cookie_name = Unicode()
    def _cookie_name_default(self):
        return 'ipy-multiuser-%s' % self.user
    
    multiuser_prefix = Unicode()
    multiuser_api_url = Unicode()
    
    url_prefix = Unicode()
    def _url_prefix_default(self):
        return '/user/%s/' % self.user
    
    api_token = Unicode()
    def _api_token_default(self):
        return str(uuid.uuid4())
    
    cookie_token = Unicode()
    def _cookie_token_default(self):
        return str(uuid.uuid4())
    
    def _env_key(self, d, key, value):
        d['%s%s' % (self.env_prefix, key)] = value
    
    env = Dict()
    def _env_default(self):
        env = os.environ.copy()
        self._env_key(env, 'COOKIE_SECRET', self.cookie_secret)
        self._env_key(env, 'API_TOKEN', self.api_token)
        return env
    
    @property
    def auth_data(self):
        return dict(
            user=self.user,
        )
    
    def start(self):
        assert self.process is None or self.process.poll() is not None
        cmd = [sys.executable, '-m', 'multiuser.singleuser',
            '--user=%s' % self.user, '--port=%i' % self.port,
            '--cookie-name=%s' % self.cookie_name,
            '--multiuser-prefix=%s' % self.multiuser_prefix,
            '--multiuser-api-url=%s' % self.multiuser_api_url,
            '--base-url=%s' % self.url_prefix,
            ]
        app_log.info("Spawning: %s" % cmd)
        self.process = Popen(cmd, env=self.env,
            # don't forward signals:
            preexec_fn=os.setpgrp,
        )
    
    def running(self):
        if self.process is None:
            return False
        if self.process.poll() is not None:
            self.process = None
            return False
        return True
    
    def request_stop(self):
        if self.running():
            self.process.send_signal(signal.SIGINT)
            time.sleep(0.1)
        if self.running():
            self.process.send_signal(signal.SIGINT)
        
    def stop(self):
        for i in range(100):
            if self.running():
                time.sleep(0.1)
            else:
                break
        if self.running():
            self.process.terminate()
    

class SingleUserManager(LoggingConfigurable):
    
    users = Dict()
    routes_t = Unicode('http://localhost:8000/api/routes{uri}')
    single_user_t = Unicode('http://localhost:{port}')
    
    def _wait_for_port(self, port, timeout=2):
        tic = time.time()
        while time.time() - tic < timeout:
            try:
                socket.create_connection(('localhost', port))
            except socket.error:
                time.sleep(0.1)
            else:
                break
    
    
    def get_session(self, user, **kwargs):
        if user not in self.users:
            kwargs['user'] = user
            self.users[user] = UserSession(**kwargs)
        return self.users[user]
            
    def spawn(self, user):
        session = self.get_session(user)
        if session.running():
            app_log.warn("User session %s already running", user)
            return
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
        """Get the user session object for a given API token"""
        for session in self.users.values():
            if session.api_token == token:
                return session
    
    def user_for_cookie_token(self, token):
        """Get the user session object for a given cookie token"""
        for session in self.users.values():
            if session.cookie_token == token:
                return session
    
    def shutdown(self, user):
        assert user in self.users
        session = self.users.pop(user)
        session.stop()
        r = requests.delete(self.routes_url,
            data=json.dumps(user=user, port=session.port),
        )
        r.raise_for_status()
    
    def cleanup(self):
        sessions = list(self.users.values())
        self.users = {}
        for session in sessions:
            self.log.info("Cleaning up %s's server" % session.user)
            session.request_stop()
        for i in range(100):
            if any([ session.running() for session in sessions ]):
                time.sleep(0.1)
            else:
                break
        for session in sessions:
            session.stop()

class BaseHandler(RequestHandler):
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
        

    
class MainHandler(BaseHandler):
    @web.authenticated
    def get(self):
        self.redirect("/user/%s/" % self.get_current_user())

class UserHandler(BaseHandler):
    @web.authenticated
    def get(self, user):
        self.log.info("multi-user at single-user url: %s", user)
        if self.get_current_user() == user:
            self.spawn_single_user(user)
            self.redirect('')
        else:
            self.clear_login_cookie()
            self.redirect(url_concat(self.settings['login_url'], {
                'next' : '/user/%s/' % user
            }))

class AuthorizationsHandler(BaseHandler):
    @token_authorized
    def get(self, token):
        app_log.info('cookie token: %r', token)
        session = self.user_manager.user_for_cookie_token(token)
        if session is None:
            app_log.info('cookie tokens: %r',
                { user:s.cookie_token for user,s in self.user_manager.users.items() }
            )
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

def main():
    define("port", default=8001, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    handlers = [
        (r"/", MainHandler),
        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler),
        (r"/headers", HeadersHandler),
        (r"/api/authorizations/([^/]+)", AuthorizationsHandler),
    ]
    
    # add base_url to handlers
    base_url = "/multiuser/"
    for i, tup in enumerate(handlers):
        lis = list(tup)
        lis[0] = utils.url_path_join(base_url, tup[0])
        handlers[i] = tuple(lis)
    
    handlers.extend([
        (r"/user/([^/]+)/?.*", UserHandler),
        (r"/", web.RedirectHandler, {"url" : base_url}),
    ])
    user_manager = SingleUserManager()
    
    application = Application(handlers,
        base_url=base_url,
        user_manager=user_manager,
        cookie_secret='super secret',
        cookie_name='multiusertest',
        multiuser_prefix=base_url,
        multiuser_api_url=utils.url_path_join(
            'http://localhost:%i' % options.port,
            base_url,
            'api',
        ),
        login_url=utils.url_path_join(base_url, 'login'),
        template_path=os.path.join(here, 'templates'),
    )
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    proxy = Popen(["node", os.path.join(here, 'js', 'main.js')])
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        proxy.terminate()
        user_manager.cleanup()


if __name__ == "__main__":
    main()
