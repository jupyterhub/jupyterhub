#!/usr/bin/env python

import os

import requests

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.web import RequestHandler, Application
from tornado import web
from tornado.log import app_log

from tornado.options import define, options

from IPython.html import utils

class BaseHandler(RequestHandler):
    cookie_name = 'multiusertest'
    
    @property
    def user(self):
        return self.settings['user']
    
    @property
    def multiuser_api_key(self):
        return self.settings['multiuser_api_key']
    
    @property
    def multi_user_url(self):
        return "http://localhost:8001"
    
    def verify_token(self, token):
        r = requests.get(utils.url_path_join(
            self.multi_user_url, "/api/authorizations", token,
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
            return None

class MainHandler(BaseHandler):
    
    @web.authenticated
    def get(self, uri):
        self.write("single-user %s: %s" % (self.user, uri))

def main():
    env = os.environ
    define("port", default=8888, help="run on the given port", type=int)
    define("user", default='', help="my username", type=str)
    
    tornado.options.parse_command_line()
    application = Application([
        (r"(.*)", MainHandler),
    ],
        user=options.user,
        multiuser_api_key=env['IP_API_TOKEN'],
        login_url='/login',
    )
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    app_log.info("single user %s listening on %s" % (options.user, options.port))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
