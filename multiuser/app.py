#!/usr/bin/env python

import os
from subprocess import Popen

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado import web

from IPython.utils.traitlets import (
    Unicode, Integer, Dict, TraitError, List,
)
from IPython.config import Application
from IPython.html import utils

here = os.path.dirname(__file__)

from .handlers import (
    RootHandler,
    LoginHandler,
    LogoutHandler,
    AuthorizationsHandler,
    UserHandler,
)

from .user import UserManager

class MultiUserAuthenticationApp(Application):
    port = Integer(8000, config=True,
        help="The public facing port of the proxy"
    )
    proxy_api_port = Integer(config=True,
        help="The port for the proxy API handlers"
    )
    def _proxy_api_port_default(self):
        return self.port + 1
    
    multiuser_port = Integer(8081, config=True,
        help="The port for this process"
    )
    
    multiuser_prefix = Unicode('/multiuser/', config=True,
        help="The prefix for the multi-user server. Must not be '/'"
    )
    def _multiuser_prefix_changed(self, name, old, new):
        if new == '/':
            raise TraitError("'/' is not a valid multi-user prefix")
        newnew = new
        if not new.startswith('/'):
            newnew = '/' + new
        if not newnew.endswith('/'):
            newnew = newnew + '/'
        if newnew != new:
            self.multiuser_prefix = newnew
    
    tornado_settings = Dict(config=True)
    
    handlers = List()
    
    def add_url_prefix(self, prefix, handlers):
        """add a url prefix to handlers"""
        for i, tup in enumerate(handlers):
            lis = list(tup)
            lis[0] = utils.url_path_join(prefix, tup[0])
            handlers[i] = tuple(lis)
        return handlers
    
    def init_handlers(self):
        handlers = [
            (r"/", RootHandler),
            (r"/login", LoginHandler),
            (r"/logout", LogoutHandler),
            (r"/api/authorizations/([^/]+)", AuthorizationsHandler),
        ]
        self.handlers = self.add_url_prefix(self.multiuser_prefix, handlers)
        self.handlers.extend([
            (r"/user/([^/]+)/?.*", UserHandler),
            (r"/", web.RedirectHandler, {"url" : self.multiuser_prefix}),
        ])
    
    def init_user_manager(self):
        self.user_manager = UserManager(proxy_port=self.proxy_api_port)
    
    def init_proxy(self):
        env = os.environ.copy()
        env['CONFIGPROXY_AUTH_TOKEN'] = self.user_manager.proxy_auth_token
        self.proxy = Popen(["node", os.path.join(here, 'js', 'main.js'),
            '--port', str(self.port),
            '--api-port', str(self.proxy_api_port),
            '--upstream-port', str(self.multiuser_port),
        ], env=env)
    
    def init_tornado_settings(self):
        base_url = self.multiuser_prefix
        self.tornado_settings.update(
            base_url=base_url,
            user_manager=self.user_manager,
            cookie_secret='super secret',
            cookie_name='multiusertest',
            multiuser_prefix=base_url,
            multiuser_api_url=utils.url_path_join(
                'http://localhost:%i' % self.multiuser_port,
                base_url,
                'api',
            ),
            login_url=utils.url_path_join(base_url, 'login'),
            template_path=os.path.join(here, 'templates'),
        )
    
    def init_tornado_application(self):
        self.tornado_application = web.Application(self.handlers, **self.tornado_settings)
        
    def initialize(self, *args, **kwargs):
        super(MultiUserAuthenticationApp, self).initialize(*args, **kwargs)
        self.init_user_manager()
        self.init_proxy()
        self.init_handlers()
        self.init_tornado_settings()
        self.init_tornado_application()
    
    def start(self):
        http_server = tornado.httpserver.HTTPServer(self.tornado_application)
        http_server.listen(self.multiuser_port)
        try:
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            self.proxy.terminate()
            self.user_manager.cleanup()

main = MultiUserAuthenticationApp.launch_instance

if __name__ == "__main__":
    main()
