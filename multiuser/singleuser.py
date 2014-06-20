#!/usr/bin/env python
"""Dummy Single-User app to test the multi-user environment"""

import json
import os
import time

import requests

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado import web
from tornado.web import RequestHandler, Application
from tornado.websocket import WebSocketHandler
from tornado.log import app_log

from tornado.options import define, options

from IPython.html import utils

from .headers import HeadersHandler

here = os.path.dirname(__file__)

class BaseHandler(RequestHandler):
    @property
    def cookie_name(self):
        return self.settings['cookie_name']
    
    @property
    def user(self):
        return self.settings['user']
    
    @property
    def base_url(self):
        return self.settings['base_url']
    
    @property
    def multiuser_api_key(self):
        return self.settings['multiuser_api_key']
    
    @property
    def multiuser_api_url(self):
        return self.settings['multiuser_api_url']
    
    def verify_token(self, token):
        r = requests.get(utils.url_path_join(
            self.multiuser_api_url, "authorizations", token,
        ),
            headers = {'Authorization' : 'token %s' % self.multiuser_api_key}
        )
        if r.status_code == 404:
            return {'user' : ''}
        r.raise_for_status()
        return r.json()
    
    def get_current_user(self):
        token = self.get_cookie(self.cookie_name, '')
        if token:
            auth_data = self.verify_token(token)
            if not auth_data:
                # treat invalid token the same as no token
                return None
            user = auth_data['user']
            if user == self.user:
                return user
            else:
                raise web.HTTPError(403, "User %s does not have access to %s" % (user, self.user))
        else:
            app_log.debug("No token cookie")
            return None

class MainHandler(BaseHandler):
    
    @web.authenticated
    def get(self, uri):
        self.render("singleuser.html",
            uri=uri,
            user=self.user,
            base_url=self.base_url,
        )

from tornado.ioloop import PeriodicCallback

class WSHandler(BaseHandler, WebSocketHandler):
    def open(self):
        pc = PeriodicCallback(self.ping, 1000)
        pc.start()
        
    def ping(self):
        self.write_message(str(time.time()))
    


def main():
    env = os.environ
    define("port", default=8888, help="run on the given port", type=int)
    define("user", default='', help="my username", type=str)
    define("cookie_name", default='cookie', help="my cookie name", type=str)
    define("base_url", default='/', help="My base URL", type=str)
    define("multiuser_prefix", default='/multiuser/', help="The multi-user URL", type=str)
    define("multiuser_api_url", default='http://localhost:8001/multiuser/api/', help="The multi-user API URL", type=str)
    
    tornado.options.parse_command_line()
    handlers = [
        ("/headers", HeadersHandler),
        ("/ws", WSHandler),
        (r"(.*)", MainHandler),
    ]
    base_url = options.base_url
    for i, tup in enumerate(handlers):
        lis = list(tup)
        lis[0] = utils.url_path_join(base_url, tup[0])
        handlers[i] = tuple(lis)
    
    application = Application(handlers,
        user=options.user,
        multiuser_api_key=env['IPY_API_TOKEN'],
        cookie_secret=env['IPY_COOKIE_SECRET'],
        cookie_name=options.cookie_name,
        login_url=utils.url_path_join(options.multiuser_prefix, 'login'),
        multiuser_api_url = options.multiuser_api_url,
        base_url=options.base_url,
        template_path=os.path.join(here, 'templates'),
    )
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    app_log.info("User %s listening on %s" % (options.user, options.port))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
