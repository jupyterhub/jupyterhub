#!/usr/bin/env python3
"""The multi-user notebook application"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import atexit
import binascii
import logging
import os
import shutil
import signal
import socket
import sys
import threading
from datetime import datetime
from getpass import getuser
from subprocess import Popen
from urllib.parse import urlparse

if sys.version_info[:2] < (3,3):
    raise ValueError("Python < 3.3 not supported: %s" % sys.version)

from jinja2 import Environment, FileSystemLoader

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import scoped_session

import tornado.httpserver
import tornado.options
from tornado.httpclient import HTTPError
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.log import app_log, access_log, gen_log
from tornado import gen, web

from traitlets import (
    Unicode, Integer, Dict, TraitError, List, Bool, Any,
    Type, Set, Instance, Bytes, Float,
    observe, default,
)
from traitlets.config import Application, catch_config_error

here = os.path.dirname(__file__)

import jupyterhub
from . import handlers, apihandlers
from .handlers.static import CacheControlStaticFilesHandler, LogoHandler
from .services.service import Service

from . import dbutil, orm
from .user import User, UserDict
from ._data import DATA_FILES_PATH
from .log import CoroutineLogFormatter, log_request
from .traitlets import URLPrefix, Command
from .utils import (
    url_path_join,
    ISO8601_ms, ISO8601_s,
)
# classes for config
from .auth import Authenticator, PAMAuthenticator
from .spawner import Spawner, LocalProcessSpawner

# For faking stats
from .emptyclass import EmptyClass


common_aliases = {
    'log-level': 'Application.log_level',
    'f': 'JupyterHub.config_file',
    'config': 'JupyterHub.config_file',
    'db': 'JupyterHub.db_url',
}


aliases = {
    'base-url': 'JupyterHub.base_url',
    'y': 'JupyterHub.answer_yes',
    'ssl-key': 'JupyterHub.ssl_key',
    'ssl-cert': 'JupyterHub.ssl_cert',
    'ip': 'JupyterHub.ip',
    'port': 'JupyterHub.port',
    'pid-file': 'JupyterHub.pid_file',
    'log-file': 'JupyterHub.extra_log_file',
}
token_aliases = {}
token_aliases.update(common_aliases)
aliases.update(common_aliases)

flags = {
    'debug': ({'Application' : {'log_level': logging.DEBUG}},
        "set log level to logging.DEBUG (maximize logging output)"),
    'generate-config': ({'JupyterHub': {'generate_config': True}},
        "generate default config file"),
    'no-db': ({'JupyterHub': {'db_url': 'sqlite:///:memory:'}},
        "disable persisting state database to disk"
    ),
    'no-ssl': ({'JupyterHub': {'confirm_no_ssl': True}},
        "[DEPRECATED in 0.7: does nothing]"
    ),
}

SECRET_BYTES = 2048 # the number of bytes to use when generating new secrets

class NewToken(Application):
    """Generate and print a new API token"""
    name = 'jupyterhub-token'
    version = jupyterhub.__version__
    description = """Generate and return new API token for a user.

    Usage:

        jupyterhub token [username]
    """

    examples = """
        $> jupyterhub token kaylee
        ab01cd23ef45
    """

    name = Unicode(getuser())

    aliases = token_aliases
    classes = []

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
        hub.load_config_file(hub.config_file)
        hub.init_db()
        hub.hub = hub.db.query(orm.Hub).first()
        hub.init_users()
        user = orm.User.find(hub.db, self.name)
        if user is None:
            print("No such user: %s" % self.name, file=sys.stderr)
            self.exit(1)
        token = user.new_api_token()
        print(token)

class UpgradeDB(Application):
    """Upgrade the JupyterHub database schema."""

    name = 'jupyterhub-upgrade-db'
    version = jupyterhub.__version__
    description = """Upgrade the JupyterHub database to the current schema.

    Usage:

        jupyterhub upgrade-db
    """
    aliases = common_aliases
    classes = []

    def _backup_db_file(self, db_file):
        """Backup a database file"""
        if not os.path.exists(db_file):
            return

        timestamp = datetime.now().strftime('.%Y-%m-%d-%H%M%S')
        backup_db_file = db_file + timestamp
        for i in range(1, 10):
            if not os.path.exists(backup_db_file):
                break
            backup_db_file = '{}.{}.{}'.format(db_file, timestamp, i)
        if os.path.exists(backup_db_file):
            self.exit("backup db file already exists: %s" % backup_db_file)

        self.log.info("Backing up %s => %s", db_file, backup_db_file)
        shutil.copy(db_file, backup_db_file)

    def start(self):
        hub = JupyterHub(parent=self)
        hub.load_config_file(hub.config_file)
        if (hub.db_url.startswith('sqlite:///')):
            db_file = hub.db_url.split(':///', 1)[1]
            self._backup_db_file(db_file)
        self.log.info("Upgrading %s", hub.db_url)
        dbutil.upgrade(hub.db_url)


class JupyterHub(Application):
    """An Application for starting a Multi-User Jupyter Notebook server."""
    name = 'jupyterhub'
    version = jupyterhub.__version__

    description = """Start a multi-user Jupyter Notebook server

    Spawns a configurable-http-proxy and multi-user Hub,
    which authenticates users and spawns single-user Notebook servers
    on behalf of users.
    """

    examples = """

    generate default config file:

        jupyterhub --generate-config -f /etc/jupyterhub/jupyterhub_config.py

    spawn the server on 10.0.1.2:443 with https:

        jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert
    """

    aliases = Dict(aliases)
    flags = Dict(flags)

    subcommands = {
        'token': (NewToken, "Generate an API token for a user"),
        'upgrade-db': (UpgradeDB, "Upgrade your JupyterHub state database to the current version."),
    }

    classes = List([
        Spawner,
        LocalProcessSpawner,
        Authenticator,
        PAMAuthenticator,
    ])

    load_groups = Dict(List(Unicode()),
        help="""Dict of 'group': ['usernames'] to load at startup.

        This strictly *adds* groups and users to groups.

        Loading one set of groups, then starting JupyterHub again with a different
        set will not remove users or groups from previous launches.
        That must be done through the API.
        """
    ).tag(config=True)

    config_file = Unicode('jupyterhub_config.py',
        help="The config file to load",
    ).tag(config=True)
    generate_config = Bool(False,
        help="Generate default config file",
    ).tag(config=True)
    answer_yes = Bool(False,
        help="Answer yes to any questions (e.g. confirm overwrite)"
    ).tag(config=True)
    pid_file = Unicode('',
        help="""File to write PID
        Useful for daemonizing jupyterhub.
        """
    ).tag(config=True)
    cookie_max_age_days = Float(14,
        help="""Number of days for a login cookie to be valid.
        Default is two weeks.
        """
    ).tag(config=True)
    last_activity_interval = Integer(300,
        help="Interval (in seconds) at which to update last-activity timestamps."
    ).tag(config=True)
    proxy_check_interval = Integer(30,
        help="Interval (in seconds) at which to check if the proxy is running."
    ).tag(config=True)

    data_files_path = Unicode(DATA_FILES_PATH,
        help="The location of jupyterhub data files (e.g. /usr/local/share/jupyter/hub)"
    ).tag(config=True)

    template_paths = List(
        help="Paths to search for jinja templates.",
    ).tag(config=True)

    @default('template_paths')
    def _template_paths_default(self):
        return [os.path.join(self.data_files_path, 'templates')]

    confirm_no_ssl = Bool(False,
        help="""DEPRECATED: does nothing"""
    ).tag(config=True)
    ssl_key = Unicode('',
        help="""Path to SSL key file for the public facing interface of the proxy

        Use with ssl_cert
        """
    ).tag(config=True)
    ssl_cert = Unicode('',
        help="""Path to SSL certificate file for the public facing interface of the proxy

        Use with ssl_key
        """
    ).tag(config=True)
    ip = Unicode('',
        help="The public facing ip of the whole application (the proxy)"
    ).tag(config=True)

    subdomain_host = Unicode('',
        help="""Run single-user servers on subdomains of this host.

        This should be the full https://hub.domain.tld[:port]

        Provides additional cross-site protections for javascript served by single-user servers.

        Requires <username>.hub.domain.tld to resolve to the same host as hub.domain.tld.

        In general, this is most easily achieved with wildcard DNS.

        When using SSL (i.e. always) this also requires a wildcard SSL certificate.
        """
    ).tag(config=True)
    def _subdomain_host_changed(self, name, old, new):
        if new and '://' not in new:
            # host should include '://'
            # if not specified, assume https: You have to be really explicit about HTTP!
            self.subdomain_host = 'https://' + new

    domain = Unicode(
        help="domain name, e.g. 'example.com' (excludes protocol, port)"
    )
    @default('domain')
    def _domain_default(self):
        if not self.subdomain_host:
            return ''
        return urlparse(self.subdomain_host).hostname

    port = Integer(8000,
        help="The public facing port of the proxy"
    ).tag(config=True)
    base_url = URLPrefix('/',
        help="The base URL of the entire application"
    ).tag(config=True)
    logo_file = Unicode('',
        help="Specify path to a logo image to override the Jupyter logo in the banner."
    ).tag(config=True)

    @default('logo_file')
    def _logo_file_default(self):
        return os.path.join(self.data_files_path, 'static', 'images', 'jupyter.png')

    jinja_environment_options = Dict(
        help="Supply extra arguments that will be passed to Jinja environment."
    ).tag(config=True)

    proxy_cmd = Command('configurable-http-proxy',
        help="""The command to start the http proxy.

        Only override if configurable-http-proxy is not on your PATH
        """
    ).tag(config=True)
    debug_proxy = Bool(False,
        help="show debug output in configurable-http-proxy"
    ).tag(config=True)
    proxy_auth_token = Unicode(
        help="""The Proxy Auth token.

        Loaded from the CONFIGPROXY_AUTH_TOKEN env variable by default.
        """
    ).tag(config=True)

    @default('proxy_auth_token')
    def _proxy_auth_token_default(self):
        token = os.environ.get('CONFIGPROXY_AUTH_TOKEN', None)
        if not token:
            self.log.warning('\n'.join([
                "",
                "Generating CONFIGPROXY_AUTH_TOKEN. Restarting the Hub will require restarting the proxy.",
                "Set CONFIGPROXY_AUTH_TOKEN env or JupyterHub.proxy_auth_token config to avoid this message.",
                "",
            ]))
            token = orm.new_token()
        return token

    proxy_api_ip = Unicode('127.0.0.1',
        help="The ip for the proxy API handlers"
    ).tag(config=True)
    proxy_api_port = Integer(
        help="The port for the proxy API handlers"
    ).tag(config=True)

    @default('proxy_api_port')
    def _proxy_api_port_default(self):
        return self.port + 1

    hub_port = Integer(8081,
        help="The port for this process"
    ).tag(config=True)
    hub_ip = Unicode('127.0.0.1',
        help="The ip for this process"
    ).tag(config=True)
    hub_prefix = URLPrefix('/hub/',
        help="The prefix for the hub server.  Always /base_url/hub/"
    )

    @default('hub_prefix')
    def _hub_prefix_default(self):
        return url_path_join(self.base_url, '/hub/')

    @observe('base_url')
    def _update_hub_prefix(self, change):
        """add base URL to hub prefix"""
        base_url = change['new']
        self.hub_prefix = self._hub_prefix_default()

    cookie_secret = Bytes(
        help="""The cookie secret to use to encrypt cookies.

        Loaded from the JPY_COOKIE_SECRET env variable by default.
        """
    ).tag(
        config=True,
        env='JPY_COOKIE_SECRET',
    )

    cookie_secret_file = Unicode('jupyterhub_cookie_secret',
        help="""File in which to store the cookie secret."""
    ).tag(config=True)

    api_tokens = Dict(Unicode(),
        help="""PENDING DEPRECATION: consider using service_tokens

        Dict of token:username to be loaded into the database.

        Allows ahead-of-time generation of API tokens for use by externally managed services,
        which authenticate as JupyterHub users.

        Consider using service_tokens for general services that talk to the JupyterHub API.
        """
    ).tag(config=True)
    @observe('api_tokens')
    def _deprecate_api_tokens(self, change):
        self.log.warning("JupyterHub.api_tokens is pending deprecation."
            "  Consider using JupyterHub.service_tokens."
            "  If you have a use case for services that identify as users,"
            " let us know: https://github.com/jupyterhub/jupyterhub/issues"
        )

    service_tokens = Dict(Unicode(),
        help="""Dict of token:servicename to be loaded into the database.

        Allows ahead-of-time generation of API tokens for use by externally managed services.
        """
    ).tag(config=True)

    services = List(Dict(),
        help="""List of service specification dictionaries.

        A service

        For instance::

            services = [
                {
                    'name': 'cull_idle',
                    'command': ['/path/to/cull_idle_servers.py'],
                },
                {
                    'name': 'formgrader',
                    'url': 'http://127.0.0.1:1234',
                    'token': 'super-secret',
                    'environment': 
                }
            ]
        """
    ).tag(config=True)
    _service_map = Dict()

    authenticator_class = Type(PAMAuthenticator, Authenticator,
        help="""Class for authenticating users.

        This should be a class with the following form:

        - constructor takes one kwarg: `config`, the IPython config object.

        - is a tornado.gen.coroutine
        - returns username on success, None on failure
        - takes two arguments: (handler, data),
          where `handler` is the calling web.RequestHandler,
          and `data` is the POST form data from the login page.
        """
    ).tag(config=True)

    authenticator = Instance(Authenticator)

    @default('authenticator')
    def _authenticator_default(self):
        return self.authenticator_class(parent=self, db=self.db)

    # class for spawning single-user servers
    spawner_class = Type(LocalProcessSpawner, Spawner,
        help="""The class to use for spawning single-user servers.

        Should be a subclass of Spawner.
        """
    ).tag(config=True)

    db_url = Unicode('sqlite:///jupyterhub.sqlite',
        help="url for the database. e.g. `sqlite:///jupyterhub.sqlite`"
    ).tag(config=True)

    @observe('db_url')
    def _db_url_changed(self, change):
        new = change['new']
        if '://' not in new:
            # assume sqlite, if given as a plain filename
            self.db_url = 'sqlite:///%s' % new

    db_kwargs = Dict(
        help="""Include any kwargs to pass to the database connection.
        See sqlalchemy.create_engine for details.
        """
    ).tag(config=True)

    reset_db = Bool(False,
        help="Purge and reset the database."
    ).tag(config=True)
    debug_db = Bool(False,
        help="log all database transactions. This has A LOT of output"
    ).tag(config=True)
    session_factory = Any()

    users = Instance(UserDict)

    @default('users')
    def _users_default(self):
        assert self.tornado_settings
        return UserDict(db_factory=lambda : self.db, settings=self.tornado_settings)

    admin_access = Bool(False,
        help="""Grant admin users permission to access single-user servers.

        Users should be properly informed if this is enabled.
        """
    ).tag(config=True)
    admin_users = Set(
        help="""DEPRECATED, use Authenticator.admin_users instead."""
    ).tag(config=True)

    tornado_settings = Dict(
        help="Extra settings overrides to pass to the tornado application."
    ).tag(config=True)

    cleanup_servers = Bool(True,
        help="""Whether to shutdown single-user servers when the Hub shuts down.

        Disable if you want to be able to teardown the Hub while leaving the single-user servers running.

        If both this and cleanup_proxy are False, sending SIGINT to the Hub will
        only shutdown the Hub, leaving everything else running.

        The Hub should be able to resume from database state.
        """
    ).tag(config=True)

    cleanup_proxy = Bool(True,
        help="""Whether to shutdown the proxy when the Hub shuts down.

        Disable if you want to be able to teardown the Hub while leaving the proxy running.

        Only valid if the proxy was starting by the Hub process.

        If both this and cleanup_servers are False, sending SIGINT to the Hub will
        only shutdown the Hub, leaving everything else running.

        The Hub should be able to resume from database state.
        """
    ).tag(config=True)

    statsd_host = Unicode(
        help="Host to send statsd metrics to"
    ).tag(config=True)

    statsd_port = Integer(
        8125,
        help="Port on which to send statsd metrics about the hub"
    ).tag(config=True)

    statsd_prefix = Unicode(
        'jupyterhub',
        help="Prefix to use for all metrics sent by jupyterhub to statsd"
    ).tag(config=True)

    handlers = List()

    _log_formatter_cls = CoroutineLogFormatter
    http_server = None
    proxy_process = None
    io_loop = None

    @default('log_level')
    def _log_level_default(self):
        return logging.INFO

    @default('log_datefmt')
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    @default('log_format')
    def _log_format_default(self):
        """override default log format to include time"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    extra_log_file = Unicode(
        help="""Send JupyterHub's logs to this file.

        This will *only* include the logs of the Hub itself,
        not the logs of the proxy or any single-user servers.
        """
    ).tag(config=True)
    extra_log_handlers = List(
        Instance(logging.Handler),
        help="Extra log handlers to set on JupyterHub logger",
    ).tag(config=True)

    statsd = Any(allow_none=False, help="The statsd client, if any. A mock will be used if we aren't using statsd")
    @default('statsd')
    def _statsd(self):
        if self.statsd_host:
            import statsd
            client = statsd.StatsClient(
                self.statsd_host,
                self.statsd_port,
                self.statsd_prefix
            )
            return client
        else:
            # return an empty mock object!
            return EmptyClass()

    def init_logging(self):
        # This prevents double log messages because tornado use a root logger that
        # self.log is a child of. The logging module dipatches log messages to a log
        # and all of its ancenstors until propagate is set to False.
        self.log.propagate = False

        if self.extra_log_file:
            self.extra_log_handlers.append(
                logging.FileHandler(self.extra_log_file)
            )

        _formatter = self._log_formatter_cls(
            fmt=self.log_format,
            datefmt=self.log_datefmt,
        )
        for handler in self.extra_log_handlers:
            if handler.formatter is None:
                handler.setFormatter(_formatter)
            self.log.addHandler(handler)

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
        # load handlers from the authenticator
        h.extend(self.authenticator.get_handlers(self))
        # set default handlers
        h.extend(handlers.default_handlers)
        h.extend(apihandlers.default_handlers)

        h.append((r'/logo', LogoHandler, {'path': self.logo_file}))
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
        env_name = trait.metadata.get('env')
        secret_file = os.path.abspath(
            os.path.expanduser(self.cookie_secret_file)
        )
        secret = self.cookie_secret
        secret_from = 'config'
        # load priority: 1. config, 2. env, 3. file
        secret_env = os.environ.get(env_name)
        if not secret and secret_env:
            secret_from = 'env'
            self.log.info("Loading %s from env[%s]", trait_name, env_name)
            secret = binascii.a2b_hex(secret_env)
        if not secret and os.path.exists(secret_file):
            secret_from = 'file'
            self.log.info("Loading %s from %s", trait_name, secret_file)
            try:
                perm = os.stat(secret_file).st_mode
                if perm & 0o07:
                    raise ValueError("cookie_secret_file can be read or written by anybody")
                with open(secret_file) as f:
                    b64_secret = f.read()
                secret = binascii.a2b_base64(b64_secret)
            except Exception as e:
                self.log.error(
                    "Refusing to run JupyterHub with invalid cookie_secret_file. "
                    "%s error was: %s",
                    secret_file, e)
                self.exit(1)
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
                self.log.warning("Failed to set permissions on %s", secret_file)
        # store the loaded trait value
        self.cookie_secret = secret

    # thread-local storage of db objects
    _local = Instance(threading.local, ())
    @property
    def db(self):
        if not hasattr(self._local, 'db'):
            self._local.db = scoped_session(self.session_factory)()
        return self._local.db

    @property
    def hub(self):
        if not getattr(self._local, 'hub', None):
            q = self.db.query(orm.Hub)
            assert q.count() <= 1
            self._local.hub = q.first()
            if self.subdomain_host and self._local.hub:
                self._local.hub.host = self.subdomain_host
        return self._local.hub

    @hub.setter
    def hub(self, hub):
        self._local.hub = hub
        if hub and self.subdomain_host:
            hub.host = self.subdomain_host

    @property
    def proxy(self):
        if not getattr(self._local, 'proxy', None):
            q = self.db.query(orm.Proxy)
            assert q.count() <= 1
            p = self._local.proxy = q.first()
            if p:
                p.auth_token = self.proxy_auth_token
        return self._local.proxy

    @proxy.setter
    def proxy(self, proxy):
        self._local.proxy = proxy

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
            # trigger constructing thread local db property
            _ = self.db
        except OperationalError as e:
            self.log.error("Failed to connect to db: %s", self.db_url)
            self.log.debug("Database error was:", exc_info=True)
            if self.db_url.startswith('sqlite:///'):
                self._check_db_path(self.db_url.split(':///', 1)[1])
            self.log.critical('\n'.join([
                "If you recently upgraded JupyterHub, try running",
                "    jupyterhub upgrade-db",
                "to upgrade your JupyterHub database schema",
            ]))
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
        if self.subdomain_host:
            if not self.subdomain_host:
                raise ValueError("Must specify subdomain_host when using subdomains."
                " This should be the public domain[:port] of the Hub.")

        self.db.commit()

    @gen.coroutine
    def init_users(self):
        """Load users into and from the database"""
        db = self.db

        if self.admin_users and not self.authenticator.admin_users:
            self.log.warning(
                "\nJupyterHub.admin_users is deprecated."
                "\nUse Authenticator.admin_users instead."
            )
            self.authenticator.admin_users = self.admin_users
        admin_users = [
            self.authenticator.normalize_username(name)
            for name in self.authenticator.admin_users
        ]
        self.authenticator.admin_users = set(admin_users) # force normalization
        for username in admin_users:
            if not self.authenticator.validate_username(username):
                raise ValueError("username %r is not valid" % username)

        if not admin_users:
            self.log.warning("No admin users, admin interface will be unavailable.")
            self.log.warning("Add any administrative users to `c.Authenticator.admin_users` in config.")

        new_users = []

        for name in admin_users:
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

        whitelist = [
            self.authenticator.normalize_username(name)
            for name in self.authenticator.whitelist
        ]
        self.authenticator.whitelist = set(whitelist) # force normalization
        for username in whitelist:
            if not self.authenticator.validate_username(username):
                raise ValueError("username %r is not valid" % username)

        if not whitelist:
            self.log.info("Not using whitelist. Any authenticated user will be allowed.")

        # add whitelisted users to the db
        for name in whitelist:
            user = orm.User.find(db, name)
            if user is None:
                user = orm.User(name=name)
                new_users.append(user)
                db.add(user)

        db.commit()

        # Notify authenticator of all users.
        # This ensures Auth whitelist is up-to-date with the database.
        # This lets whitelist be used to set up initial list,
        # but changes to the whitelist can occur in the database,
        # and persist across sessions.
        for user in db.query(orm.User):
            try:
                yield gen.maybe_future(self.authenticator.add_user(user))
            except Exception:
                # TODO: Review approach to synchronize whitelist with db
                # known cause of the exception is a user who has already been removed from the system
                # but the user still exists in the hub's user db
                self.log.exception("Error adding user %r already in db", user.name)
        db.commit() # can add_user touch the db?

        # The whitelist set and the users in the db are now the same.
        # From this point on, any user changes should be done simultaneously
        # to the whitelist set and user db, unless the whitelist is empty (all users allowed).

    @gen.coroutine
    def init_groups(self):
        """Load predefined groups into the database"""
        db = self.db
        for name, usernames in self.load_groups.items():
            group = orm.Group.find(db, name)
            if group is None:
                group = orm.Group(name=name)
                db.add(group)
            for username in usernames:
                username = self.authenticator.normalize_username(username)
                if not (yield gen.maybe_future(self.authenticator.check_whitelist(username))):
                    raise ValueError("Username %r is not in whitelist" % username)
                user = orm.User.find(db, name=username)
                if user is None:
                    if not self.authenticator.validate_username(username):
                        raise ValueError("Group username %r is not valid" % username)
                    user = orm.User(name=username)
                    db.add(user)
                group.users.append(user)
        db.commit()

    @gen.coroutine
    def _add_tokens(self, token_dict, kind):
        """Add tokens for users or services to the database"""
        if kind == 'user':
            Class = orm.User
        elif kind == 'service':
            Class = orm.Service
        else:
            raise ValueError("kind must be user or service, not %r" % kind)

        db = self.db
        for token, name in token_dict.items():
            if kind == 'user':
                name = self.authenticator.normalize_username(name)
                if not (yield gen.maybe_future(self.authenticator.check_whitelist(name))):
                    raise ValueError("Token name %r is not in whitelist" % name)
                if not self.authenticator.validate_username(name):
                    raise ValueError("Token name %r is not valid" % name)
            orm_token = orm.APIToken.find(db, token)
            if orm_token is None:
                obj = Class.find(db, name)
                created = False
                if obj is None:
                    created = True
                    self.log.debug("Adding %s %r to database", kind, name)
                    obj = Class(name=name)
                    db.add(obj)
                    db.commit()
                self.log.info("Adding API token for %s: %s", kind, name)
                try:
                    obj.new_api_token(token)
                except Exception:
                    if created:
                        # don't allow bad tokens to create users
                        db.delete(obj)
                        db.commit()
                        raise
            else:
                self.log.debug("Not duplicating token %s", orm_token)
        db.commit()

    @gen.coroutine
    def init_api_tokens(self):
        """Load predefined API tokens (for services) into database"""
        yield self._add_tokens(self.service_tokens, kind='service')
        yield self._add_tokens(self.api_tokens, kind='user')

    def init_services(self):
        self._service_map.clear()
        if self.domain:
            domain = 'services.' + self.domain
            parsed = urlparse(self.subdomain_host)
            host = '%s://services.%s' % (parsed.scheme, parsed.netloc)
        else:
            domain = host = ''
        for spec in self.services:
            if 'name' not in spec:
                raise ValueError('service spec must have a name: %r' % spec)
            name = spec['name']
            # get/create orm
            orm_service = orm.Service.find(self.db, name=name)
            if orm_service is None:
                # not found, create a new one
                orm_service = orm.Service(name=name)
                self.db.add(orm_service)
            orm_service.admin = spec.get('admin', False)
            self.db.commit()
            service = Service(parent=self,
                base_url=self.base_url,
                db=self.db, orm=orm_service,
                domain=domain, host=host,
                hub_api_url=self.hub.api_url,
            )

            traits = service.traits(input=True)
            for key, value in spec.items():
                if key not in traits:
                    raise AttributeError("No such service field: %s" % key)
                setattr(service, key, value)

            if service.url:
                parsed = urlparse(service.url)
                if parsed.port is not None:
                    port = parsed.port
                elif parsed.scheme == 'http':
                    port = 80
                elif parsed.scheme == 'https':
                    port = 443
                server = service.orm.server = orm.Server(
                    proto=parsed.scheme,
                    ip=parsed.hostname,
                    port=port,
                    cookie_name='jupyterhub-services',
                    base_url=service.prefix,
                )
                self.db.add(server)
            else:
                service.orm.server = None

            self._service_map[name] = service
            if service.managed:
                if not service.api_token:
                    # generate new token
                    service.api_token = service.orm.new_api_token()
                else:
                    # ensure provided token is registered
                    self.service_tokens[service.api_token] = service.name
            else:
                self.service_tokens[service.api_token] = service.name

        # delete services from db not in service config:
        for service in self.db.query(orm.Service):
            if service.name not in self._service_map:
                self.db.delete(service)
        self.db.commit()

    @gen.coroutine
    def init_spawners(self):
        db = self.db

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
            self.log.warning("User %s server stopped with exit code: %s",
                user.name, status,
            )
            yield self.proxy.delete_user(user)
            yield user.stop()

        for orm_user in db.query(orm.User):
            self.users[orm_user.id] = user = User(orm_user, self.tornado_settings)
            self.log.debug("Loading state for %s from db", user.name)
            spawner = user.spawner
            status = yield spawner.poll()
            if status is None:
                self.log.info("%s still running", user.name)
                spawner.add_poll_callback(user_stopped, user)
                spawner.start_polling()
            else:
                # user not running. This is expected if server is None,
                # but indicates the user's server died while the Hub wasn't running
                # if user.server is defined.
                log = self.log.warning if user.server else self.log.debug
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
        self.proxy.public_server.base_url = self.base_url
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
                routes = yield self.proxy.get_routes()
            except (HTTPError, OSError, socket.error) as e:
                if isinstance(e, HTTPError) and e.code == 403:
                    msg = "Did CONFIGPROXY_AUTH_TOKEN change?"
                else:
                    msg = "Is something else using %s?" % self.proxy.public_server.bind_url
                self.log.error("Proxy appears to be running at %s, but I can't access it (%s)\n%s",
                    self.proxy.public_server.bind_url, e, msg)
                self.exit(1)
                return
            else:
                self.log.info("Proxy already running at: %s", self.proxy.public_server.bind_url)
                yield self.proxy.check_routes(self.users, self._service_map, routes)
            self.proxy_process = None
            return

        env = os.environ.copy()
        env['CONFIGPROXY_AUTH_TOKEN'] = self.proxy.auth_token
        cmd = self.proxy_cmd + [
            '--ip', self.proxy.public_server.ip,
            '--port', str(self.proxy.public_server.port),
            '--api-ip', self.proxy.api_server.ip,
            '--api-port', str(self.proxy.api_server.port),
            '--default-target', self.hub.server.host,
            '--error-target', url_path_join(self.hub.server.url, 'error'),
        ]
        if self.subdomain_host:
            cmd.append('--host-routing')
        if self.debug_proxy:
            cmd.extend(['--log-level', 'debug'])
        if self.ssl_key:
            cmd.extend(['--ssl-key', self.ssl_key])
        if self.ssl_cert:
            cmd.extend(['--ssl-cert', self.ssl_cert])
        if self.statsd_host:
            cmd.extend([
                '--statsd-host', self.statsd_host,
                '--statsd-port', str(self.statsd_port),
                '--statsd-prefix', self.statsd_prefix + '.chp'
            ])
        # Warn if SSL is not used
        if ' --ssl' not in ' '.join(cmd):
            self.log.warning("Running JupyterHub without SSL."
                "  I hope there is SSL termination happening somewhere else...")
        self.log.info("Starting proxy @ %s", self.proxy.public_server.bind_url)
        self.log.debug("Proxy cmd: %s", cmd)
        try:
            self.proxy_process = Popen(cmd, env=env, start_new_session=True)
        except FileNotFoundError as e:
            self.log.error(
                "Failed to find proxy %r\n"
                "The proxy can be installed with `npm install -g configurable-http-proxy`"
                 % self.proxy_cmd
            )
            self.exit(1)
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
        yield self.proxy.add_all_users(self.users)
        yield self.proxy.add_all_services(self.services)
        self.log.info("New proxy back up, and good to go")

    def init_tornado_settings(self):
        """Set up the tornado settings dict."""
        base_url = self.hub.server.base_url
        jinja_options = dict(
            autoescape=True,
        )
        jinja_options.update(self.jinja_environment_options)
        jinja_env = Environment(
            loader=FileSystemLoader(self.template_paths),
            **jinja_options
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
            log_function=log_request,
            config=self.config,
            log=self.log,
            db=self.db,
            proxy=self.proxy,
            hub=self.hub,
            admin_users=self.authenticator.admin_users,
            admin_access=self.admin_access,
            authenticator=self.authenticator,
            spawner_class=self.spawner_class,
            base_url=self.base_url,
            cookie_secret=self.cookie_secret,
            cookie_max_age_days=self.cookie_max_age_days,
            login_url=login_url,
            logout_url=logout_url,
            static_path=os.path.join(self.data_files_path, 'static'),
            static_url_prefix=url_path_join(self.hub.server.base_url, 'static/'),
            static_handler_class=CacheControlStaticFilesHandler,
            template_path=self.template_paths,
            jinja2_env=jinja_env,
            version_hash=version_hash,
            subdomain_host=self.subdomain_host,
            domain=self.domain,
            statsd=self.statsd,
        )
        # allow configured settings to have priority
        settings.update(self.tornado_settings)
        self.tornado_settings = settings
        # constructing users requires access to tornado_settings
        self.tornado_settings['users'] = self.users
        self.tornado_settings['services'] = self._service_map

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
            self.log.warning("Use JupyterHub in config, not JupyterHubApp. Outdated config:\n%s",
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
        yield self.init_groups()
        self.init_services()
        yield self.init_api_tokens()
        self.init_tornado_settings()
        yield self.init_spawners()
        self.init_handlers()
        self.init_tornado_application()

    @gen.coroutine
    def cleanup(self):
        """Shutdown managed services and various subprocesses. Cleanup runtime files."""

        futures = []

        managed_services = [ s for s in self._service_map.values() if s.managed ]
        if managed_services:
            self.log.info("Cleaning up %i services...", len(managed_services))
            for service in managed_services:
                futures.append(service.stop())

        if self.cleanup_servers:
            self.log.info("Cleaning up single-user servers...")
            # request (async) process termination
            for uid, user in self.users.items():
                if user.spawner is not None:
                    futures.append(user.stop())
        else:
            self.log.info("Leaving single-user servers running")

        # clean up proxy while single-user servers are shutting down
        if self.cleanup_proxy:
            if self.proxy_process:
                self.log.info("Cleaning up proxy[%i]...", self.proxy_process.pid)
                if self.proxy_process.poll() is None:
                    try:
                        self.proxy_process.terminate()
                    except Exception as e:
                        self.log.error("Failed to terminate proxy process: %s", e)
            else:
                self.log.info("I didn't start the proxy, I can't clean it up")
        else:
            self.log.info("Leaving proxy running")


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
        config_file_dir = os.path.dirname(os.path.abspath(self.config_file))
        if not os.path.isdir(config_file_dir):
            self.exit("{} does not exist. The destination directory must exist before generating config file.".format(
                config_file_dir,
            ))
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
        users_count = 0
        active_users_count = 0
        for prefix, route in routes.items():
            if 'user' not in route:
                # not a user route, ignore it
                continue
            user = orm.User.find(self.db, route['user'])
            if user is None:
                self.log.warning("Found no user for route: %s", route)
                continue
            try:
                dt = datetime.strptime(route['last_activity'], ISO8601_ms)
            except Exception:
                dt = datetime.strptime(route['last_activity'], ISO8601_s)
            user.last_activity = max(user.last_activity, dt)
            # FIXME: Make this configurable duration. 30 minutes for now!
            if (datetime.now() - user.last_activity).total_seconds() < 30 * 60:
                active_users_count += 1
            users_count += 1
        self.statsd.gauge('users.running', users_count)
        self.statsd.gauge('users.active', active_users_count)

        self.db.commit()
        yield self.proxy.check_routes(self.users, self._service_map, routes)

    @gen.coroutine
    def start(self):
        """Start the whole thing"""
        self.io_loop = loop = IOLoop.current()

        if self.subapp:
            self.subapp.start()
            loop.stop()
            return

        if self.generate_config:
            self.write_config_file()
            loop.stop()
            return

        # start the webserver
        self.http_server = tornado.httpserver.HTTPServer(self.tornado_application, xheaders=True)
        try:
            self.http_server.listen(self.hub_port, address=self.hub_ip)
        except Exception:
            self.log.error("Failed to bind hub to %s", self.hub.server.bind_url)
            raise
        else:
            self.log.info("Hub API listening on %s", self.hub.server.bind_url)

        # start the proxy
        try:
            yield self.start_proxy()
        except Exception as e:
            self.log.critical("Failed to start proxy", exc_info=True)
            self.exit(1)

        for service_name, service in self._service_map.items():
            if not service.managed:
                continue
            try:
                service.start()
            except Exception as e:
                self.log.critical("Failed to start service %s", service_name, exc_info=True)
                self.exit(1)

        loop.add_callback(self.proxy.add_all_users, self.users)
        loop.add_callback(self.proxy.add_all_services, self._service_map)

        if self.proxy_process:
            # only check / restart the proxy if we started it in the first place.
            # this means a restarted Hub cannot restart a Proxy that its
            # predecessor started.
            pc = PeriodicCallback(self.check_proxy, 1e3 * self.proxy_check_interval)
            pc.start()

        if self.last_activity_interval:
            pc = PeriodicCallback(self.update_last_activity, 1e3 * self.last_activity_interval)
            pc.start()

        self.log.info("JupyterHub is now running at %s", self.proxy.public_server.url)
        # register cleanup on both TERM and INT
        atexit.register(self.atexit)
        self.init_signal()

    def init_signal(self):
        signal.signal(signal.SIGTERM, self.sigterm)

    def sigterm(self, signum, frame):
        self.log.critical("Received SIGTERM, shutting down")
        self.io_loop.stop()
        self.atexit()

    _atexit_ran = False
    def atexit(self):
        """atexit callback"""
        if self._atexit_ran:
            return
        self._atexit_ran = True
        # run the cleanup step (in a new loop, because the interrupted one is unclean)
        IOLoop.clear_current()
        loop = IOLoop()
        loop.make_current()
        loop.run_sync(self.cleanup)


    def stop(self):
        if not self.io_loop:
            return
        if self.http_server:
            if self.io_loop._running:
                self.io_loop.add_callback(self.http_server.stop)
            else:
                self.http_server.stop()
        self.io_loop.add_callback(self.io_loop.stop)

    @gen.coroutine
    def launch_instance_async(self, argv=None):
        try:
            yield self.initialize(argv)
            yield self.start()
        except Exception as e:
            self.log.exception("")
            self.exit(1)

    @classmethod
    def launch_instance(cls, argv=None):
        self = cls.instance()
        loop = IOLoop.current()
        loop.add_callback(self.launch_instance_async, argv)
        try:
            loop.start()
        except KeyboardInterrupt:
            print("\nInterrupted")

NewToken.classes.append(JupyterHub)
UpgradeDB.classes.append(JupyterHub)

main = JupyterHub.launch_instance

if __name__ == "__main__":
    main()
