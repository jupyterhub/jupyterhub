#!/usr/bin/env python

import socket
import sys
import uuid
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

def random_port():
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

define("port", default=8001, help="run on the given port", type=int)


class SingleUserManager(object):
    
    routes_t = 'http://localhost:8000/api/routes{uri}'
    single_user_t = 'http://localhost:{port}'
    
    def __init__(self):
        self.processes = {}
        self.ports = {}
    
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
        assert user not in self.processes
        port = random_port()
        self.processes[user] = Popen(
            [sys.executable, 'singleuser.py', '--port=%i' % port, '--user=%s' % user])
        self.ports[user] = port
        r = requests.post(
            self.routes_t.format(uri=u'/user/%s' % user),
            data=json.dumps(dict(
                target=self.single_user_t.format(port=port),
                user=user,
            )),
        )
        self._wait_for_port(port)
        r.raise_for_status()
        print("spawn done")
    
    def exists(self, user):
        if user in self.processes:
            if self.processes[user].poll() is None:
                return True
            else:
                self.processes.pop(user)
                self.ports.pop(user)
        
        return False
    
    def get(self, user):
        """ensure process exists and return its port"""
        if not self.exists(user):
            self.spawn(user)
        return self.ports[user]
    
    def shutdown(self, user):
        assert user in self.processes
        port = self.ports[user]
        self.processes[user].terminate()
        r = requests.delete(self.routes_url,
            data=json.dumps(user=user, port=port),
        )
        r.raise_for_status()

class BaseHandler(RequestHandler):
    cookie_name = 'multiusertest'
    def get_current_user(self):
        user = self.get_cookie(self.cookie_name, '')
        if user:
            return user
        
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
            self.set_cookie(self.cookie_name, user)
        else:
            self._render(
                message={'error': 'Invalid username or password'},
                user=user,
            )
            return

        self.redirect(next_url)

def main():
    tornado.options.parse_command_line()
    application = Application([
        (r"/", MainHandler),
        (r"/login", LoginHandler),
        # (r"/shutdown/([^/]+)", ShutdownHandler),
        # (r"/start/([^/]+)", StartHandler),
        (r"/user/([^/]+)/?.*", UserHandler),
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
