#!/usr/bin/env python

import os
from subprocess import Popen

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado import web

from IPython.utils.traitlets import (
    Unicode, Integer, Dict, TraitError, List, Instance, Bool, Bytes, Any,
    DottedObjectName,
)
from IPython.config import Application
from IPython.html.utils import url_path_join
from IPython.utils.importstring import import_item

here = os.path.dirname(__file__)

from .handlers import (
    RootHandler,
    LoginHandler,
    LogoutHandler,
    AuthorizationsHandler,
    UserHandler,
)

from . import db

# from .user import UserManager

class MultiUserApp(Application):
    
    ip = Unicode('localhost', config=True,
        help="The public facing ip of the proxy"
    )
    port = Integer(8000, config=True,
        help="The public facing port of the proxy"
    )
    base_url = Unicode('/', config=True,
        help="The base URL of the entire application"
    )
    proxy_auth_token = Unicode(config=True,
        help="The Proxy Auth token"
    )
    def _proxy_auth_token_default(self):
        return db.new_token()
    
    proxy_api_ip = Unicode('localhost', config=True,
        help="The ip for the proxy API handlers"
    )
    proxy_api_port = Integer(config=True,
        help="The port for the proxy API handlers"
    )
    def _proxy_api_port_default(self):
        return self.port + 1
    
    hub_port = Integer(8081, config=True,
        help="The port for this process"
    )
    hub_ip = Unicode('localhost', config=True,
        help="The ip for this process"
    )
    
    hub_prefix = Unicode('/hub/', config=True,
        help="The prefix for the hub server. Must not be '/'"
    )
    def _hub_prefix_default(self):
        return url_path_join(self.base_url, '/hub/')
    
    def _hub_prefix_changed(self, name, old, new):
        if new == '/':
            raise TraitError("'/' is not a valid hub prefix")
        newnew = new
        if not new.startswith('/'):
            newnew = '/' + new
        if not newnew.endswith('/'):
            newnew = newnew + '/'
        if not newnew.startswith(self.base_url):
            newnew = url_path_join(self.base_url, newnew)
        if newnew != new:
            self.hub_prefix = newnew
    
    cookie_secret = Bytes(config=True)
    def _cookie_secret_default(self):
        return b'secret!'
    
    # spawning subprocesses
    spawner_class = DottedObjectName("multiuser.spawner.ProcessSpawner")
    def _spawner_class_changed(self, name, old, new):
        self.spawner = import_item(new)
    
    spawner = Any()
    def _spawner_default(self):
        return import_item(self.spawner_class)
    
    
    db_url = Unicode('sqlite:///:memory:', config=True)
    debug_db = Bool(False)
    db = Any()
    
    tornado_settings = Dict(config=True)
    
    handlers = List()
    
    def add_url_prefix(self, prefix, handlers):
        """add a url prefix to handlers"""
        for i, tup in enumerate(handlers):
            lis = list(tup)
            lis[0] = url_path_join(prefix, tup[0])
            handlers[i] = tuple(lis)
        return handlers
    
    def init_handlers(self):
        handlers = [
            (r"/", RootHandler),
            (r"/login", LoginHandler),
            (r"/logout", LogoutHandler),
            (r"/api/authorizations/([^/]+)", AuthorizationsHandler),
        ]
        self.handlers = self.add_url_prefix(self.hub_prefix, handlers)
        self.handlers.extend([
            (r"/user/([^/]+)/?.*", UserHandler),
            (r"/", web.RedirectHandler, {"url" : self.hub_prefix}),
        ])
    
    def init_db(self):
        # TODO: load state from db for resume
        self.db = db.new_session(self.db_url, echo=self.debug_db)
    
    def init_hub(self):
        self.hub = db.Hub(
            server=db.Server(
                ip=self.hub_ip,
                port=self.hub_port,
                base_url=self.hub_prefix,
                cookie_secret=self.cookie_secret,
                cookie_name='jupyter-hub-token',
            )
        )
        self.db.add(self.hub)
        self.db.commit()
    
    def init_proxy(self):
        self.proxy = db.Proxy(
            public_server=db.Server(
                ip=self.ip,
                port=self.port,
            ),
            api_server=db.Server(
                ip=self.proxy_api_ip,
                port=self.proxy_api_port,
                base_url='/api/routes/'
            ),
            auth_token = db.new_token(),
        )
        self.db.add(self.proxy)
        self.db.commit()
    
    def start_proxy(self):
        env = os.environ.copy()
        env['CONFIGPROXY_AUTH_TOKEN'] = self.proxy.auth_token
        self.proxy = Popen(["node", os.path.join(here, 'js', 'main.js'),
            '--port', str(self.proxy.public_server.port),
            '--api-port', str(self.proxy.api_server.port),
            '--upstream-port', str(self.hub.server.port),
        ], env=env)
    
    def init_tornado_settings(self):
        base_url = self.base_url
        self.tornado_settings.update(
            db=self.db,
            hub=self.hub,
            base_url=base_url,
            cookie_secret=self.cookie_secret,
            login_url=url_path_join(self.hub.server.base_url, 'login'),
            template_path=os.path.join(here, 'templates'),
        )
    
    def init_tornado_application(self):
        self.tornado_application = web.Application(self.handlers, **self.tornado_settings)
        
    def initialize(self, *args, **kwargs):
        super(MultiUserApp, self).initialize(*args, **kwargs)
        self.init_db()
        self.init_hub()
        self.init_proxy()
        self.init_handlers()
        self.init_tornado_settings()
        self.init_tornado_application()
    
    def start(self):
        self.start_proxy()
        http_server = tornado.httpserver.HTTPServer(self.tornado_application)
        http_server.listen(self.hub_port)
        try:
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            pass
            # self.proxy.terminate()
            # self.user_manager.cleanup()

main = MultiUserApp.launch_instance

if __name__ == "__main__":
    main()
