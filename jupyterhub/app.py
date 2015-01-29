#!/usr/bin/env python
"""The multi-user notebook application"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import atexit
import binascii
import logging
import os
import socket
import sys
from datetime import datetime
from distutils.version import LooseVersion as V
from getpass import getuser
from subprocess import Popen

if sys.version_info[:2] < (3,3):
    raise ValueError("Python < 3.3 not supported: %s" % sys.version)

from jinja2 import Environment, FileSystemLoader

from sqlalchemy.exc import OperationalError

import tornado.httpserver
import tornado.options
from tornado.httpclient import HTTPError
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.log import LogFormatter, app_log, access_log, gen_log
from tornado import gen, web

import IPython
if V(IPython.__version__) < V('3.0'):
    raise ImportError("JupyterHub Requires IPython >= 3.0, found %s" % IPython.__version__)

from IPython.utils.traitlets import (
    Unicode, Integer, Dict, TraitError, List, Bool, Any,
    Type, Set, Instance, Bytes,
)
from IPython.config import Application, catch_config_error

here = os.path.dirname(__file__)

import jupyterhub
from . import handlers, apihandlers
from .handlers.static import CacheControlStaticFilesHandler

from . import orm
from ._data import DATA_FILES_PATH
from .traitlets import URLPrefix
from .utils import (
    url_path_join,
    ISO8601_ms, ISO8601_s,
)
# classes for config
from .auth import Authenticator, PAMAuthenticator
from .spawner import Spawner, LocalProcessSpawner

aliases = {
    'log-level': 'Application.log_level',
    'f': 'JupyterHub.config_file',
    'base-url': 'JupyterHub.base_url',
    'config': 'JupyterHub.config_file',
    'y': 'JupyterHub.answer_yes',
    'ssl-key': 'JupyterHub.ssl_key',
    'ssl-cert': 'JupyterHub.ssl_cert',
    'ip': 'JupyterHub.ip',
    'port': 'JupyterHub.port',
    'db': 'JupyterHub.db_url',
    'pid-file': 'JupyterHub.pid_file',
}

flags = {
    'debug': ({'Application' : {'log_level': logging.DEBUG}},
        "set log level to logging.DEBUG (maximize logging output)"),
    'generate-config': ({'JupyterHub': {'generate_config': True}},
        "generate default config file"),
    'no-db': ({'JupyterHub': {'db_url': 'sqlite:///:memory:'}},
        "disable persisting state database to disk"
    ),
}

SECRET_BYTES = 2048 # the number of bytes to use when generating new secrets

class NewToken(Application):
    """Generate and print a new API token"""
    name = 'jupyterhub-token'
    description = """Generate and return new API token for a user.
    
    Usage:
    
        jupyterhub token [username]
    """
    
    examples = """
        $> jupyterhub token kaylee
        ab01cd23ef45
    """
    
    name = Unicode(getuser())
    
    def parse_command_line(self, argv=None):
        super().parse_command_line(argv=argv)
        if not self.extra_args:
            return
        if len(self.extra_args) > 1:
            print("Must specify exactly one username", file=sys.stderr)
            self.exit(1)
        self.name = self.extra_args[0]
    
    def start(self):
        hub = JupyterHub(parent=self)
        hub.init_db()
        hub.init_users()
        user = orm.User.find(hub.db, self.name)
        if user is None:
            print("No such user: %s" % self.name)
            self.exit(1)
        token = user.new_api_token()
        print(token)


class JupyterHub(Application):
    """An Application for starting a Multi-User Jupyter Notebook server."""
    name = 'jupyterhub'
    
    description = """Start a multi-user Jupyter Notebook server
    
    Spawns a configurable-http-proxy and multi-user Hub,
    which authenticates users and spawns single-user Notebook servers
    on behalf of users.
    """
    
    examples = """
    
    generate default config file:
    
        jupyterhub --generate-config -f /etc/jupyterhub/jupyterhub.py
    
    spawn the server on 10.0.1.2:443 with https:
    
        jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert
    """
    
    aliases = Dict(aliases)
    flags = Dict(flags)
    
    subcommands = {
        'token': (NewToken, "Generate an API token for a user")
    }
    
    classes = List([
        Spawner,
        LocalProcessSpawner,
        Authenticator,
        PAMAuthenticator,
    ])
    
    config_file = Unicode('jupyterhub_config.py', config=True,
        help="The config file to load",
    )
    generate_config = Bool(False, config=True,
        help="Generate default config file",
    )
    answer_yes = Bool(False, config=True,
        help="Answer yes to any questions (e.g. confirm overwrite)"
    )
    pid_file = Unicode('', config=True,
        help="""File to write PID
        Useful for daemonizing jupyterhub.
        """
    )
    last_activity_interval = Integer(300, config=True,
        help="Interval (in seconds) at which to update last-activity timestamps."
    )
    proxy_check_interval = Integer(30, config=True,
        help="Interval (in seconds) at which to check if the proxy is running."
    )
    
    data_files_path = Unicode(DATA_FILES_PATH, config=True,
        help="The location of jupyterhub data files (e.g. /usr/local/share/jupyter/hub)"
    )
    
    ssl_key = Unicode('', config=True,
        help="""Path to SSL key file for the public facing interface of the proxy
        
        Use with ssl_cert
        """
    )
    ssl_cert = Unicode('', config=True,
        help="""Path to SSL certificate file for the public facing interface of the proxy
        
        Use with ssl_key
        """
    )
    ip = Unicode('', config=True,
        help="The public facing ip of the proxy"
    )
    port = Integer(8000, config=True,
        help="The public facing port of the proxy"
    )
    base_url = URLPrefix('/', config=True,
        help="The base URL of the entire application"
    )
    
    jinja_environment_options = Dict(config=True,
        help="Supply extra arguments that will be passed to Jinja environment."
    )
    
    proxy_cmd = Unicode('configurable-http-proxy', config=True,
        help="""The command to start the http proxy.
        
        Only override if configurable-http-proxy is not on your PATH
        """
    )
    proxy_auth_token = Unicode(config=True,
        help="""The Proxy Auth token.

        Loaded from the CONFIGPROXY_AUTH_TOKEN env variable by default.
        """
    )
    def _proxy_auth_token_default(self):
        token = os.environ.get('CONFIGPROXY_AUTH_TOKEN', None)
        if not token:
            self.log.warn('\n'.join([
                "",
                "Generating CONFIGPROXY_AUTH_TOKEN. Restarting the Hub will require restarting the proxy.",
                "Set CONFIGPROXY_AUTH_TOKEN env or JupyterHub.proxy_auth_token config to avoid this message.",
                "",
            ]))
            token = orm.new_token()
        return token
    
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
    
    hub_prefix = URLPrefix('/hub/', config=True,
        help="The prefix for the hub server. Must not be '/'"
    )
    def _hub_prefix_default(self):
        return url_path_join(self.base_url, '/hub/')
    
    def _hub_prefix_changed(self, name, old, new):
        if new == '/':
            raise TraitError("'/' is not a valid hub prefix")
        if not new.startswith(self.base_url):
            self.hub_prefix = url_path_join(self.base_url, new)
    
    cookie_secret = Bytes(config=True, env='JPY_COOKIE_SECRET',
        help="""The cookie secret to use to encrypt cookies.

        Loaded from the JPY_COOKIE_SECRET env variable by default.
        """
    )
    
    cookie_secret_file = Unicode('jupyterhub_cookie_secret', config=True,
        help="""File in which to store the cookie secret."""
    )
    
    authenticator_class = Type(PAMAuthenticator, Authenticator,
        config=True,
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
    
    authenticator = Instance(Authenticator)
    def _authenticator_default(self):
        return self.authenticator_class(parent=self, db=self.db)

    # class for spawning single-user servers
    spawner_class = Type(LocalProcessSpawner, Spawner,
        config=True,
        help="""The class to use for spawning single-user servers.
        
        Should be a subclass of Spawner.
        """
    )
    
    db_url = Unicode('sqlite:///jupyterhub.sqlite', config=True,
        help="url for the database. e.g. `sqlite:///jupyterhub.sqlite`"
    )
    def _db_url_changed(self, name, old, new):
        if '://' not in new:
            # assume sqlite, if given as a plain filename
            self.db_url = 'sqlite:///%s' % new

    db_kwargs = Dict(config=True,
        help="""Include any kwargs to pass to the database connection.
        See sqlalchemy.create_engine for details.
        """
    )

    reset_db = Bool(False, config=True,
        help="Purge and reset the database."
    )
    debug_db = Bool(False, config=True,
        help="log all database transactions. This has A LOT of output"
    )
    db = Any()
    session_factory = Any()
    
    admin_users = Set(config=True,
        help="""set of usernames of admin users

        If unspecified, only the user that launches the server will be admin.
        """
    )
    tornado_settings = Dict(config=True)
    
    handlers = List()
    
    _log_formatter_cls = LogFormatter
    
    def _log_level_default(self):
        return logging.INFO
    
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    def _log_format_default(self):
        """override default log format to include time"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    def init_logging(self):
        # This prevents double log messages because tornado use a root logger that
        # self.log is a child of. The logging module dipatches log messages to a log
        # and all of its ancenstors until propagate is set to False.
        self.log.propagate = False
        
        # hook up tornado 3's loggers to our app handlers
        for log in (app_log, access_log, gen_log):
            # ensure all log statements identify the application they come from
            log.name = self.log.name
        logger = logging.getLogger('tornado')
        logger.propagate = True
        logger.parent = self.log
        logger.setLevel(self.log.level)
    
    def init_ports(self):
        if self.hub_port == self.port:
            raise TraitError("The hub and proxy cannot both listen on port %i" % self.port)
        if self.hub_port == self.proxy_api_port:
            raise TraitError("The hub and proxy API cannot both listen on port %i" % self.hub_port)
        if self.proxy_api_port == self.port:
            raise TraitError("The proxy's public and API ports cannot both be %i" % self.port)
    
    @staticmethod
    def add_url_prefix(prefix, handlers):
        """add a url prefix to handlers"""
        for i, tup in enumerate(handlers):
            lis = list(tup)
            lis[0] = url_path_join(prefix, tup[0])
            handlers[i] = tuple(lis)
        return handlers
    
    def init_handlers(self):
        h = []
        h.extend(handlers.default_handlers)
        h.extend(apihandlers.default_handlers)
        # load handlers from the authenticator
        h.extend(self.authenticator.get_handlers(self))

        self.handlers = self.add_url_prefix(self.hub_prefix, h)

        # some extra handlers, outside hub_prefix
        self.handlers.extend([
            (r"%s" % self.hub_prefix.rstrip('/'), web.RedirectHandler,
                {
                    "url": self.hub_prefix,
                    "permanent": False,
                }
            ),
            (r"(?!%s).*" % self.hub_prefix, handlers.PrefixRedirectHandler),
            (r'(.*)', handlers.Template404),
        ])
    
    def _check_db_path(self, path):
        """More informative log messages for failed filesystem access"""
        path = os.path.abspath(path)
        parent, fname = os.path.split(path)
        user = getuser()
        if not os.path.isdir(parent):
            self.log.error("Directory %s does not exist", parent)
        if os.path.exists(parent) and not os.access(parent, os.W_OK):
            self.log.error("%s cannot create files in %s", user, parent)
        if os.path.exists(path) and not os.access(path, os.W_OK):
            self.log.error("%s cannot edit %s", user, path)
    
    def init_secrets(self):
        trait_name = 'cookie_secret'
        trait = self.traits()[trait_name]
        env_name = trait.get_metadata('env')
        secret_file = os.path.abspath(
            os.path.expanduser(self.cookie_secret_file)
        )
        secret = self.cookie_secret
        secret_from = 'config'
        # load priority: 1. config, 2. env, 3. file
        if not secret and os.environ.get(env_name):
            secret_from = 'env'
            self.log.info("Loading %s from env[%s]", trait_name, env_name)
            secret = binascii.a2b_hex(os.environ[env_name])
        if not secret and os.path.exists(secret_file):
            secret_from = 'file'
            perm = os.stat(secret_file).st_mode
            if perm & 0o077:
                self.log.error("Bad permissions on %s", secret_file)
            else:
                self.log.info("Loading %s from %s", trait_name, secret_file)
                with open(secret_file) as f:
                    b64_secret = f.read()
                try:
                    secret = binascii.a2b_base64(b64_secret)
                except Exception as e:
                    self.log.error("%s does not contain b64 key: %s", secret_file, e)
        if not secret:
            secret_from = 'new'
            self.log.debug("Generating new %s", trait_name)
            secret = os.urandom(SECRET_BYTES)
        
        if secret_file and secret_from == 'new':
            # if we generated a new secret, store it in the secret_file
            self.log.info("Writing %s to %s", trait_name, secret_file)
            b64_secret = binascii.b2a_base64(secret).decode('ascii')
            with open(secret_file, 'w') as f:
                f.write(b64_secret)
            try:
                os.chmod(secret_file, 0o600)
            except OSError:
                self.log.warn("Failed to set permissions on %s", secret_file)
        # store the loaded trait value
        self.cookie_secret = secret
    
    def init_db(self):
        """Create the database connection"""
        self.log.debug("Connecting to db: %s", self.db_url)
        try:
            self.session_factory = orm.new_session_factory(
                self.db_url,
                reset=self.reset_db,
                echo=self.debug_db,
                **self.db_kwargs
            )
            self.db = self.session_factory()
        except OperationalError as e:
            self.log.error("Failed to connect to db: %s", self.db_url)
            self.log.debug("Database error was:", exc_info=True)
            if self.db_url.startswith('sqlite:///'):
                self._check_db_path(self.db_url.split(':///', 1)[1])
            self.exit(1)
    
    def init_hub(self):
        """Load the Hub config into the database"""
        self.hub = self.db.query(orm.Hub).first()
        if self.hub is None:
            self.hub = orm.Hub(
                server=orm.Server(
                    ip=self.hub_ip,
                    port=self.hub_port,
                    base_url=self.hub_prefix,
                    cookie_name='jupyter-hub-token',
                )
            )
            self.db.add(self.hub)
        else:
            server = self.hub.server
            server.ip = self.hub_ip
            server.port = self.hub_port
            server.base_url = self.hub_prefix

        self.db.commit()
    
    @gen.coroutine
    def init_users(self):
        """Load users into and from the database"""
        db = self.db

        if not self.admin_users:
            # add current user as admin if there aren't any others
            admins = db.query(orm.User).filter(orm.User.admin==True)
            if admins.first() is None:
                self.admin_users.add(getuser())
        
        new_users = []

        for name in self.admin_users:
            # ensure anyone specified as admin in config is admin in db
            user = orm.User.find(db, name)
            if user is None:
                user = orm.User(name=name, admin=True)
                new_users.append(user)
                db.add(user)
            else:
                user.admin = True

        # the admin_users config variable will never be used after this point.
        # only the database values will be referenced.

        whitelist = self.authenticator.whitelist

        if not whitelist:
            self.log.info("Not using whitelist. Any authenticated user will be allowed.")

        # add whitelisted users to the db
        for name in whitelist:
            user = orm.User.find(db, name)
            if user is None:
                user = orm.User(name=name)
                new_users.append(user)
                db.add(user)

        if whitelist:
            # fill the whitelist with any users loaded from the db,
            # so we are consistent in both directions.
            # This lets whitelist be used to set up initial list,
            # but changes to the whitelist can occur in the database,
            # and persist across sessions.
            for user in db.query(orm.User):
                whitelist.add(user.name)

        # The whitelist set and the users in the db are now the same.
        # From this point on, any user changes should be done simultaneously
        # to the whitelist set and user db, unless the whitelist is empty (all users allowed).

        db.commit()
        
        for user in new_users:
            yield self.authenticator.add_user(user)
        db.commit()
        
        user_summaries = ['']
        def _user_summary(user):
            parts = ['{0: >8}'.format(user.name)]
            if user.admin:
                parts.append('admin')
            if user.server:
                parts.append('running at %s' % user.server)
            return ' '.join(parts)
            
        @gen.coroutine
        def user_stopped(user):
            status = yield user.spawner.poll()
            self.log.warn("User %s server stopped with exit code: %s",
                user.name, status,
            )
            yield self.proxy.delete_user(user)
            yield user.stop()
        
        for user in db.query(orm.User):
            if not user.state:
                # without spawner state, server isn't valid
                user.server = None
                user_summaries.append(_user_summary(user))
                continue
            self.log.debug("Loading state for %s from db", user.name)
            user.spawner = spawner = self.spawner_class(
                user=user, hub=self.hub, config=self.config, db=self.db,
            )
            status = yield spawner.poll()
            if status is None:
                self.log.info("%s still running", user.name)
                spawner.add_poll_callback(user_stopped, user)
                spawner.start_polling()
            else:
                # user not running. This is expected if server is None,
                # but indicates the user's server died while the Hub wasn't running
                # if user.server is defined.
                log = self.log.warn if user.server else self.log.debug
                log("%s not running.", user.name)
                user.server = None

            user_summaries.append(_user_summary(user))

        self.log.debug("Loaded users: %s", '\n'.join(user_summaries))
        db.commit()

    def init_proxy(self):
        """Load the Proxy config into the database"""
        self.proxy = self.db.query(orm.Proxy).first()
        if self.proxy is None:
            self.proxy = orm.Proxy(
                public_server=orm.Server(),
                api_server=orm.Server(),
            )
            self.db.add(self.proxy)
            self.db.commit()
        self.proxy.auth_token = self.proxy_auth_token # not persisted
        self.proxy.log = self.log
        self.proxy.public_server.ip = self.ip
        self.proxy.public_server.port = self.port
        self.proxy.api_server.ip = self.proxy_api_ip
        self.proxy.api_server.port = self.proxy_api_port
        self.proxy.api_server.base_url = '/api/routes/'
        self.db.commit()
    
    @gen.coroutine
    def start_proxy(self):
        """Actually start the configurable-http-proxy"""
        # check for proxy
        if self.proxy.public_server.is_up() or self.proxy.api_server.is_up():
            # check for *authenticated* access to the proxy (auth token can change)
            try:
                yield self.proxy.get_routes()
            except (HTTPError, OSError, socket.error) as e:
                if isinstance(e, HTTPError) and e.code == 403:
                    msg = "Did CONFIGPROXY_AUTH_TOKEN change?"
                else:
                    msg = "Is something else using %s?" % self.proxy.public_server.url
                self.log.error("Proxy appears to be running at %s, but I can't access it (%s)\n%s",
                    self.proxy.public_server.url, e, msg)
                self.exit(1)
                return
            else:
                self.log.info("Proxy already running at: %s", self.proxy.public_server.url)
            self.proxy_process = None
            return

        env = os.environ.copy()
        env['CONFIGPROXY_AUTH_TOKEN'] = self.proxy.auth_token
        cmd = [self.proxy_cmd,
            '--ip', self.proxy.public_server.ip,
            '--port', str(self.proxy.public_server.port),
            '--api-ip', self.proxy.api_server.ip,
            '--api-port', str(self.proxy.api_server.port),
            '--default-target', self.hub.server.host,
        ]
        if False:
        # if self.log_level == logging.DEBUG:
            cmd.extend(['--log-level', 'debug'])
        if self.ssl_key:
            cmd.extend(['--ssl-key', self.ssl_key])
        if self.ssl_cert:
            cmd.extend(['--ssl-cert', self.ssl_cert])
        self.log.info("Starting proxy @ %s", self.proxy.public_server.url)
        self.log.debug("Proxy cmd: %s", cmd)
        self.proxy_process = Popen(cmd, env=env)
        def _check():
            status = self.proxy_process.poll()
            if status is not None:
                e = RuntimeError("Proxy failed to start with exit code %i" % status)
                # py2-compatible `raise e from None`
                e.__cause__ = None
                raise e
        
        for server in (self.proxy.public_server, self.proxy.api_server):
            for i in range(10):
                _check()
                try:
                    yield server.wait_up(1)
                except TimeoutError:
                    continue
                else:
                    break
            yield server.wait_up(1)
        self.log.debug("Proxy started and appears to be up")
    
    @gen.coroutine
    def check_proxy(self):
        if self.proxy_process.poll() is None:
            return
        self.log.error("Proxy stopped with exit code %r",
            'unknown' if self.proxy_process is None else self.proxy_process.poll()
        )
        yield self.start_proxy()
        self.log.info("Setting up routes on new proxy")
        yield self.proxy.add_all_users()
        self.log.info("New proxy back up, and good to go")
    
    def init_tornado_settings(self):
        """Set up the tornado settings dict."""
        base_url = self.hub.server.base_url
        template_path = os.path.join(self.data_files_path, 'templates'),
        jinja_env = Environment(
            loader=FileSystemLoader(template_path),
            **self.jinja_environment_options
        )
        
        login_url = self.authenticator.login_url(base_url)
        logout_url = self.authenticator.logout_url(base_url)
        
        # if running from git, disable caching of require.js
        # otherwise cache based on server start time
        parent = os.path.dirname(os.path.dirname(jupyterhub.__file__))
        if os.path.isdir(os.path.join(parent, '.git')):
            version_hash = ''
        else:
            version_hash=datetime.now().strftime("%Y%m%d%H%M%S"),
        
        settings = dict(
            config=self.config,
            log=self.log,
            db=self.db,
            proxy=self.proxy,
            hub=self.hub,
            admin_users=self.admin_users,
            authenticator=self.authenticator,
            spawner_class=self.spawner_class,
            base_url=self.base_url,
            cookie_secret=self.cookie_secret,
            login_url=login_url,
            logout_url=logout_url,
            static_path=os.path.join(self.data_files_path, 'static'),
            static_url_prefix=url_path_join(self.hub.server.base_url, 'static/'),
            static_handler_class=CacheControlStaticFilesHandler,
            template_path=template_path,
            jinja2_env=jinja_env,
            version_hash=version_hash,
        )
        # allow configured settings to have priority
        settings.update(self.tornado_settings)
        self.tornado_settings = settings
    
    def init_tornado_application(self):
        """Instantiate the tornado Application object"""
        self.tornado_application = web.Application(self.handlers, **self.tornado_settings)
    
    def write_pid_file(self):
        pid = os.getpid()
        if self.pid_file:
            self.log.debug("Writing PID %i to %s", pid, self.pid_file)
            with open(self.pid_file, 'w') as f:
                f.write('%i' % pid)
    
    @gen.coroutine
    @catch_config_error
    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        if self.generate_config or self.subapp:
            return
        self.load_config_file(self.config_file)
        self.init_logging()
        if 'JupyterHubApp' in self.config:
            self.log.warn("Use JupyterHub in config, not JupyterHubApp. Outdated config:\n%s",
                '\n'.join('JupyterHubApp.{key} = {value!r}'.format(key=key, value=value)
                    for key, value in self.config.JupyterHubApp.items()
                )
            )
            cfg = self.config.copy()
            cfg.JupyterHub.merge(cfg.JupyterHubApp)
            self.update_config(cfg)
        self.write_pid_file()
        self.init_ports()
        self.init_secrets()
        self.init_db()
        self.init_hub()
        self.init_proxy()
        yield self.init_users()
        self.init_handlers()
        self.init_tornado_settings()
        self.init_tornado_application()
    
    @gen.coroutine
    def cleanup(self):
        """Shutdown our various subprocesses and cleanup runtime files."""
        self.log.info("Cleaning up single-user servers...")
        # request (async) process termination
        futures = []
        for user in self.db.query(orm.User):
            if user.spawner is not None:
                futures.append(user.stop())
        
        # clean up proxy while SUS are shutting down
        if self.proxy_process and self.proxy_process.poll() is None:
            self.log.info("Cleaning up proxy[%i]...", self.proxy_process.pid)
            try:
                self.proxy_process.terminate()
            except Exception as e:
                self.log.error("Failed to terminate proxy process: %s", e)
        
        # wait for the requests to stop finish:
        for f in futures:
            try:
                yield f
            except Exception as e:
                self.log.error("Failed to stop user: %s", e)

        self.db.commit()
        
        if self.pid_file and os.path.exists(self.pid_file):
            self.log.info("Cleaning up PID file %s", self.pid_file)
            os.remove(self.pid_file)
        
        # finally stop the loop once we are all cleaned up
        self.log.info("...done")
    
    def write_config_file(self):
        """Write our default config to a .py config file"""
        if os.path.exists(self.config_file) and not self.answer_yes:
            answer = ''
            def ask():
                prompt = "Overwrite %s with default config? [y/N]" % self.config_file
                try:
                    return input(prompt).lower() or 'n'
                except KeyboardInterrupt:
                    print('') # empty line
                    return 'n'
            answer = ask()
            while not answer.startswith(('y', 'n')):
                print("Please answer 'yes' or 'no'")
                answer = ask()
            if answer.startswith('n'):
                return
        
        config_text = self.generate_config_file()
        if isinstance(config_text, bytes):
            config_text = config_text.decode('utf8')
        print("Writing default config to: %s" % self.config_file)
        with open(self.config_file, mode='w') as f:
            f.write(config_text)
    
    @gen.coroutine
    def update_last_activity(self):
        """Update User.last_activity timestamps from the proxy"""
        routes = yield self.proxy.get_routes()
        for prefix, route in routes.items():
            if 'user' not in route:
                # not a user route, ignore it
                continue
            user = orm.User.find(self.db, route['user'])
            if user is None:
                self.log.warn("Found no user for route: %s", route)
                continue
            try:
                dt = datetime.strptime(route['last_activity'], ISO8601_ms)
            except Exception:
                dt = datetime.strptime(route['last_activity'], ISO8601_s)
            user.last_activity = max(user.last_activity, dt)

        self.db.commit()
    
    @gen.coroutine
    def start(self):
        """Start the whole thing"""
        loop = IOLoop.current()
        
        if self.subapp:
            self.subapp.start()
            loop.stop()
            return
        
        if self.generate_config:
            self.write_config_file()
            loop.stop()
            return
        
        # start the proxy
        try:
            yield self.start_proxy()
        except Exception as e:
            self.log.critical("Failed to start proxy", exc_info=True)
            self.exit(1)
            return
        
        loop.add_callback(self.proxy.add_all_users)
        
        if self.proxy_process:
            # only check / restart the proxy if we started it in the first place.
            # this means a restarted Hub cannot restart a Proxy that its
            # predecessor started.
            pc = PeriodicCallback(self.check_proxy, 1e3 * self.proxy_check_interval)
            pc.start()
        
        if self.last_activity_interval:
            pc = PeriodicCallback(self.update_last_activity, 1e3 * self.last_activity_interval)
            pc.start()

        # start the webserver
        http_server = tornado.httpserver.HTTPServer(self.tornado_application, xheaders=True)
        http_server.listen(self.hub_port)
        # run the cleanup step (in a new loop, because the interrupted one is unclean)
        
        atexit.register(lambda : IOLoop().run_sync(self.cleanup))
    
    @gen.coroutine
    def launch_instance_async(self, argv=None):
        yield self.initialize(argv)
        yield self.start()
    
    @classmethod
    def launch_instance(cls, argv=None):
        self = cls.instance(argv=argv)
        loop = IOLoop.current()
        loop.add_callback(self.launch_instance_async, argv)
        try:
            loop.start()
        except KeyboardInterrupt:
            print("\nInterrupted")

main = JupyterHub.launch_instance

if __name__ == "__main__":
    main()
