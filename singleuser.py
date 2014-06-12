#!/usr/bin/env python

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.web import RequestHandler, Application
from tornado import web
from tornado.log import app_log

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("user", default='', help="my username", type=str)

class BaseHandler(RequestHandler):
    cookie_name = 'multiusertest'
    @property
    def user(self):
        return self.settings['user']
    
    def get_current_user(self):
        user = self.get_cookie(self.cookie_name, '')
        if user and user == self.user:
            return user
        else:
            raise web.HTTPError(403, "User %s does not have access to %s" % (user, self.user))

class MainHandler(BaseHandler):
    
    @web.authenticated
    def get(self, uri):
        self.write("single-user %s: %s" % (self.user, uri))

def main():
    tornado.options.parse_command_line()
    application = Application([
        (r"(.*)", MainHandler),
    ],
        user=options.user,
        login_url='/login',
    )
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    app_log.info("single user %s listening on %s" % (options.user, options.port))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
