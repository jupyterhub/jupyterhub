#!/usr/bin/env python
"""The multi-user notebook application"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


import logging
import os
from subprocess import Popen

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.log import LogFormatter
from tornado import gen, web

from IPython.utils.traitlets import (
    Unicode, Integer, Dict, TraitError, List, Instance, Bool, Bytes, Any,
    DottedObjectName,
)
from IPython.config import Application
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
from ._data import DATA_FILES_PATH
from .utils import url_path_join

class JupyterHubApp(Application):
    """An Application for starting a Multi-User Notebook server."""
    data_files_path = Unicode(DATA_FILES_PATH, config=True,
        help="The location of jupyter data files (e.g. /usr/local/share/jupyter)"
    )
    
    ip = Unicode('localhost', config=True,
        help="The public facing ip of the proxy"
    )
    port = Integer(8000, config=True,
        help="The public facing port of the proxy"
    )
    base_url = Unicode('/', config=True,
        help="The base URL of the entire application"
    )
    
    proxy_cmd = Unicode('configurable-http-proxy', config=True,
        help="""The command to start the http proxy.
        
        Only override if configurable-http-proxy is not on your PATH
        """
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
    
    authenticator = DottedObjectName("jupyterhub.auth.PAMAuthenticator", config=True,
        help="""Class for authenticating users.
        
        This should be a class with the following form:
        
        - constructor takes one kwarg: `config`, the IPython config object.
        
        - is a tornado.gen.coroutine
        - returns username on success, None on failure
        - takes two arguments: (handler, data),
          where `handler` is the calling web.RequestHandler,
          and `data` is the POST form data from the login page.
        """
    )
    # class for spawning single-user servers
    spawner_class = DottedObjectName("jupyterhub.spawner.LocalProcessSpawner", config=True,
        help="""The class to use for spawning single-user servers.
        
        Should be a subclass of Spawner.
        """
    )
    
    db_url = Unicode('sqlite:///:memory:', config=True)
    debug_db = Bool(False)
    db = Any()
    
    tornado_settings = Dict(config=True)
    
    handlers = List()
    
    
    _log_formatter_cls = LogFormatter
    
    def _log_level_default(self):
        return logging.INFO
    
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%H:%M:%S"
    
    def _log_format_default(self):
        """override default log format to include time"""
        return u"%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s]%(end_color)s %(message)s"
    
    def init_logging(self):
        # This prevents double log messages because tornado use a root logger that
        # self.log is a child of. The logging module dipatches log messages to a log
        # and all of its ancenstors until propagate is set to False.
        self.log.propagate = False
        
        # hook up tornado 3's loggers to our app handlers
        logger = logging.getLogger('tornado')
        logger.propagate = True
        logger.parent = self.log
        logger.setLevel(self.log.level)
    
    
    @staticmethod
    def add_url_prefix(prefix, handlers):
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
        # TODO: if not resuming, clear existing db contents
        self.db = db.new_session(self.db_url, echo=self.debug_db)
    
    def init_hub(self):
        """Load the Hub config into the database"""
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
        """Load the Proxy config into the database"""
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
        """Actually start the configurable-http-proxy"""
        env = os.environ.copy()
        env['CONFIGPROXY_AUTH_TOKEN'] = self.proxy.auth_token
        self.proxy = Popen([self.proxy_cmd,
            '--ip', self.proxy.public_server.ip,
            '--port', str(self.proxy.public_server.port),
            '--api-ip', self.proxy.api_server.ip,
            '--api-port', str(self.proxy.api_server.port),
            '--upstream-ip', self.hub.server.ip,
            '--upstream-port', str(self.hub.server.port),
        ], env=env)
    
    def init_tornado_settings(self):
        """Set up the tornado settings dict."""
        base_url = self.base_url
        settings = dict(
            config=self.config,
            # log=self.log,
            db=self.db,
            hub=self.hub,
            authenticator=import_item(self.authenticator)(config=self.config),
            spawner_class=import_item(self.spawner_class),
            base_url=base_url,
            cookie_secret=self.cookie_secret,
            login_url=url_path_join(self.hub.server.base_url, 'login'),
            template_path=os.path.join(here, 'templates'),
        )
        # allow configured settings to have priority
        settings.update(self.tornado_settings)
        self.tornado_settings = settings
    
    def init_tornado_application(self):
        """Instantiate the tornado Application object"""
        self.tornado_application = web.Application(self.handlers, **self.tornado_settings)
        
    def initialize(self, *args, **kwargs):
        super(JupyterHubApp, self).initialize(*args, **kwargs)
        self.init_logging()
        self.init_db()
        self.init_hub()
        self.init_proxy()
        self.init_handlers()
        self.init_tornado_settings()
        self.init_tornado_application()
    
    @gen.coroutine
    def cleanup(self):
        self.log.info("Cleaning up proxy...")
        self.proxy.terminate()
        self.log.info("Cleaning up single-user servers...")
        
        # request (async) process termination
        futures = []
        for user in self.db.query(db.User):
            if user.spawner is not None:
                futures.append(user.spawner.stop())
        
        # wait for the requests to stop finish:
        for f in futures:
            yield f
        
        # finally stop the loop once we are all cleaned up
        self.log.info("...done")
        tornado.ioloop.IOLoop.instance().stop()
    
    def start(self):
        """Start the whole thing"""
        # start the proxy
        self.start_proxy()
        # start the webserver
        http_server = tornado.httpserver.HTTPServer(self.tornado_application)
        http_server.listen(self.hub_port)
        
        loop = tornado.ioloop.IOLoop.instance()
        try:
            loop.start()
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            # have to start the loop one more time,
            # to allow for async cleanup code.
            loop.add_callback(self.cleanup)
            tornado.ioloop.IOLoop.instance().start()

main = JupyterHubApp.launch_instance

if __name__ == "__main__":
    main()
