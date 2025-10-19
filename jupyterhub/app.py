#!/usr/bin/env python3
"""The multi-user notebook application"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import atexit
import binascii
import logging
import os
import re
import secrets
import shlex
import signal
import socket
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial
from getpass import getuser
from operator import itemgetter
from pathlib import Path
from textwrap import dedent
from typing import Optional
from urllib.parse import unquote, urlparse, urlunparse

import tornado.httpserver
import tornado.options
from dateutil.parser import parse as parse_date
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PrefixLoader
from jupyter_events.logger import EventLogger
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import contains_eager, selectinload
from tornado import gen, web
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.log import access_log, app_log, gen_log
from traitlets import (
    Any,
    Bool,
    Bytes,
    Dict,
    Float,
    Instance,
    Integer,
    List,
    Set,
    Tuple,
    Unicode,
    Union,
    default,
    observe,
    validate,
)
from traitlets.config import Application, Configurable, catch_config_error

here = os.path.dirname(__file__)

import jupyterhub

from . import apihandlers, crypto, dbutil, handlers, orm, roles, scopes
from ._data import DATA_FILES_PATH

# classes for config
from .auth import Authenticator, PAMAuthenticator
from .crypto import CryptKeeper

# For faking stats
from .emptyclass import EmptyClass
from .handlers.static import CacheControlStaticFilesHandler, LogoHandler
from .log import CoroutineLogFormatter, log_request
from .metrics import (
    HUB_STARTUP_DURATION_SECONDS,
    INIT_SPAWNERS_DURATION_SECONDS,
    RUNNING_SERVERS,
    TOTAL_USERS,
    PeriodicMetricsCollector,
)
from .oauth.provider import make_provider
from .objects import Hub, Server
from .proxy import ConfigurableHTTPProxy, Proxy
from .services.service import Service
from .spawner import LocalProcessSpawner, Spawner
from .traitlets import Callable, Command, EntryPointType, URLPrefix
from .user import UserDict
from .utils import (
    AnyTimeoutError,
    catch_db_error,
    make_ssl_context,
    maybe_future,
    print_ps_info,
    print_stacks,
    subdomain_hook_idna,
    subdomain_hook_legacy,
    url_path_join,
    utcnow,
)

common_aliases = {
    'log-level': 'Application.log_level',
    'f': 'JupyterHub.config_file',
    'config': 'JupyterHub.config_file',
    'db': 'JupyterHub.db_url',
}
if isinstance(Application.aliases, dict):
    common_aliases.update(Application.aliases)

aliases = {
    'base-url': 'JupyterHub.base_url',
    'y': 'JupyterHub.answer_yes',
    'ssl-key': 'JupyterHub.ssl_key',
    'ssl-cert': 'JupyterHub.ssl_cert',
    'url': 'JupyterHub.bind_url',
    'ip': 'JupyterHub.ip',
    'port': 'JupyterHub.port',
    'pid-file': 'JupyterHub.pid_file',
    'log-file': 'JupyterHub.extra_log_file',
}
token_aliases = {}
token_aliases.update(common_aliases)
aliases.update(common_aliases)

flags = {}
if isinstance(Application.flags, dict):
    flags.update(Application.flags)
hub_flags = {
    'debug': (
        {'Application': {'log_level': logging.DEBUG}},
        "set log level to logging.DEBUG (maximize logging output)",
    ),
    'generate-config': (
        {'JupyterHub': {'generate_config': True}},
        "generate default config file",
    ),
    'generate-certs': (
        {'JupyterHub': {'generate_certs': True}},
        "generate certificates used for internal ssl",
    ),
    'no-db': (
        {'JupyterHub': {'db_url': 'sqlite:///:memory:'}},
        "disable persisting state database to disk",
    ),
    'upgrade-db': (
        {'JupyterHub': {'upgrade_db': True}},
        """Automatically upgrade the database if needed on startup.

        Only safe if the database has been backed up.
        Only SQLite database files will be backed up automatically.
        """,
    ),
    'no-ssl': (
        {'JupyterHub': {'confirm_no_ssl': True}},
        "[DEPRECATED in 0.7: does nothing]",
    ),
}
flags.update(hub_flags)

COOKIE_SECRET_BYTES = (
    32  # the number of bytes to use when generating new cookie secrets
)

HEX_RE = re.compile('^([a-f0-9]{2})+$', re.IGNORECASE)

_mswindows = os.name == "nt"


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

    name = Unicode()

    @default('name')
    def _default_name(self):
        return getuser()

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

        def init_roles_and_users():
            loop = asyncio.new_event_loop()
            loop.run_until_complete(hub.init_role_creation())
            loop.run_until_complete(hub.init_users())

        ThreadPoolExecutor(1).submit(init_roles_and_users).result()
        user = orm.User.find(hub.db, self.name)
        if user is None:
            print(f"No such user: {self.name}", file=sys.stderr)
            self.exit(1)
        token = user.new_api_token(note="command-line generated")
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

    def start(self):
        hub = JupyterHub(parent=self)
        hub.load_config_file(hub.config_file)
        self.log = hub.log
        dbutil.upgrade_if_needed(hub.db_url, log=self.log)


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

    raise_config_file_errors = True

    subcommands = {
        'token': (NewToken, "Generate an API token for a user"),
        'upgrade-db': (
            UpgradeDB,
            "Upgrade your JupyterHub state database to the current version.",
        ),
    }

    classes = List()

    @default('classes')
    def _load_classes(self):
        classes = {Spawner, Authenticator, CryptKeeper}
        for name, trait in self.traits(config=True).items():
            # load entry point groups into configurable class list
            # so that they show up in config files, etc.
            if isinstance(trait, EntryPointType):
                for key, entry_point in trait.load_entry_points().items():
                    try:
                        cls = entry_point.load()
                    except Exception as e:
                        self.log.debug(
                            "Failed to load %s entrypoint %r: %r",
                            trait.entry_point_group,
                            key,
                            e,
                        )
                        continue
                    if issubclass(cls, Configurable):
                        classes.add(cls)
        return list(classes)

    load_groups = Dict(
        Union([Dict(), List()]),
        help="""
        Dict of `{'group': {'users':['usernames'], 'properties': {}}`  to load at startup.

        Example::

            c.JupyterHub.load_groups = {
                'groupname': {
                    'users': ['usernames'],
                    'properties': {'key': 'value'},
                },
            }

        This strictly *adds* groups and users to groups.
        Properties, if defined, replace all existing properties.

        Loading one set of groups, then starting JupyterHub again with a different
        set will not remove users or groups from previous launches.
        That must be done through the API.

        .. versionchanged:: 3.2
          Changed format of group from list of usernames to dict
        """,
    ).tag(config=True)

    load_roles = List(
        Dict(),
        help="""List of predefined role dictionaries to load at startup.

        For instance::

            load_roles = [
                            {
                                'name': 'teacher',
                                'description': 'Access to users' information and group membership',
                                'scopes': ['users', 'groups'],
                                'users': ['cyclops', 'gandalf'],
                                'services': [],
                                'groups': []
                            }
                        ]

        All keys apart from 'name' are optional.
        See all the available scopes in the JupyterHub REST API documentation.

        Default roles are defined in roles.py.

        """,
    ).tag(config=True)

    custom_scopes = Dict(
        key_trait=Unicode(),
        value_trait=Dict(
            key_trait=Unicode(),
        ),
        help="""Custom scopes to define.

        For use when defining custom roles,
        to grant users granular permissions

        All custom scopes must have a description,
        and must start with the prefix `custom:`.

        For example::

            custom_scopes = {
                "custom:jupyter_server:read": {
                    "description": "read-only access to a single-user server",
                },
            }
        """,
    ).tag(config=True)

    config_file = Unicode('jupyterhub_config.py', help="The config file to load").tag(
        config=True
    )

    @validate("config_file")
    def _validate_config_file(self, proposal):
        if not self.generate_config and not os.path.isfile(proposal.value):
            print(
                f"ERROR: Failed to find specified config file: {proposal.value}",
                file=sys.stderr,
            )
            sys.exit(1)
        return proposal.value

    generate_config = Bool(False, help="Generate default config file").tag(config=True)
    generate_certs = Bool(False, help="Generate certs used for internal ssl").tag(
        config=True
    )
    answer_yes = Bool(
        False, help="Answer yes to any questions (e.g. confirm overwrite)"
    ).tag(config=True)
    pid_file = Unicode(
        '',
        help="""File to write PID
        Useful for daemonizing JupyterHub.
        """,
    ).tag(config=True)

    cookie_host_prefix_enabled = Bool(
        False,
        help="""Enable `__Host-` prefix on authentication cookies.
        
        The `__Host-` prefix on JupyterHub cookies provides further
        protection against cookie tossing when untrusted servers
        may control subdomains of your jupyterhub deployment.
        
        _However_, it also requires that cookies be set on the path `/`,
        which means they are shared by all JupyterHub components,
        so a compromised server component will have access to _all_ JupyterHub-related
        cookies of the visiting browser.
        It is recommended to only combine `__Host-` cookies with per-user domains.

        .. versionadded:: 4.1
        """,
    ).tag(config=True)

    cookie_max_age_days = Float(
        14,
        help="""Number of days for a login cookie to be valid.
        Default is two weeks.
        """,
    ).tag(config=True)

    oauth_token_expires_in = Integer(
        help="""Expiry (in seconds) of OAuth access tokens.

        The default is to expire when the cookie storing them expires,
        according to `cookie_max_age_days` config.

        These are the tokens stored in cookies when you visit
        a single-user server or service.
        When they expire, you must re-authenticate with the Hub,
        even if your Hub authentication is still valid.
        If your Hub authentication is valid,
        logging in may be a transparent redirect as you refresh the page.

        This does not affect JupyterHub API tokens in general,
        which do not expire by default.
        Only tokens issued during the oauth flow
        accessing services and single-user servers are affected.

        .. versionadded:: 1.4
            OAuth token expires_in was not previously configurable.
        .. versionchanged:: 1.4
            Default now uses cookie_max_age_days so that oauth tokens
            which are generally stored in cookies,
            expire when the cookies storing them expire.
            Previously, it was one hour.
        """,
        config=True,
    )

    @default("oauth_token_expires_in")
    def _cookie_max_age_seconds(self):
        """default to cookie max age, where these tokens are stored"""
        # convert cookie max age days to seconds
        return int(self.cookie_max_age_days * 24 * 3600)

    token_expires_in_max_seconds = Integer(
        0,
        config=True,
        help="""
        Set the maximum expiration (in seconds) of tokens created via the API.

        Set to any positive value to disallow creation of tokens with no expiration.

        0 (default) = no limit.
        
        Does not affect:
        
        - Server API tokens ($JUPYTERHUB_API_TOKEN is tied to lifetime of the server)
        - Tokens issued during oauth (use `oauth_token_expires_in`)
        - Tokens created via the API before configuring this limit
        
        .. versionadded:: 5.1
        """,
    )

    redirect_to_server = Bool(
        True, help="Redirect user to server (if running), instead of control panel."
    ).tag(config=True)
    activity_resolution = Integer(
        30,
        help="""
        Resolution (in seconds) for updating activity

        If activity is registered that is less than activity_resolution seconds
        more recent than the current value,
        the new value will be ignored.

        This avoids too many writes to the Hub database.
        """,
    ).tag(config=True)
    last_activity_interval = Integer(
        300, help="Interval (in seconds) at which to update last-activity timestamps."
    ).tag(config=True)
    proxy_check_interval = Integer(
        5,
        help="DEPRECATED since version 0.8: Use ConfigurableHTTPProxy.check_running_interval",
    ).tag(config=True)
    service_check_interval = Integer(
        60,
        help="Interval (in seconds) at which to check connectivity of services with web endpoints.",
    ).tag(config=True)
    active_user_window = Integer(
        30 * 60, help="Duration (in seconds) to determine the number of active users."
    ).tag(config=True)

    data_files_path = Unicode(
        DATA_FILES_PATH,
        help="The location of jupyterhub data files (e.g. /usr/local/share/jupyterhub)",
    ).tag(config=True)

    template_paths = List(
        help="Paths to search for jinja templates, before using the default templates."
    ).tag(config=True)

    @default('template_paths')
    def _template_paths_default(self):
        return [os.path.join(self.data_files_path, 'templates')]

    template_vars = Dict(
        help="""Extra variables to be passed into jinja templates.

        Values in dict may contain callable objects.
        If value is callable, the current user is passed as argument.

        Example::

            def callable_value(user):
                # user is generated by handlers.base.get_current_user
                with open("/tmp/file.txt", "r") as f:
                    ret = f.read()
                ret = ret.replace("<username>", user.name)
                return ret

            c.JupyterHub.template_vars = {
                "key1": "value1",
                "key2": callable_value,
            }
        """,
    ).tag(config=True)

    confirm_no_ssl = Bool(False, help="""DEPRECATED: does nothing""").tag(config=True)
    ssl_key = Unicode(
        '',
        help="""Path to SSL key file for the public facing interface of the proxy

        When setting this, you should also set ssl_cert
        """,
    ).tag(config=True)
    ssl_cert = Unicode(
        '',
        help="""Path to SSL certificate file for the public facing interface of the proxy

        When setting this, you should also set ssl_key
        """,
    ).tag(config=True)
    internal_ssl = Bool(
        False,
        help="""Enable SSL for all internal communication

        This enables end-to-end encryption between all JupyterHub components.
        JupyterHub will automatically create the necessary certificate
        authority and sign notebook certificates as they're created.
        """,
    ).tag(config=True)
    internal_certs_location = Unicode(
        'internal-ssl',
        help="""The location to store certificates automatically created by
        JupyterHub.

        Use with internal_ssl
        """,
    ).tag(config=True)
    recreate_internal_certs = Bool(
        False,
        help="""Recreate all certificates used within JupyterHub on restart.

        Note: enabling this feature requires restarting all notebook servers.

        Use with internal_ssl
        """,
    ).tag(config=True)
    external_ssl_authorities = Dict(
        help="""Dict authority:dict(files). Specify the key, cert, and/or
        ca file for an authority. This is useful for externally managed
        proxies that wish to use internal_ssl.

        The files dict has this format (you must specify at least a cert)::

            {
                'key': '/path/to/key.key',
                'cert': '/path/to/cert.crt',
                'ca': '/path/to/ca.crt'
            }

        The authorities you can override: 'hub-ca', 'notebooks-ca',
        'proxy-api-ca', 'proxy-client-ca', and 'services-ca'.

        Use with internal_ssl
        """
    ).tag(config=True)
    internal_ssl_authorities = Dict(
        default_value={
            'hub-ca': None,
            'notebooks-ca': None,
            'proxy-api-ca': None,
            'proxy-client-ca': None,
            'services-ca': None,
        },
        help="""Dict authority:dict(files). When creating the various
        CAs needed for internal_ssl, these are the names that will be used
        for each authority.

        Use with internal_ssl
        """,
    )
    internal_ssl_components_trust = Dict(
        help="""Dict component:list(components). This dict specifies the
        relationships of components secured by internal_ssl.
        """
    )
    internal_trust_bundles = Dict(
        help="""Dict component:path. These are the paths to the trust bundles
        that each component should have. They will be set during
        `init_internal_ssl`.

        Use with internal_ssl
        """
    )
    internal_ssl_key = Unicode(help="""The key to be used for internal ssl""")
    internal_ssl_cert = Unicode(help="""The cert to be used for internal ssl""")
    internal_ssl_ca = Unicode(
        help="""The certificate authority to be used for internal ssl"""
    )
    internal_proxy_certs = Dict(
        help=""" Dict component:dict(cert files). This dict contains the certs
        generated for both the proxy API and proxy client.
        """
    )
    trusted_alt_names = List(
        Unicode(),
        help="""Names to include in the subject alternative name.

        These names will be used for server name verification. This is useful
        if JupyterHub is being run behind a reverse proxy or services using ssl
        are on different hosts.

        Use with internal_ssl
        """,
    ).tag(config=True)

    trusted_downstream_ips = List(
        Unicode(),
        help="""Downstream proxy IP addresses to trust.

        This sets the list of IP addresses that are trusted and skipped when processing
        the `X-Forwarded-For` header. For example, if an external proxy is used for TLS
        termination, its IP address should be added to this list to ensure the correct
        client IP addresses are recorded in the logs instead of the proxy server's IP
        address.
        """,
    ).tag(config=True)

    ip = Unicode(
        '',
        help="""The public facing ip of the whole JupyterHub application
        (specifically referred to as the proxy).

        This is the address on which the proxy will listen. The default is to
        listen on all interfaces. This is the only address through which JupyterHub
        should be accessed by users.
        """,
    ).tag(config=True)

    port = Integer(
        8000,
        help="""The public facing port of the proxy.

        This is the port on which the proxy will listen.
        This is the only port through which JupyterHub
        should be accessed by users.
        """,
    ).tag(config=True)

    base_url = URLPrefix(
        '/',
        help="""The base URL of the entire application.

        Add this to the beginning of all JupyterHub URLs.
        Use base_url to run JupyterHub within an existing website.
        """,
    ).tag(config=True)

    @default('base_url')
    def _default_base_url(self):
        # call validate to ensure leading/trailing slashes
        return JupyterHub.base_url.validate(self, urlparse(self.bind_url).path)

    @observe('ip', 'port', 'base_url')
    def _url_part_changed(self, change):
        """propagate deprecated ip/port/base_url config to the bind_url"""
        urlinfo = urlparse(self.bind_url)
        if ':' in self.ip:
            fmt = '[%s]:%i'
        else:
            fmt = '%s:%i'
        urlinfo = urlinfo._replace(netloc=fmt % (self.ip, self.port))
        urlinfo = urlinfo._replace(path=self.base_url)
        bind_url = urlunparse(urlinfo)

        # Warn if both bind_url and ip/port/base_url are set
        if bind_url != self.bind_url:
            if self.bind_url != self._bind_url_default():
                self.log.warning(
                    "Both bind_url and ip/port/base_url have been configured. "
                    " please use just one or the other."
                )
            self.bind_url = bind_url

    bind_url = Unicode(
        "http://:8000",
        help="""The public facing URL of the whole JupyterHub application.

        This is the address on which the proxy will bind.
        Sets protocol, ip, base_url
        """,
    ).tag(config=True)

    @validate('bind_url')
    def _validate_bind_url(self, proposal):
        """ensure protocol field of bind_url matches ssl"""
        v = proposal['value']
        proto, sep, rest = v.partition('://')
        if self.ssl_cert and proto != 'https':
            return 'https' + sep + rest
        elif proto != 'http' and not self.ssl_cert:
            return 'http' + sep + rest
        return v

    @default('bind_url')
    def _bind_url_default(self):
        proto = 'https' if self.ssl_cert else 'http'
        return proto + '://:8000'

    public_url = Unicode(
        "",
        config=True,
        help="""Set the public URL of JupyterHub

        This will skip any detection of URL and protocol from requests,
        which isn't always correct when JupyterHub is behind
        multiple layers of proxies, etc.
        Usually the failure is detecting http when it's really https.

        Should include the full, public URL of JupyterHub,
        including the public-facing base_url prefix
        (i.e. it should include a trailing slash), e.g.
        https://jupyterhub.example.org/prefix/
        """,
    )

    @default("public_url")
    def _default_public_url(self):
        if self.subdomain_host:
            # if subdomain_host is specified, use it by default
            return self.subdomain_host + self.base_url
        else:
            return ""

    @validate("public_url")
    def _validate_public_url(self, proposal):
        url = proposal.value
        if not url:
            # explicitly empty (default)
            return url
        if not url.endswith("/"):
            # ensure we have a trailing slash
            # for consistency with base_url
            url = url + "/"
        if not url.endswith(self.base_url):
            if not urlparse(url).path.strip("/"):
                # no path specified, add base_url and warn
                url = url.rstrip("/") + self.base_url
                self.log.warning(
                    f"Adding missing base_url {self.base_url!r} to JupyterHub.public_url = {url!r}"
                )
            else:
                # path specified but it doesn't match, raise
                raise ValueError(
                    f"JupyterHub.public_url = {url!r} must include base_url: {self.base_url!r}"
                )
        if "://" not in url:
            # https by default; should be specified
            url = 'https://' + url
            self.log.warning(
                f"Adding missing protocol 'https://' to JupyterHub.public_url = {url!r}"
            )
        return url

    subdomain_host = Unicode(
        '',
        help="""Run single-user servers on subdomains of this host.

        This should be the full `https://hub.domain.tld[:port]`.

        Provides additional cross-site protections for javascript served by single-user servers.

        Requires `<username>.hub.domain.tld` to resolve to the same host as `hub.domain.tld`.

        In general, this is most easily achieved with wildcard DNS.

        When using SSL (i.e. always) this also requires a wildcard SSL certificate.
        """,
    ).tag(config=True)

    @validate("subdomain_host")
    def _validate_subdomain_host(self, proposal):
        new = proposal.value
        if new and '://' not in new:
            # host should include '://'
            # if not specified, assume https: You have to be really explicit about HTTP!
            new = 'https://' + new
            self.log.warning(
                f"Adding missing protocol 'https://' to JupyterHub.subdomain_host = {new!r}"
            )
        return new

    domain = Unicode(help="domain name, e.g. 'example.com' (excludes protocol, port)")

    @default('domain')
    def _domain_default(self):
        if not (self.public_url or self.subdomain_host):
            return ''
        return urlparse(self.public_url or self.subdomain_host).hostname

    subdomain_hook = Union(
        [Callable(), Unicode()],
        default_value="idna",
        config=True,
        help="""
        Hook for constructing subdomains for users and services.
        Only used when `JupyterHub.subdomain_host` is set.

        There are two predefined hooks, which can be selected by name:

        - 'legacy' (deprecated)
        - 'idna' (default, more robust. No change for _most_ usernames)

        Otherwise, should be a function which must not be async.
        A custom subdomain_hook should have the signature:

        def subdomain_hook(name, domain, kind) -> str:
            ...

        and should return a unique, valid domain name for all usernames.

        - `name` is the original name, which may need escaping to be safe as a domain name label
        - `domain` is the domain of the Hub itself
        - `kind` will be one of 'user' or 'service'

        JupyterHub itself puts very little limit on usernames
        to accommodate a wide variety of Authenticators,
        but your identity provider is likely much more strict,
        allowing you to make assumptions about the name.

        The 'idna' hook should produce a valid domain name for any user,
        using IDNA encoding for unicode usernames, and a truncate-and-hash approach for
        any usernames that can't be easily encoded into a domain component.

        .. versionadded:: 5.0
        """,
    )

    @default("subdomain_hook")
    def _default_subdomain_hook(self):
        return subdomain_hook_idna

    @validate("subdomain_hook")
    def _subdomain_hook(self, proposal):
        # shortcut `subdomain_hook = "idna"` config
        hook = proposal.value
        if hook == "idna":
            return subdomain_hook_idna
        if hook == "legacy":
            if self.subdomain_host:
                self.log.warning(
                    "Using deprecated 'legacy' subdomain hook. JupyterHub.subdomain_hook = 'idna' is the new default, added in JupyterHub 5."
                )
            return subdomain_hook_legacy
        if not callable(hook):
            raise ValueError(
                f"subdomain_hook must be 'idna', 'legacy', or a callable, got {hook!r}"
            )
        return hook

    logo_file = Unicode(
        '',
        help="Specify path to a logo image to override the Jupyter logo in the banner.",
    ).tag(config=True)

    @default('logo_file')
    def _logo_file_default(self):
        return os.path.join(
            self.data_files_path, 'static', 'images', 'jupyterhub-80.png'
        )

    jinja_environment_options = Dict(
        help="Supply extra arguments that will be passed to Jinja environment."
    ).tag(config=True)

    proxy_class = EntryPointType(
        default_value=ConfigurableHTTPProxy,
        klass=Proxy,
        entry_point_group="jupyterhub.proxies",
        help="""The class to use for configuring the JupyterHub proxy.

        Should be a subclass of :class:`jupyterhub.proxy.Proxy`.

        .. versionchanged:: 1.0
            proxies may be registered via entry points,
            e.g. `c.JupyterHub.proxy_class = 'traefik'`
        """,
    ).tag(config=True)

    proxy_cmd = Command(
        [],
        config=True,
        help="DEPRECATED since version 0.8. Use ConfigurableHTTPProxy.command",
    ).tag(config=True)

    debug_proxy = Bool(
        False, help="DEPRECATED since version 0.8: Use ConfigurableHTTPProxy.debug"
    ).tag(config=True)
    proxy_auth_token = Unicode(
        help="DEPRECATED since version 0.8: Use ConfigurableHTTPProxy.auth_token"
    ).tag(config=True)

    _proxy_config_map = {
        'proxy_check_interval': 'check_running_interval',
        'proxy_cmd': 'command',
        'debug_proxy': 'debug',
        'proxy_auth_token': 'auth_token',
    }

    @observe(*_proxy_config_map)
    def _deprecated_proxy_config(self, change):
        dest = self._proxy_config_map[change.name]
        self.log.warning(
            "JupyterHub.%s is deprecated in JupyterHub 0.8, use ConfigurableHTTPProxy.%s",
            change.name,
            dest,
        )
        self.config.ConfigurableHTTPProxy[dest] = change.new

    proxy_api_ip = Unicode(
        help="DEPRECATED since version 0.8 : Use ConfigurableHTTPProxy.api_url"
    ).tag(config=True)
    proxy_api_port = Integer(
        help="DEPRECATED since version 0.8 : Use ConfigurableHTTPProxy.api_url"
    ).tag(config=True)

    @observe('proxy_api_port', 'proxy_api_ip')
    def _deprecated_proxy_api(self, change):
        self.log.warning(
            "JupyterHub.%s is deprecated in JupyterHub 0.8, use ConfigurableHTTPProxy.api_url",
            change.name,
        )
        self.config.ConfigurableHTTPProxy.api_url = 'http://{}:{}'.format(
            self.proxy_api_ip or '127.0.0.1', self.proxy_api_port or self.port + 1
        )

    forwarded_host_header = Unicode(
        '',
        help="""Alternate header to use as the Host (e.g., X-Forwarded-Host)
        when determining whether a request is cross-origin

        This may be useful when JupyterHub is running behind a proxy that rewrites
        the Host header.
        """,
    ).tag(config=True)

    hub_port = Integer(
        8081,
        help="""The internal port for the Hub process.

        This is the internal port of the hub itself. It should never be accessed directly.
        See JupyterHub.port for the public port to use when accessing jupyterhub.
        It is rare that this port should be set except in cases of port conflict.

        See also `hub_ip` for the ip and `hub_bind_url` for setting the full bind URL.
        """,
    ).tag(config=True)

    hub_ip = Unicode(
        '127.0.0.1',
        help="""The ip address for the Hub process to *bind* to.

        By default, the hub listens on localhost only. This address must be accessible from
        the proxy and user servers. You may need to set this to a public ip or '' for all
        interfaces if the proxy or user servers are in containers or on a different host.

        See `hub_connect_ip` for cases where the bind and connect address should differ,
        or `hub_bind_url` for setting the full bind URL.
        """,
    ).tag(config=True)

    hub_connect_ip = Unicode(
        '',
        help="""The ip or hostname for proxies and spawners to use
        for connecting to the Hub.

        Use when the bind address (`hub_ip`) is 0.0.0.0, :: or otherwise different
        from the connect address.

        Default: when `hub_ip` is 0.0.0.0 or ::, use `socket.gethostname()`, otherwise use `hub_ip`.

        Note: Some spawners or proxy implementations might not support hostnames. Check your
        spawner or proxy documentation to see if they have extra requirements.

        .. versionadded:: 0.8
        """,
    ).tag(config=True)

    hub_connect_url = Unicode(
        help="""
        The URL for connecting to the Hub.
        Spawners, services, and the proxy will use this URL
        to talk to the Hub.

        Only needs to be specified if the default hub URL is not
        connectable (e.g. using a unix+http:// bind url).

        .. seealso::
            JupyterHub.hub_connect_ip
            JupyterHub.hub_bind_url

        .. versionadded:: 0.9
        """,
        config=True,
    )

    hub_bind_url = Unicode(
        help="""
        The URL on which the Hub will listen.
        This is a private URL for internal communication.
        Typically set in combination with hub_connect_url.
        If a unix socket, hub_connect_url **must** also be set.

        For example:

            "http://127.0.0.1:8081"
            "unix+http://%2Fsrv%2Fjupyterhub%2Fjupyterhub.sock"

        .. versionadded:: 0.9
        """,
        config=True,
    )

    hub_connect_port = Integer(
        0,
        help="""
        DEPRECATED

        Use hub_connect_url

        .. versionadded:: 0.8

        .. deprecated:: 0.9
            Use hub_connect_url
        """,
    ).tag(config=True)

    hub_prefix = URLPrefix(
        '/hub/', help="The prefix for the hub server.  Always /base_url/hub/"
    )

    @default('hub_prefix')
    def _hub_prefix_default(self):
        return url_path_join(self.base_url, '/hub/')

    hub_routespec = Unicode(
        "/",
        help="""
        The routing prefix for the Hub itself.

        Override to send only a subset of traffic to the Hub.
        Default is to use the Hub as the default route for all requests.

        This is necessary for normal jupyterhub operation,
        as the Hub must receive requests for e.g. `/user/:name`
        when the user's server is not running.

        However, some deployments using only the JupyterHub API
        may want to handle these events themselves,
        in which case they can register their own default target with the proxy
        and set e.g. `hub_routespec = /hub/` to serve only the hub's own pages, or even `/hub/api/` for api-only operation.

        Note: hub_routespec must include the base_url, if any.

        .. versionadded:: 1.4
        """,
    ).tag(config=True)

    @default("hub_routespec")
    def _default_hub_routespec(self):
        # Default routespec for the Hub is the *app* base url
        # not the hub URL, so the Hub receives requests for non-running servers
        # use `/` with host-based routing so the Hub
        # gets requests for all hosts
        if self.subdomain_host:
            routespec = '/'
        else:
            routespec = self.base_url
        return routespec

    @validate("hub_routespec")
    def _validate_hub_routespec(self, proposal):
        """ensure leading/trailing / on custom routespec prefix

        - trailing '/' always required
        - leading '/' required unless using subdomains
        """
        routespec = proposal.value
        if not routespec.endswith("/"):
            routespec = routespec + "/"
        if not self.subdomain_host and not routespec.startswith("/"):
            routespec = "/" + routespec
        return routespec

    @observe("hub_routespec")
    def _hub_routespec_changed(self, change):
        if change.new == change.old:
            return
        routespec = change.new
        if routespec not in {'/', self.base_url}:
            self.log.warning(
                f"Using custom route for Hub: {routespec}."
                " Requests for not-running servers may not be handled."
            )

    @observe('base_url')
    def _update_hub_prefix(self, change):
        """add base URL to hub prefix"""
        self.hub_prefix = self._hub_prefix_default()

    trust_user_provided_tokens = Bool(
        False,
        help="""Trust user-provided tokens (via JupyterHub.service_tokens)
        to have good entropy.

        If you are not inserting additional tokens via configuration file,
        this flag has no effect.

        In JupyterHub 0.8, internally generated tokens do not
        pass through additional hashing because the hashing is costly
        and does not increase the entropy of already-good UUIDs.

        User-provided tokens, on the other hand, are not trusted to have good entropy by default,
        and are passed through many rounds of hashing to stretch the entropy of the key
        (i.e. user-provided tokens are treated as passwords instead of random keys).
        These keys are more costly to check.

        If your inserted tokens are generated by a good-quality mechanism,
        e.g. `openssl rand -hex 32`, then you can set this flag to True
        to reduce the cost of checking authentication tokens.
        """,
    ).tag(config=True)
    cookie_secret = Union(
        [Bytes(), Unicode()],
        help="""The cookie secret to use to encrypt cookies.

        Loaded from the JPY_COOKIE_SECRET env variable by default.

        Should be exactly 256 bits (32 bytes).
        """,
    ).tag(config=True, env='JPY_COOKIE_SECRET')

    @validate('cookie_secret')
    def _validate_secret_key(self, proposal):
        """Coerces strings with even number of hexadecimal characters to bytes."""
        r = proposal['value']
        if isinstance(r, str):
            try:
                return bytes.fromhex(r)
            except ValueError:
                raise ValueError(
                    "cookie_secret set as a string must contain an even amount of hexadecimal characters."
                )
        else:
            return r

    @observe('cookie_secret')
    def _cookie_secret_check(self, change):
        secret = change.new
        if len(secret) > COOKIE_SECRET_BYTES:
            self.log.warning(
                "Cookie secret is %i bytes.  It should be %i.",
                len(secret),
                COOKIE_SECRET_BYTES,
            )

    cookie_secret_file = Unicode(
        'jupyterhub_cookie_secret', help="""File in which to store the cookie secret."""
    ).tag(config=True)

    api_tokens = Dict(
        Unicode(),
        help="""PENDING DEPRECATION: consider using services

        Dict of token:username to be loaded into the database.

        Allows ahead-of-time generation of API tokens for use by externally managed services,
        which authenticate as JupyterHub users.

        Consider using services for general services that talk to the JupyterHub API.
        """,
    ).tag(config=True)

    api_page_default_limit = Integer(
        50,
        help="The default amount of records returned by a paginated endpoint",
    ).tag(config=True)

    api_page_max_limit = Integer(
        200, help="The maximum amount of records that can be returned at once"
    ).tag(config=True)

    authenticate_prometheus = Bool(
        True, help="Authentication for prometheus metrics"
    ).tag(config=True)

    @observe('api_tokens')
    def _deprecate_api_tokens(self, change):
        self.log.warning(
            "JupyterHub.api_tokens is pending deprecation"
            " since JupyterHub version 0.8."
            "  Consider using JupyterHub.service_tokens."
            "  If you have a use case for services that identify as users,"
            " let us know: https://github.com/jupyterhub/jupyterhub/issues"
        )

    service_tokens = Dict(
        Unicode(),
        help="""Dict of token:servicename to be loaded into the database.

        Allows ahead-of-time generation of API tokens for use by externally managed services.
        """,
    ).tag(config=True)

    services = List(
        Dict(),
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
                    'api_token': 'super-secret',
                    'environment':
                }
            ]
        """,
    ).tag(config=True)
    _service_map = Dict()

    authenticator_class = EntryPointType(
        default_value=PAMAuthenticator,
        klass=Authenticator,
        entry_point_group="jupyterhub.authenticators",
        help="""Class for authenticating users.

        This should be a subclass of :class:`jupyterhub.auth.Authenticator`

        with an :meth:`authenticate` method that:

        - is a coroutine (asyncio or tornado)
        - returns username on success, None on failure
        - takes two arguments: (handler, data),
          where `handler` is the calling web.RequestHandler,
          and `data` is the POST form data from the login page.

        .. versionchanged:: 1.0
            authenticators may be registered via entry points,
            e.g. `c.JupyterHub.authenticator_class = 'pam'`
        """,
    ).tag(config=True)

    authenticator = Instance(Authenticator)

    @default('authenticator')
    def _authenticator_default(self):
        return self.authenticator_class(parent=self, _deprecated_db_session=self.db)

    implicit_spawn_seconds = Float(
        0,
        help="""Trigger implicit spawns after this many seconds.

        When a user visits a URL for a server that's not running,
        they are shown a page indicating that the requested server
        is not running with a button to spawn the server.

        Setting this to a positive value will redirect the user
        after this many seconds, effectively clicking this button
        automatically for the users,
        automatically beginning the spawn process.

        Warning: this can result in errors and surprising behavior
        when sharing access URLs to actual servers,
        since the wrong server is likely to be started.
        """,
    ).tag(config=True)

    allow_named_servers = Bool(
        False, help="Allow named single-user servers per user"
    ).tag(config=True)

    named_server_limit_per_user = Union(
        [Integer(), Callable()],
        default_value=0,
        help="""
        Maximum number of concurrent named servers that can be created by a user at a time.

        Setting this can limit the total resources a user can consume.

        If set to 0, no limit is enforced.

        Can be an integer or a callable/awaitable based on the handler object:

        ::

            def named_server_limit_per_user_fn(handler):
                user = handler.current_user
                if user and user.admin:
                    return 0
                return 5

            c.JupyterHub.named_server_limit_per_user = named_server_limit_per_user_fn
        """,
    ).tag(config=True)

    default_server_name = Unicode(
        "",
        help="""
        If named servers are enabled, default name of server to spawn or open
        when no server is specified, e.g. by user-redirect.

        Note: This has no effect if named servers are not enabled,
        and does _not_ change the existence or behavior of the default server named `''` (the empty string).
        This only affects which named server is launched when no server is specified,
        e.g. by links to `/hub/user-redirect/lab/tree/mynotebook.ipynb`.
        """,
    ).tag(config=True)
    # Ensure that default_server_name doesn't do anything if named servers aren't allowed
    _default_server_name = Unicode(
        help="Non-configurable version exposed to JupyterHub."
    )

    @default('_default_server_name')
    def _set_default_server_name(self):
        if self.allow_named_servers:
            return self.default_server_name
        else:
            if self.default_server_name:
                self.log.warning(
                    f"Ignoring `JupyterHub.default_server_name = {self.default_server_name!r}` config"
                    " without `JupyterHub.allow_named_servers = True`."
                )
            return ""

    # class for spawning single-user servers
    spawner_class = EntryPointType(
        default_value=LocalProcessSpawner,
        klass=Spawner,
        entry_point_group="jupyterhub.spawners",
        help="""The class to use for spawning single-user servers.

        Should be a subclass of :class:`jupyterhub.spawner.Spawner`.

        .. versionchanged:: 1.0
            spawners may be registered via entry points,
            e.g. `c.JupyterHub.spawner_class = 'localprocess'`
        """,
    ).tag(config=True)

    concurrent_spawn_limit = Integer(
        100,
        help="""
        Maximum number of concurrent users that can be spawning at a time.

        Spawning lots of servers at the same time can cause performance
        problems for the Hub or the underlying spawning system.
        Set this limit to prevent bursts of logins from attempting
        to spawn too many servers at the same time.

        This does not limit the number of total running servers.
        See active_server_limit for that.

        If more than this many users attempt to spawn at a time, their
        requests will be rejected with a 429 error asking them to try again.
        Users will have to wait for some of the spawning services
        to finish starting before they can start their own.

        If set to 0, no limit is enforced.
        """,
    ).tag(config=True)

    spawn_throttle_retry_range = Tuple(
        (30, 60),
        help="""
        (min seconds, max seconds) range to suggest a user wait before retrying.

        When `concurrent_spawn_limit` is exceeded, spawning is throttled.
        We suggest users wait random period of time within this range
        before retrying.

        A Retry-After header is set with a random value within this range.
        Error pages will display a rounded version of this value.

        The lower bound should ideally be approximately
        the median spawn time for your deployment.
        """,
    )

    active_server_limit = Integer(
        0,
        help="""
        Maximum number of concurrent servers that can be active at a time.

        Setting this can limit the total resources your users can consume.

        An active server is any server that's not fully stopped.
        It is considered active from the time it has been requested
        until the time that it has completely stopped.

        If this many user servers are active, users will not be able to
        launch new servers until a server is shutdown.
        Spawn requests will be rejected with a 429 error asking them to try again.

        If set to 0, no limit is enforced.
        """,
    ).tag(config=True)

    init_spawners_timeout = Integer(
        10,
        help="""
        Timeout (in seconds) to wait for spawners to initialize

        Checking if spawners are healthy can take a long time
        if many spawners are active at hub start time.

        If it takes longer than this timeout to check,
        init_spawner will be left to complete in the background
        and the http server is allowed to start.

        A timeout of -1 means wait forever,
        which can mean a slow startup of the Hub
        but ensures that the Hub is fully consistent by the time it starts responding to requests.
        This matches the behavior of jupyterhub 1.0.

        .. versionadded: 1.1.0

        """,
    ).tag(config=True)

    db_url = Unicode(
        'sqlite:///jupyterhub.sqlite',
        help="url for the database. e.g. `sqlite:///jupyterhub.sqlite`",
    ).tag(config=True)

    @observe('db_url')
    def _db_url_changed(self, change):
        new = change['new']
        if '://' not in new:
            # assume sqlite, if given as a plain filename
            self.db_url = f'sqlite:///{new}'

    db_kwargs = Dict(
        help="""Include any kwargs to pass to the database connection.
        See sqlalchemy.create_engine for details.
        """
    ).tag(config=True)

    upgrade_db = Bool(
        False,
        help="""Upgrade the database automatically on start.

        Only safe if database is regularly backed up.
        Only SQLite databases will be backed up to a local file automatically.
    """,
    ).tag(config=True)
    reset_db = Bool(False, help="Purge and reset the database.").tag(config=True)
    debug_db = Bool(
        False, help="log all database transactions. This has A LOT of output"
    ).tag(config=True)
    session_factory = Any()

    users = Instance(UserDict)

    @default('users')
    def _users_default(self):
        assert self.tornado_settings
        return UserDict(db_factory=lambda: self.db, settings=self.tornado_settings)

    admin_access = Bool(
        False,
        help="""DEPRECATED since version 2.0.0.

        The default admin role has full permissions, use custom RBAC scopes instead to
        create restricted administrator roles.
        https://jupyterhub.readthedocs.io/en/stable/rbac/index.html
        """,
    ).tag(config=True)

    admin_users = Set(
        help="""DEPRECATED since version 0.7.2, use Authenticator.admin_users instead."""
    ).tag(config=True)

    tornado_settings = Dict(
        help="Extra settings overrides to pass to the tornado application."
    ).tag(config=True)

    cleanup_servers = Bool(
        True,
        help="""Whether to shutdown single-user servers when the Hub shuts down.

        Disable if you want to be able to teardown the Hub while leaving the single-user servers running.

        If both this and cleanup_proxy are False, sending SIGINT to the Hub will
        only shutdown the Hub, leaving everything else running.

        The Hub should be able to resume from database state.
        """,
    ).tag(config=True)

    cleanup_proxy = Bool(
        True,
        help="""Whether to shutdown the proxy when the Hub shuts down.

        Disable if you want to be able to teardown the Hub while leaving the proxy running.

        Only valid if the proxy was starting by the Hub process.

        If both this and cleanup_servers are False, sending SIGINT to the Hub will
        only shutdown the Hub, leaving everything else running.

        The Hub should be able to resume from database state.
        """,
    ).tag(config=True)

    statsd_host = Unicode(
        help="Host to send statsd metrics to. An empty string (the default) disables sending metrics."
    ).tag(config=True)

    statsd_port = Integer(
        8125, help="Port on which to send statsd metrics about the hub"
    ).tag(config=True)

    statsd_prefix = Unicode(
        'jupyterhub', help="Prefix to use for all metrics sent by jupyterhub to statsd"
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
        help="""
        DEPRECATED: use output redirection instead, e.g.

        jupyterhub &>> /var/log/jupyterhub.log
        """
    ).tag(config=True)

    @observe('extra_log_file')
    def _log_file_changed(self, change):
        if change.new:
            self.log.warning(
                dedent(
                    f"""
                extra_log_file is DEPRECATED in jupyterhub-0.8.2.

                extra_log_file only redirects logs of the Hub itself,
                and will discard any other output, such as
                that of subprocess spawners or the proxy.

                It is STRONGLY recommended that you redirect process
                output instead, e.g.

                    jupyterhub &>> '{change.new}'
            """
                )
            )

    extra_log_handlers = List(
        Instance(logging.Handler), help="Extra log handlers to set on JupyterHub logger"
    ).tag(config=True)

    statsd = Any(
        allow_none=False,
        help="The statsd client, if any. A mock will be used if we aren't using statsd",
    )

    shutdown_on_logout = Bool(
        False, help="""Shuts down all user servers on logout"""
    ).tag(config=True)

    @default('statsd')
    def _statsd(self):
        if self.statsd_host:
            import statsd

            client = statsd.StatsClient(
                self.statsd_host, self.statsd_port, self.statsd_prefix
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
                logging.FileHandler(self.extra_log_file, encoding='utf8')
            )

        _formatter = self._log_formatter_cls(
            fmt=self.log_format, datefmt=self.log_datefmt
        )
        for handler in self.extra_log_handlers:
            if handler.formatter is None:
                handler.setFormatter(_formatter)
            self.log.addHandler(handler)

        # disable curl debug, which is TOO MUCH
        logging.getLogger('tornado.curl_httpclient').setLevel(
            max(self.log_level, logging.INFO)
        )

        for log in (app_log, access_log, gen_log):
            # ensure all log statements identify the application they come from
            log.name = self.log.name

        # hook up tornado's and oauthlib's loggers to our own
        for name in ("tornado", "oauthlib"):
            logger = logging.getLogger(name)
            logger.propagate = True
            logger.parent = self.log
            logger.setLevel(self.log.level)

    @staticmethod
    def add_url_prefix(prefix, handlers):
        """add a url prefix to handlers"""
        for i, tup in enumerate(handlers):
            lis = list(tup)
            if tup[0]:
                lis[0] = url_path_join(prefix, tup[0])
            else:
                # the '' route should match /prefix not /prefix/
                lis[0] = prefix.rstrip("/")
            handlers[i] = tuple(lis)
        return handlers

    extra_handlers = List(
        help="""
        DEPRECATED.

        If you need to register additional HTTP endpoints
        please use services instead.
        """
    ).tag(config=True)

    @observe("extra_handlers")
    def _extra_handlers_changed(self, change):
        if change.new:
            self.log.warning(
                "JupyterHub.extra_handlers is deprecated in JupyterHub 3.1."
                " Please use JupyterHub services to register additional HTTP endpoints."
            )

    default_url = Union(
        [Unicode(), Callable()],
        help="""
        The default URL for users when they arrive (e.g. when user directs to "/")

        By default, redirects users to their own server.

        Can be a Unicode string (e.g. '/hub/home') or a callable based on the handler object:

        ::

            def default_url_fn(handler):
                user = handler.current_user
                if user and user.admin:
                    return '/hub/admin'
                return '/hub/home'

            c.JupyterHub.default_url = default_url_fn
        """,
    ).tag(config=True)

    user_redirect_hook = Callable(
        None,
        allow_none=True,
        help="""
        Callable to affect behavior of /user-redirect/

        Receives 4 parameters:
        1. path - URL path that was provided after /user-redirect/
        2. request - A Tornado HTTPServerRequest representing the current request.
        3. user - The currently authenticated user.
        4. base_url - The base_url of the current hub, for relative redirects

        It should return the new URL to redirect to, or None to preserve
        current behavior.
        """,
    ).tag(config=True)

    use_legacy_stopped_server_status_code = Bool(
        False,
        help="""
        Return 503 rather than 424 when request comes in for a non-running server.

        Prior to JupyterHub 2.0, we returned a 503 when any request came in for
        a user server that was currently not running. By default, JupyterHub 2.0
        will return a 424 - this makes operational metric dashboards more useful.

        JupyterLab < 3.2 expected the 503 to know if the user server is no longer
        running, and prompted the user to start their server. Set this config to
        true to retain the old behavior, so JupyterLab < 3.2 can continue to show
        the appropriate UI when the user server is stopped.

        This option will be removed in a future release.
        """,
        config=True,
    )

    metrics_collector = Any()
    _periodic_callbacks = Dict()

    def init_handlers(self):
        h = []
        # load handlers from the authenticator
        h.extend(self.authenticator.get_handlers(self))
        # set default handlers
        h.extend(handlers.default_handlers)
        h.extend(apihandlers.default_handlers)

        # add any user configurable handlers.
        h.extend(self.extra_handlers)

        h.append((r'/logo', LogoHandler, {'path': self.logo_file}))
        h.append((r'/api/(.*)', apihandlers.base.API404))

        self.handlers = self.add_url_prefix(self.hub_prefix, h)
        # some extra handlers, outside hub_prefix
        self.handlers.extend(
            [
                # add trailing / to ``/user|services/:name`
                (
                    rf"{self.base_url}(user|services)/([^/]+)",
                    handlers.AddSlashHandler,
                ),
                (rf"(?!{self.hub_prefix}).*", handlers.PrefixRedirectHandler),
                (r'(.*)', handlers.Template404),
            ]
        )

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
        secret_file = os.path.abspath(os.path.expanduser(self.cookie_secret_file))
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
                if not _mswindows:  # Windows permissions don't follow POSIX rules
                    perm = os.stat(secret_file).st_mode
                    if perm & 0o07:
                        msg = "cookie_secret_file can be read or written by anybody"
                        raise ValueError(msg)
                with open(secret_file) as f:
                    text_secret = f.read().strip()
                if HEX_RE.match(text_secret):
                    # >= 0.8, use 32B hex
                    secret = binascii.a2b_hex(text_secret)
                else:
                    # old b64 secret with a bunch of ignored bytes
                    secret = binascii.a2b_base64(text_secret)
                    self.log.warning(
                        dedent(
                            """
                    Old base64 cookie-secret detected in {0}.

                    JupyterHub >= 0.8 expects 32B hex-encoded cookie secret
                    for tornado's sha256 cookie signing.

                    To generate a new secret:

                        openssl rand -hex 32 > "{0}"
                    """
                        ).format(secret_file)
                    )
            except Exception as e:
                self.log.error(
                    "Refusing to run JupyterHub with invalid cookie_secret_file. "
                    "%s error was: %s",
                    secret_file,
                    e,
                )
                self.exit(1)

        if not secret:
            secret_from = 'new'
            self.log.debug("Generating new %s", trait_name)
            secret = secrets.token_bytes(COOKIE_SECRET_BYTES)

        if secret_file and secret_from == 'new':
            # if we generated a new secret, store it in the secret_file
            self.log.info("Writing %s to %s", trait_name, secret_file)
            text_secret = binascii.b2a_hex(secret).decode('ascii')
            with open(secret_file, 'w') as f:
                f.write(text_secret)
                f.write('\n')
            if not _mswindows:  # Windows permissions don't follow POSIX rules
                try:
                    os.chmod(secret_file, 0o600)
                except OSError:
                    self.log.warning("Failed to set permissions on %s", secret_file)
        # store the loaded trait value
        self.cookie_secret = secret

    def init_internal_ssl(self):
        """Create the certs needed to turn on internal SSL."""

        if self.internal_ssl:
            from certipy import Certipy, CertNotFoundError

            certipy = Certipy(
                store_dir=self.internal_certs_location,
                remove_existing=self.recreate_internal_certs,
            )

            # Here we define how trust should be laid out per each component
            self.internal_ssl_components_trust = {
                'hub-ca': list(self.internal_ssl_authorities.keys()),
                'proxy-api-ca': ['hub-ca', 'services-ca', 'notebooks-ca'],
                'proxy-client-ca': ['hub-ca', 'notebooks-ca'],
                'notebooks-ca': ['hub-ca', 'proxy-client-ca'],
                'services-ca': ['hub-ca', 'proxy-api-ca'],
            }

            hub_name = 'hub-ca'

            # If any external CAs were specified in external_ssl_authorities
            # add records of them to Certipy's store.
            self.internal_ssl_authorities.update(self.external_ssl_authorities)
            for authority, files in self.internal_ssl_authorities.items():
                if files:
                    self.log.info("Adding CA for %s", authority)
                    certipy.store.add_record(
                        authority, is_ca=True, files=files, overwrite=True
                    )

            self.internal_trust_bundles = certipy.trust_from_graph(
                self.internal_ssl_components_trust
            )

            default_alt_names = [
                "IP:127.0.0.1",
                "IP:0:0:0:0:0:0:0:1",
                "DNS:localhost",
            ]
            if self.subdomain_host:
                default_alt_names.append(
                    f"DNS:{urlparse(self.subdomain_host).hostname}"
                )
            # The signed certs used by hub-internal components
            try:
                internal_key_pair = certipy.store.get_record("hub-internal")
            except CertNotFoundError:
                alt_names = list(default_alt_names)
                # In the event the hub needs to be accessed externally, add
                # the fqdn and (optionally) rev_proxy to the set of alt_names.
                alt_names += ["DNS:" + socket.getfqdn()] + self.trusted_alt_names
                self.log.info(
                    "Adding CA for %s: %s", "hub-internal", ";".join(alt_names)
                )
                internal_key_pair = certipy.create_signed_pair(
                    "hub-internal", hub_name, alt_names=alt_names
                )
            else:
                self.log.info("Using existing hub-internal CA")

            # Create the proxy certs
            proxy_api = 'proxy-api'
            proxy_client = 'proxy-client'
            for component in [proxy_api, proxy_client]:
                ca_name = component + '-ca'
                alt_names = default_alt_names + self.trusted_alt_names
                try:
                    record = certipy.store.get_record(component)
                except CertNotFoundError:
                    self.log.info(
                        "Generating signed pair for %s: %s",
                        component,
                        ';'.join(alt_names),
                    )
                    record = certipy.create_signed_pair(
                        component, ca_name, alt_names=alt_names
                    )
                else:
                    self.log.info("Using existing %s CA", component)

                self.internal_proxy_certs[component] = {
                    "keyfile": record['files']['key'],
                    "certfile": record['files']['cert'],
                    "cafile": record['files']['cert'],
                }

            self.internal_ssl_key = internal_key_pair['files']['key']
            self.internal_ssl_cert = internal_key_pair['files']['cert']
            self.internal_ssl_ca = self.internal_trust_bundles[hub_name]

            # Configure the AsyncHTTPClient. This will affect anything using
            # AsyncHTTPClient.
            # can't use ssl_options in case of pycurl
            AsyncHTTPClient.configure(
                AsyncHTTPClient.configured_class(),
                defaults=dict(
                    ca_certs=self.internal_ssl_ca,
                    client_key=self.internal_ssl_key,
                    client_cert=self.internal_ssl_cert,
                    validate_cert=True,
                ),
            )

    def init_db(self):
        """Create the database connection"""

        urlinfo = urlparse(self.db_url)
        if urlinfo.password:
            # avoid logging the database password
            urlinfo = urlinfo._replace(
                netloc=f'{urlinfo.username}:[redacted]@{urlinfo.hostname}:{urlinfo.port}'
            )
            db_log_url = urlinfo.geturl()
        else:
            db_log_url = self.db_url
        self.log.debug("Connecting to db: %s", db_log_url)
        if self.upgrade_db:
            dbutil.upgrade_if_needed(self.db_url, log=self.log)

        try:
            self.session_factory = orm.new_session_factory(
                self.db_url, reset=self.reset_db, echo=self.debug_db, **self.db_kwargs
            )
            self.db = self.session_factory()
        except OperationalError as e:
            self.log.error("Failed to connect to db: %s", db_log_url)
            self.log.debug("Database error was:", exc_info=True)
            if self.db_url.startswith('sqlite:///'):
                self._check_db_path(self.db_url.split(':///', 1)[1])
            self.log.critical(
                '\n'.join(
                    [
                        "If you recently upgraded JupyterHub, try running",
                        "    jupyterhub upgrade-db",
                        "to upgrade your JupyterHub database schema",
                    ]
                )
            )
            self.exit(1)
        except orm.DatabaseSchemaMismatch as e:
            self.exit(e)

        # ensure the default oauth client exists
        if (
            not self.db.query(orm.OAuthClient)
            .filter_by(identifier="jupyterhub")
            .one_or_none()
        ):
            # create the oauth client for jupyterhub itself
            # this allows us to distinguish between orphaned tokens
            # (failed cascade deletion) and tokens issued by the hub
            # it has no client_secret, which means it cannot be used
            # to make requests
            client = orm.OAuthClient(
                identifier="jupyterhub",
                secret="",
                redirect_uri="",
                description="JupyterHub",
            )
            self.db.add(client)
            self.db.commit()

    def init_hub(self):
        """Load the Hub URL config"""
        if self.public_url:
            # host = scheme://hostname:port (no path)
            public_host = urlunparse(urlparse(self.public_url)._replace(path=""))
        else:
            public_host = self.subdomain_host
        hub_args = dict(
            base_url=self.hub_prefix,
            routespec=self.hub_routespec,
            public_host=public_host,
            certfile=self.internal_ssl_cert,
            keyfile=self.internal_ssl_key,
            cafile=self.internal_ssl_ca,
        )
        if self.hub_bind_url:
            # ensure hub_prefix is set on bind_url
            self.hub_bind_url = urlunparse(
                urlparse(self.hub_bind_url)._replace(path=self.hub_prefix)
            )
            hub_args['bind_url'] = self.hub_bind_url
        else:
            hub_args['ip'] = self.hub_ip
            hub_args['port'] = self.hub_port

        self.hub = Hub(**hub_args)
        if self.cookie_host_prefix_enabled:
            self.hub.cookie_name = "__Host-" + self.hub.cookie_name

        if not self.subdomain_host:
            api_prefix = url_path_join(self.hub.base_url, "api/")
            if not api_prefix.startswith(self.hub.routespec):
                self.log.warning(
                    f"Hub API prefix {api_prefix} not on prefix {self.hub.routespec}. "
                    "The Hub may not receive any API requests from outside."
                )

        if self.hub_connect_ip:
            self.hub.connect_ip = self.hub_connect_ip
        if self.hub_connect_port:
            self.hub.connect_port = self.hub_connect_port
            self.log.warning(
                "JupyterHub.hub_connect_port is deprecated as of 0.9."
                " Use JupyterHub.hub_connect_url to fully specify"
                " the URL for connecting to the Hub."
            )

        if self.hub_connect_url:
            # ensure hub_prefix is on connect_url
            self.hub_connect_url = urlunparse(
                urlparse(self.hub_connect_url)._replace(path=self.hub_prefix)
            )
            self.hub.connect_url = self.hub_connect_url
        if self.internal_ssl:
            self.hub.proto = 'https'

    async def init_users(self):
        """Load users into and from the database"""
        db = self.db

        if self.authenticator.enable_auth_state:
            # check that auth_state encryption is available
            # if it's not, exit with an informative error.
            ck = crypto.CryptKeeper.instance()
            try:
                ck.check_available()
            except Exception as e:
                self.exit(
                    f"auth_state is enabled, but encryption is not available: {e}"
                )

        # give the authenticator a chance to check its own config
        self.authenticator.check_allow_config()

        if self.admin_users and not self.authenticator.admin_users:
            self.log.warning(
                "\nJupyterHub.admin_users is deprecated since version 0.7.2."
                "\nUse Authenticator.admin_users instead."
            )
            self.authenticator.admin_users = self.admin_users
        admin_users = [
            self.authenticator.normalize_username(name)
            for name in self.authenticator.admin_users
        ]
        self.authenticator.admin_users = set(admin_users)  # force normalization
        for username in admin_users:
            if not self.authenticator.validate_username(username):
                raise ValueError(f"username {username!r} is not valid")

        new_users = []

        for name in admin_users:
            # ensure anyone specified as admin in config is admin in db
            user = orm.User.find(db, name)
            if user is None:
                user = orm.User(name=name, admin=True)
                db.add(user)
                roles.assign_default_roles(self.db, entity=user)
                new_users.append(user)
            else:
                user.admin = True

        # the admin_users config variable will never be used after this point.
        # only the database values will be referenced.
        allowed_users = [
            self.authenticator.normalize_username(name)
            for name in self.authenticator.allowed_users
        ]
        self.authenticator.allowed_users = set(allowed_users)  # force normalization
        for username in allowed_users:
            if not self.authenticator.validate_username(username):
                raise ValueError(f"username {username!r} is not valid")

        if self.authenticator.allowed_users and self.authenticator.admin_users:
            # make sure admin users are in the allowed_users set, if defined,
            # otherwise they won't be able to login
            self.authenticator.allowed_users |= self.authenticator.admin_users

        # add allowed users to the db
        for name in allowed_users:
            user = orm.User.find(db, name)
            if user is None:
                user = orm.User(name=name)
                new_users.append(user)
                db.add(user)

        db.commit()

        # Notify authenticator of all users.
        # This ensures Authenticator.allowed_users is up-to-date with the database.
        # This lets .allowed_users be used to set up initial list,
        # but changes to the allowed_users set can occur in the database,
        # and persist across sessions.
        total_users = 0
        blocked_users = self.authenticator.blocked_users
        for user in db.query(orm.User):
            if user.name in blocked_users:
                # don't call add_user with blocked users
                continue
            try:
                f = self.authenticator.add_user(user)
                if f:
                    await maybe_future(f)
            except Exception:
                self.log.exception("Error adding user %s already in db", user.name)
                if self.authenticator.delete_invalid_users:
                    self.log.warning(
                        "Deleting invalid user %s from the Hub database", user.name
                    )
                    db.delete(user)
                else:
                    self.log.warning(
                        dedent(
                            """
                    You can set
                        c.Authenticator.delete_invalid_users = True
                    to automatically delete users from the Hub database that no longer pass
                    Authenticator validation,
                    such as when user accounts are deleted from the external system
                    without notifying JupyterHub.
                    """
                        )
                    )
            else:
                total_users += 1
                # handle database upgrades where user.created is undefined.
                # we don't want to allow user.created to be undefined,
                # so initialize it to last_activity (if defined) or now.
                if not user.created:
                    user.created = user.last_activity or utcnow(with_tz=False)
        db.commit()

        # The allowed_users set and the users in the db are now the same.
        # From this point on, any user changes should be done simultaneously
        # to the allowed_users set and user db, unless the allowed set is empty (all users allowed).

        TOTAL_USERS.set(total_users)

    async def _get_or_create_user(self, username, hint):
        """Create user if username is found in config but user does not exist"""
        user = orm.User.find(self.db, name=username)
        if user is None:
            if not self.authenticator.validate_username(username):
                raise ValueError(f"Username {username!r} is not valid")
            self.log.info(f"Creating user {username} found in {hint}")
            user = orm.User(name=username)
            self.db.add(user)
            roles.assign_default_roles(self.db, entity=user)
            self.db.commit()
            f = self.authenticator.add_user(user)
            if f:
                await maybe_future(f)
        return user

    async def init_blocked_users(self):
        """Revoke all permissions for users in Authenticator.blocked_users"""
        blocked_users = self.authenticator.blocked_users
        if not blocked_users:
            # nothing to check
            return
        db = self.db
        for user in db.query(orm.User).filter(orm.User.name.in_(blocked_users)):
            # revoke permissions from blocked users
            # so already-issued credentials have no access to the API
            self.log.debug(f"Found blocked user in database: {user.name}")
            if user.admin:
                self.log.warning(
                    f"Removing admin permissions from blocked user {user.name}"
                )
                user.admin = False
            if user.roles:
                self.log.warning(
                    f"Removing blocked user {user.name} from roles: {', '.join(role.name for role in user.roles)}"
                )
                user.roles = []
            if user.groups:
                self.log.warning(
                    f"Removing blocked user {user.name} from groups: {', '.join(group.name for group in user.groups)}"
                )
                user.groups = []

        db.commit()

    async def init_groups(self):
        """Load predefined groups into the database"""
        db = self.db

        if self.authenticator.manage_groups and self.load_groups:
            raise ValueError("Group management has been offloaded to the authenticator")

        for name, contents in self.load_groups.items():
            self.log.debug("Loading group %s", name)
            group = orm.Group.find(db, name)

            if group is None:
                self.log.info(f"Creating group {name}")
                group = orm.Group(name=name)
                db.add(group)
            if isinstance(contents, list):
                self.log.warning(
                    "group config `'groupname': [usernames]` config format is deprecated in JupyterHub 3.2,"
                    " use `'groupname': {'users': [usernames], ...}`"
                )
                contents = {"users": contents}
            if 'users' in contents:
                for username in contents['users']:
                    username = self.authenticator.normalize_username(username)
                    user = await self._get_or_create_user(
                        username, hint=f"group: {name}"
                    )
                    if group not in user.groups:
                        self.log.debug(f"Adding user {username} to group {name}")
                        group.users.append(user)

            if 'properties' in contents:
                group_properties = contents['properties']
                if group.properties != group_properties:
                    # add equality check to avoid no-op db transactions
                    self.log.debug(
                        f"Adding properties to group {name}: {group_properties}"
                    )
                    group.properties = group_properties

        db.commit()

    async def init_role_creation(self):
        """Load default and user-defined roles and scopes into the database"""
        if self.custom_scopes:
            self.log.info(f"Defining {len(self.custom_scopes)} custom scopes.")
            scopes.define_custom_scopes(self.custom_scopes)

        roles_to_load = self.load_roles[:]

        if self.authenticator.manage_roles and self.load_roles:
            offending_roles = []
            for role_spec in roles_to_load:
                user_role_assignments = role_spec.get('users', [])
                group_role_assignments = role_spec.get('groups', [])
                if user_role_assignments or group_role_assignments:
                    offending_roles.append(role_spec)
            if offending_roles:
                raise ValueError(
                    "When authenticator manages roles, `load_roles` can not"
                    " be used for assigning roles to users nor groups."
                    f" Offending roles: {offending_roles}"
                )

        if self.authenticator.manage_roles:
            managed_roles = await self.authenticator.load_managed_roles()
            for role in managed_roles:
                role['managed_by_auth'] = True
            roles_to_load.extend(managed_roles)

        self.log.debug('Loading roles into database')
        default_roles = roles.get_default_roles()
        config_role_names = [r['name'] for r in roles_to_load]

        default_roles_dict = {role["name"]: role for role in default_roles}
        init_roles = []
        roles_with_new_permissions = []
        for role_spec in roles_to_load:
            role_name = role_spec['name']
            self.log.debug("Loading role %s", role_name)
            if role_name in default_roles_dict:
                self.log.debug("Overriding default role %s", role_name)
                # merge custom role spec with default role spec when overriding
                # so the new role can be partially defined
                default_role_spec = default_roles_dict.pop(role_name)
                merged_role_spec = {}
                merged_role_spec.update(default_role_spec)
                merged_role_spec.update(role_spec)
                role_spec = merged_role_spec

            # Check for duplicates
            if config_role_names.count(role_name) > 1:
                raise ValueError(
                    f"Role {role_name} multiply defined. Please check the `load_roles` configuration"
                )
            init_roles.append(role_spec)
            # Check if some roles have obtained new permissions (to avoid 'scope creep')
            old_role = orm.Role.find(self.db, name=role_name)
            if old_role:
                if not set(role_spec.get('scopes', [])).issubset(old_role.scopes):
                    self.log.warning(f"Role {role_name} has obtained extra permissions")
                    roles_with_new_permissions.append(role_name)

        # make sure we load any default roles not overridden
        init_roles = list(default_roles_dict.values()) + init_roles

        if (
            self.db.query(orm.Role).first() is None
            and self.db.query(orm.User).first() is not None
        ):
            # apply rbac-upgrade default role assignment if there are users in the db,
            # but not any roles
            self._rbac_upgrade = True
        else:
            self._rbac_upgrade = False

        init_non_managed_role_names = [
            r['name'] for r in init_roles if not r.get('managed_by_auth', False)
        ]
        init_managed_role_names = [
            r['name'] for r in init_roles if r.get('managed_by_auth', False)
        ]

        # delete all roles that were defined by `load_roles()` config but are not longer there
        for role in self.db.query(orm.Role).filter(
            (orm.Role.managed_by_auth == False)
            & orm.Role.name.notin_(init_non_managed_role_names)
        ):
            self.log.warning(f"Deleting role {role.name}")
            self.db.delete(role)

        # delete all roles that were defined by authenticator but are not in `load_managed_roles()`
        if self.authenticator.reset_managed_roles_on_startup:
            deleted_stale_roles = (
                self.db.query(orm.Role)
                .filter(
                    (orm.Role.managed_by_auth == True)
                    & (orm.Role.name.notin_(init_managed_role_names))
                )
                .delete()
            )
            if deleted_stale_roles:
                self.log.info(
                    "Deleted %s stale roles previously added by an authenticator",
                    deleted_stale_roles,
                )

        for role in init_roles:
            roles.create_role(self.db, role, commit=False)

        self.db.commit()

    async def init_role_assignment(self):
        # tokens are added separately
        kinds = ['users', 'services', 'groups']
        admin_role_objects = ['users', 'services']
        config_admin_users = set(self.authenticator.admin_users)
        db = self.db
        # start by marking all role role assignments from authenticator as stale
        stale_managed_role_assignment = {}
        if self.authenticator.reset_managed_roles_on_startup:
            for kind in kinds:
                entity_name = kind[:-1]
                association_class = orm._role_associations[entity_name]
                stale_managed_role_assignment[kind] = set(
                    db.query(association_class)
                    .filter(association_class.managed_by_auth == True)
                    .all()
                )

        roles_to_load_assignments_from = self.load_roles[:]

        if self.authenticator.manage_roles:
            managed_roles = await self.authenticator.load_managed_roles()
            for role in managed_roles:
                role['managed_by_auth'] = True
            roles_to_load_assignments_from.extend(managed_roles)

        # load predefined roles from config file
        if config_admin_users:
            for role_spec in roles_to_load_assignments_from:
                if role_spec['name'] == 'admin':
                    self.log.warning(
                        "Configuration specifies both admin_users and users in the admin role specification. "
                        "If admin role is present in config, c.Authenticator.admin_users should not be used."
                    )
                    self.log.info(
                        "Merging admin_users set with users list in admin role"
                    )
                    role_spec['users'] = set(role_spec.get('users', []))
                    role_spec['users'] |= config_admin_users
        self.log.debug('Loading role assignments from config')
        has_admin_role_spec = {role_bearer: False for role_bearer in admin_role_objects}

        for role_spec in roles_to_load_assignments_from:
            role = orm.Role.find(db, name=role_spec['name'])
            role_name = role_spec["name"]
            if role_name == 'admin':
                for kind in admin_role_objects:
                    has_admin_role_spec[kind] = kind in role_spec
                    if has_admin_role_spec[kind]:
                        self.log.info(f"Admin role specifies static {kind} list")
                    else:
                        self.log.info(
                            f"Admin role does not specify {kind}, preserving admin membership in database"
                        )
            # add users, services, and/or groups,
            # tokens need to be checked for permissions
            for kind in kinds:
                orm_role_bearers = []
                if kind in role_spec:
                    for name in role_spec[kind]:
                        if kind == 'users':
                            name = self.authenticator.normalize_username(name)
                        Class = orm.get_class(kind)
                        orm_obj = Class.find(db, name)
                        if orm_obj is not None:
                            orm_role_bearers.append(orm_obj)
                        else:
                            if kind == 'users':
                                orm_obj = await self._get_or_create_user(
                                    name, hint=f"role: {role_name}"
                                )
                                orm_role_bearers.append(orm_obj)
                            elif kind == 'groups':
                                self.log.info(
                                    f"Creating group {name} found in role: {role_name}"
                                )
                                group = orm.Group(name=name)
                                db.add(group)
                                db.commit()
                                orm_role_bearers.append(group)
                            elif kind == "services":
                                raise ValueError(
                                    f"Found undefined service {name} in role {role_name}. Define it first in c.JupyterHub.services."
                                )
                            else:
                                # this can't happen now, but keep the `else` in case we introduce a problem
                                # in the declaration of `kinds` above
                                raise ValueError(f"Unhandled role member kind: {kind}")

                        # Ensure all with admin role have admin flag
                        if role_name == 'admin':
                            orm_obj.admin = True
                    # explicitly defined list
                    # ensure membership list is exact match (adds and revokes permissions)
                    setattr(role, kind, orm_role_bearers)
                    # if the role_spec was contributed by the authenticator, mark the newly
                    # created assignments as managed by authenticator too; also mark the
                    # assignment as not stale (in case if it was marked as such initially)
                    if role_spec.get('managed_by_auth', False):
                        entity_name = kind[:-1]
                        association_class = orm._role_associations[entity_name]
                        kind_id = getattr(association_class, f'{entity_name}_id')
                        associations = db.query(association_class).filter(
                            kind_id.in_([bearer.id for bearer in orm_role_bearers])
                            & (association_class.role_id == role.id)
                        )
                        for association in associations:
                            association.managed_by_auth = True
                            # this association is not stale
                            if association in stale_managed_role_assignment[kind]:
                                stale_managed_role_assignment[kind].remove(association)
                else:
                    # no defined members in `load_managed_roles()`
                    # leaving 'users' undefined should not remove existing managed role assignments
                    if kind == "users" and role_spec.get('managed_by_auth', False):
                        entity_name = kind[:-1]
                        association_class = orm._role_associations[entity_name]
                        kind_id = getattr(association_class, f'{entity_name}_id')
                        associations = db.query(association_class).filter(
                            association_class.role_id == role.id
                        )
                        for association in associations:
                            if association in stale_managed_role_assignment[kind]:
                                stale_managed_role_assignment[kind].remove(association)
                    # no defined members in `load_roles()`
                    # leaving 'users' undefined in overrides of the default 'user' role
                    # should not clear membership on startup
                    # since allowed users could be managed by the authenticator
                    elif kind == "users" and role_name == "user":
                        # Default user lists can be managed by the Authenticator,
                        # if unspecified in role config
                        pass
                    else:
                        # otherwise, omitting a member category is equivalent to specifying an empty list
                        setattr(role, kind, [])

        if self.authenticator.reset_managed_roles_on_startup:
            for kind, stale_assignments in stale_managed_role_assignment.items():
                if stale_assignments:
                    for assignment in stale_assignments:
                        self.db.delete(assignment)
                    self.log.info(
                        "Deleted %s stale %s role assignments previously added by an authenticator",
                        len(stale_assignments),
                        kind[:-1],
                    )

        db.commit()
        if self.authenticator.allowed_users:
            user_role = orm.Role.find(db, "user")
            self.log.debug("Assigning allowed_users to the user role")
            # query only those that need the user role _and don't have it_
            needs_user_role = db.query(orm.User).filter(
                orm.User.name.in_(self.authenticator.allowed_users)
                & ~orm.User.roles.any(id=user_role.id)
            )
            if self.log.isEnabledFor(logging.DEBUG):
                # filter on isEnabledFor to skip the extra `count()` query if we aren't going to log it
                self.log.debug(
                    f"Assigning {needs_user_role.count()} allowed_users to the user role"
                )

            for user in needs_user_role:
                roles.grant_role(db, user, user_role)

        admin_role = orm.Role.find(db, 'admin')
        for kind in admin_role_objects:
            Class = orm.get_class(kind)

            # sync obj.admin with admin role
            # query only those objects that do not match config
            # to avoid expensive query for no-op updates

            # always: in admin role sets admin = True
            for is_admin in db.query(Class).filter(
                (Class.admin == False) & Class.roles.any(id=admin_role.id)
            ):
                self.log.info(f"Setting admin=True on {is_admin}")
                is_admin.admin = True

            # iterate over users with admin=True
            # who are not in the admin role.
            for not_admin_obj in db.query(Class).filter(
                (Class.admin == True) & ~Class.roles.any(id=admin_role.id)
            ):
                if has_admin_role_spec[kind]:
                    # role membership specified exactly in config,
                    # already populated above.
                    # make sure user.admin matches admin role
                    # setting .admin=False for anyone no longer in admin role
                    self.log.warning(f"Removing admin=True from {not_admin_obj}")
                    not_admin_obj.admin = False
                else:
                    # no admin role membership declared,
                    # populate admin role from admin attribute (the old way, only additive)
                    roles.grant_role(db, not_admin_obj, admin_role)
        db.commit()
        # make sure that on hub upgrade, all users, services and tokens have at least one role (update with default)
        if getattr(self, '_rbac_upgrade', False):
            self.log.warning(
                "No roles found; assuming hub upgrade. Initializing default roles for all entities"
            )
            for kind in kinds:
                roles.check_for_default_roles(db, kind)

    async def _add_tokens(self, token_dict, kind):
        """Add tokens for users or services to the database"""
        if kind == 'user':
            Class = orm.User
        elif kind == 'service':
            Class = orm.Service
        else:
            raise ValueError(f"kind must be user or service, not {kind!r}")

        db = self.db
        for token, name in token_dict.items():
            if kind == 'user':
                name = self.authenticator.normalize_username(name)
                if not self.authenticator.validate_username(name):
                    raise ValueError(f"Token user name {name!r} is not valid")
            if kind == 'service':
                if not any(service_name == name for service_name in self._service_map):
                    self.log.warning(
                        f"service {name} not in services, creating implicitly. It is recommended to register services using services list."
                    )
            orm_token = orm.APIToken.find(db, token)
            if orm_token is None:
                obj = Class.find(db, name)
                created = False
                if obj is None:
                    created = True
                    self.log.debug("Adding %s %s to database", kind, name)
                    obj = Class(name=name)
                    db.add(obj)
                    db.commit()
                self.log.info("Adding API token for %s: %s", kind, name)
                try:
                    # set generated=False to ensure that user-provided tokens
                    # get extra hashing (don't trust entropy of user-provided tokens)
                    obj.new_api_token(
                        token,
                        note="from config",
                        generated=self.trust_user_provided_tokens,
                    )
                except Exception:
                    if created:
                        # don't allow bad tokens to create users
                        db.delete(obj)
                        db.commit()
                    raise
            else:
                self.log.debug("Not duplicating token %s", orm_token)
        db.commit()

    # purge expired tokens hourly
    purge_expired_tokens_interval = 3600

    @catch_db_error
    def purge_expired_tokens(self):
        """purge all expiring token objects from the database

        run periodically
        """
        # this should be all the subclasses of Expiring
        for cls in (orm.APIToken, orm.OAuthCode, orm.Share, orm.ShareCode):
            self.log.debug(f"Purging expired {cls.__name__}s")
            cls.purge_expired(self.db)

    async def init_api_tokens(self):
        """Load predefined API tokens (for services) into database"""

        await self._add_tokens(self.service_tokens, kind='service')
        await self._add_tokens(self.api_tokens, kind='user')

        await self.purge_expired_tokens()
        # purge expired tokens hourly
        # we don't need to be prompt about this
        # because expired tokens cannot be used anyway

        pc = PeriodicCallback(
            self.purge_expired_tokens, 1e3 * self.purge_expired_tokens_interval
        )
        self._periodic_callbacks["purge_expired_tokens"] = pc
        pc.start()

    def service_from_orm(
        self,
        orm_service: orm.Service,
    ) -> Service:
        """Create the service instance and related objects from
        ORM data.

        Args:
            orm_service (orm.Service): The `orm.Service` object

        Returns:
            Service: the created service
        """

        name = orm_service.name
        if self.subdomain_host:
            parsed_host = urlparse(self.subdomain_host)
            domain = self.subdomain_hook(name, parsed_host.hostname, kind="service")
            host = f"{parsed_host.scheme}://{domain}"
            if parsed_host.port:
                host = f"{host}:{parsed_host.port}"
        else:
            domain = host = ''

        service = Service(
            parent=self,
            app=self,
            base_url=self.base_url,
            db=self.db,
            orm=orm_service,
            roles=orm_service.roles,
            domain=domain,
            host=host,
            hub=self.hub,
        )
        traits = service.traits(input=True)
        for key, trait in traits.items():
            if not trait.metadata.get("in_db", True):
                continue
            orm_value = getattr(orm_service, key)
            if orm_value is not None:
                setattr(service, key, orm_value)

        if orm_service.oauth_client is not None:
            service.oauth_client_id = orm_service.oauth_client.identifier
            service.oauth_redirect_uri = orm_service.oauth_client.redirect_uri
            oauth_msg = f"with ouath_client_id={orm_service.oauth_client.identifier}"
        else:
            oauth_msg = "without oauth"

        self.log.info(f"Loaded service {service.name} from database {oauth_msg}.")

        self._service_map[name] = service

        return service

    def service_from_spec(
        self,
        spec: Dict,
        from_config=True,
    ) -> Optional[Service]:
        """Create the service instance and related objects from
        config data.

        Args:
            spec (Dict): The spec of service, defined in the config file.
            from_config (bool, optional): `True` if the service will be created
            from the config file, `False` if it is created from REST API.
            Defaults to `True`.

        Returns:
            Optional[Service]: The created service
        """

        if 'name' not in spec:
            raise ValueError(f'service spec must have a name: {spec}')

        name = spec['name']

        if self.subdomain_host:
            parsed_host = urlparse(self.subdomain_host)
            domain = self.subdomain_hook(name, parsed_host.hostname, kind="service")
            host = f"{parsed_host.scheme}://{domain}"
            if parsed_host.port:
                host = f"{host}:{parsed_host.port}"
        else:
            domain = host = ''

        # get/create orm
        orm_service = orm.Service.find(self.db, name=name)
        if orm_service is None:
            # not found, create a new one
            orm_service = orm.Service(name=name, from_config=from_config)
            self.db.add(orm_service)
            if spec.get('admin', False):
                self.log.warning(
                    f"Service {name} sets `admin: True`, which is deprecated in JupyterHub 2.0."
                    " You can assign now assign roles via `JupyterHub.load_roles` configuration."
                    " If you specify services in the admin role configuration, "
                    "the Service admin flag will be ignored."
                )
                roles.update_roles(self.db, entity=orm_service, roles=['admin'])
        else:
            # Do nothing if the config file tries to modify a API-base service
            # or vice versa.
            if orm_service.from_config != from_config:
                if from_config:
                    self.log.error(
                        f"The service {name} from the config file is trying to modify a runtime-created service with the same name"
                    )
                else:
                    self.log.error(
                        f"The runtime-created service {name} is trying to modify a config-based service with the same name"
                    )
                return
        orm_service.admin = spec.get('admin', False)

        self.db.commit()
        service = Service(
            parent=self,
            app=self,
            base_url=self.base_url,
            db=self.db,
            orm=orm_service,
            roles=orm_service.roles,
            domain=domain,
            host=host,
            hub=self.hub,
        )

        traits = service.traits(input=True)
        for key, value in spec.items():
            trait = traits.get(key)
            if trait is None:
                raise AttributeError(f"No such service field: {key}")
            setattr(service, key, value)
            # also set the value on the orm object
            # unless it's marked as not in the db
            # (e.g. on the oauth object)
            if trait.metadata.get("in_db", True):
                setattr(orm_service, key, value)

        if service.api_token:
            self.service_tokens[service.api_token] = service.name
        elif service.managed:
            # generate new token
            # TODO: revoke old tokens?
            service.api_token = service.orm.new_api_token(note="generated at startup")

        if service.url:
            parsed = urlparse(service.url)
            if parsed.scheme not in {"http", "https"}:
                raise ValueError(
                    f"Unsupported scheme in URL for service {name}: {service.url}. Must be http[s]"
                )

            port = None
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
                cookie_name=service.oauth_client_id,
                base_url=service.prefix,
            )
            self.db.add(server)
        else:
            service.orm.server = None

        if service.oauth_available:
            self.log.info(
                f"Creating service {service.name} with oauth_client_id={service.oauth_client_id}"
            )
            if not service.oauth_redirect_uri:
                # redirect uri has a default value if a URL is configured,
                # but must be specified explicitly for external services
                raise ValueError(
                    f"Service {service.name} has oauth configured, but is missing required oauth_redirect_uri."
                )
            allowed_scopes = set()
            if service.oauth_client_allowed_scopes:
                allowed_scopes.update(service.oauth_client_allowed_scopes)
            if service.oauth_roles:
                if not allowed_scopes:
                    # DEPRECATED? It's still convenient and valid,
                    # e.g. 'admin'
                    allowed_roles = list(
                        self.db.query(orm.Role).filter(
                            orm.Role.name.in_(service.oauth_roles)
                        )
                    )
                    allowed_scopes.update(roles.roles_to_scopes(allowed_roles))
                else:
                    self.log.warning(
                        f"Ignoring oauth_roles for {service.name}: {service.oauth_roles},"
                        f" using oauth_client_allowed_scopes={allowed_scopes}."
                    )
            oauth_client = self.oauth_provider.add_client(
                client_id=service.oauth_client_id,
                client_secret=service.api_token,
                redirect_uri=service.oauth_redirect_uri,
                description=f"JupyterHub service {service.name}",
            )
            service.orm.oauth_client = oauth_client
            # add access-scopes, derived from OAuthClient itself
            allowed_scopes.update(scopes.access_scopes(oauth_client))
            oauth_client.allowed_scopes = sorted(allowed_scopes)
        else:
            self.log.info(f"Creating service {service.name} without oauth.")
            if service.oauth_client:
                self.log.warning(
                    f"Deleting unused oauth client for service {service.name} with client_id={service.oauth_client.identifier}"
                )
                self.db.delete(service.oauth_client)

        self._service_map[name] = service

        return service

    def init_services(self):
        self._service_map.clear()
        for spec in self.services:
            self.service_from_spec(spec, from_config=True)

        for service_orm in self.db.query(orm.Service):
            if service_orm.from_config:
                # delete config-based services from db
                # that are not in current config file:
                if service_orm.name not in self._service_map:
                    self.db.delete(service_orm)
            else:
                self.service_from_orm(service_orm)

        self.db.commit()

    async def check_services_health(self):
        """Check connectivity of all services"""
        for name, service in self._service_map.items():
            if not service.url:
                # no URL to check, nothing to do
                continue
            try:
                await Server.from_orm(service.orm.server).wait_up(timeout=1, http=True)
            except AnyTimeoutError:
                self.log.warning(
                    "Cannot connect to %s service %s at %s",
                    service.kind,
                    name,
                    service.url,
                )
            else:
                self.log.debug(
                    "%s service %s running at %s",
                    service.kind.title(),
                    name,
                    service.url,
                )

    async def init_spawners(self):
        self.log.debug("Initializing spawners")
        db = self.db

        def _user_summary(user):
            """user is an orm.User, not a full user"""
            parts = [f'{user.name: >8}']
            if user.admin:
                parts.append('admin')
            for name, spawner in sorted(user.orm_spawners.items(), key=itemgetter(0)):
                if spawner.server:
                    parts.append(f'{user.name}:{name} running at {spawner.server}')
            return ' '.join(parts)

        async def user_stopped(user, server_name):
            spawner = user.spawners[server_name]
            status = await spawner.poll()
            self.log.warning(
                "User %s server stopped with exit code: %s", user.name, status
            )
            await self.proxy.delete_user(user, server_name)
            await user.stop(server_name)

        async def check_spawner(user, name, spawner):
            status = 0
            if spawner.server:
                if user.name in self.authenticator.blocked_users:
                    self.log.warning(
                        f"Stopping spawner for blocked user: {spawner._log_name}"
                    )
                    try:
                        await user.stop(name)
                    except Exception:
                        self.log.exception(
                            f"Failed to stop {spawner._log_name}",
                            exc_info=True,
                        )
                    return
                try:
                    status = await spawner.poll()
                except Exception:
                    self.log.exception(
                        "Failed to poll spawner for %s, assuming the spawner is not running.",
                        spawner._log_name,
                    )
                    status = -1

            if status is None:
                # poll claims it's running.
                # Check if it's really there
                url_in_db = spawner.server.url
                url = await spawner.get_url()
                if url != url_in_db:
                    self.log.warning(
                        "%s had invalid url %s. Updating to %s",
                        spawner._log_name,
                        url_in_db,
                        url,
                    )
                    urlinfo = urlparse(url)
                    spawner.server.protocol = urlinfo.scheme
                    spawner.server.ip = urlinfo.hostname
                    if urlinfo.port:
                        spawner.server.port = urlinfo.port
                    elif urlinfo.scheme == 'http':
                        spawner.server.port = 80
                    elif urlinfo.scheme == 'https':
                        spawner.server.port = 443
                    self.db.commit()

                self.log.debug(
                    "Verifying that %s is running at %s", spawner._log_name, url
                )
                try:
                    await user._wait_up(spawner)
                except AnyTimeoutError:
                    self.log.error(
                        "%s does not appear to be running at %s, shutting it down.",
                        spawner._log_name,
                        url,
                    )
                    status = -1

            if status is None:
                self.log.info("%s still running", user.name)
                spawner.add_poll_callback(user_stopped, user, name)
                spawner.start_polling()
            else:
                # user not running. This is expected if server is None,
                # but indicates the user's server died while the Hub wasn't running
                # if spawner.server is defined.
                if spawner.server:
                    self.log.warning(
                        "%s appears to have stopped while the Hub was down",
                        spawner._log_name,
                    )
                    try:
                        await user.stop(name)
                    except Exception:
                        self.log.exception(
                            f"Failed to cleanup {spawner._log_name} which appeared to stop while the Hub was down.",
                            exc_info=True,
                        )
                else:
                    self.log.debug("%s not running", spawner._log_name)

            spawner._check_pending = False

        # parallelize checks for running Spawners
        # run query on extant Server objects
        # so this is O(running servers) not O(total users)
        # Server objects can be associated with either a Spawner or a Service,
        # we are only interested in the ones associated with a Spawner
        check_futures = []

        for orm_user, orm_spawner in (
            self.db.query(orm.User, orm.Spawner)
            # join filters out any Users with no Spawners
            .join(orm.Spawner, orm.User._orm_spawners)
            # this gets Users with *any* active server
            .filter(orm.Spawner.server != None)
            # pre-load relationships to avoid O(N active servers) queries
            .options(
                contains_eager(orm.User._orm_spawners),
                selectinload(orm.Spawner.server),
            )
            .populate_existing()
        ):
            # instantiate Spawner wrapper and check if it's still alive
            # spawner should be running
            user = self.users[orm_user]
            spawner = user.spawners[orm_spawner.name]
            self.log.debug("Loading state for %s from db", spawner._log_name)
            # signal that check is pending to avoid race conditions
            spawner._check_pending = True
            f = asyncio.ensure_future(check_spawner(user, spawner.name, spawner))
            check_futures.append(f)

        # it's important that we get here before the first await
        # so that we know all spawners are instantiated and in the check-pending state

        # await checks after submitting them all
        if check_futures:
            self.log.debug(
                "Awaiting checks for %i possibly-running spawners", len(check_futures)
            )
            await asyncio.gather(*check_futures)
        db.commit()

        # only perform this query if we are going to log it
        if self.log_level <= logging.DEBUG:
            user_summaries = map(_user_summary, self.users.values())
            self.log.debug("Loaded users:\n%s", '\n'.join(user_summaries))

        active_counts = self.users.count_active_users()
        RUNNING_SERVERS.set(active_counts['active'])
        return len(check_futures)

    def init_oauth(self):
        base_url = self.hub.base_url
        self.oauth_provider = make_provider(
            lambda: self.db,
            url_prefix=url_path_join(base_url, 'api/oauth2'),
            login_url=url_path_join(base_url, 'login'),
            token_expires_in=self.oauth_token_expires_in,
        )

    def cleanup_oauth_clients(self):
        """Cleanup any OAuth clients that shouldn't be in the database.

        This should mainly be services that have been removed from configuration or renamed.
        """
        oauth_client_ids = {"jupyterhub"}
        for service in self._service_map.values():
            if service.oauth_available:
                oauth_client_ids.add(service.oauth_client_id)
        for user in self.users.values():
            for spawner in user.spawners.values():
                oauth_client_ids.add(spawner.oauth_client_id)
        for i, oauth_client in enumerate(self.db.query(orm.OAuthClient)):
            if oauth_client.identifier not in oauth_client_ids:
                self.log.warning("Deleting OAuth client %s", oauth_client.identifier)
                self.db.delete(oauth_client)
                # Some deployments that create temporary users may have left *lots*
                # of entries here.
                # Don't try to delete them all in one transaction,
                # commit at most 100 deletions at a time.
                if i % 100 == 0:
                    self.db.commit()
        self.db.commit()

    def init_proxy(self):
        """Load the Proxy config"""
        # FIXME: handle deprecated config here
        self.proxy = self.proxy_class(
            db_factory=lambda: self.db,
            public_url=self.bind_url,
            parent=self,
            app=self,
            log=self.log,
            hub=self.hub,
            host_routing=bool(self.subdomain_host),
            ssl_cert=self.ssl_cert,
            ssl_key=self.ssl_key,
        )

    def init_tornado_settings(self):
        """Set up the tornado settings dict."""
        base_url = self.hub.base_url
        jinja_options = dict(autoescape=True, enable_async=True)
        jinja_options.update(self.jinja_environment_options)
        base_path = self._template_paths_default()[0]
        if base_path not in self.template_paths:
            self.template_paths.append(base_path)
        loader = ChoiceLoader(
            [
                PrefixLoader({'templates': FileSystemLoader([base_path])}, '/'),
                FileSystemLoader(self.template_paths),
            ]
        )
        jinja_env = Environment(loader=loader, **jinja_options)
        # We need a sync jinja environment too, for the times we *must* use sync
        # code - particularly in RequestHandler.write_error. Since *that*
        # is called from inside the asyncio event loop, we can't actulaly just
        # schedule it on the loop - without starting another thread with its
        # own loop, which seems not worth the trouble. Instead, we create another
        # environment, exactly like this one, but sync
        del jinja_options['enable_async']
        jinja_env_sync = Environment(loader=loader, **jinja_options)

        login_url = url_path_join(base_url, 'login')
        logout_url = self.authenticator.logout_url(base_url)

        # if running from git, disable caching of require.js
        # otherwise cache based on server start time
        parent = os.path.dirname(os.path.dirname(jupyterhub.__file__))
        if os.path.isdir(os.path.join(parent, '.git')):
            version_hash = ''
        else:
            version_hash = datetime.now().strftime("%Y%m%d%H%M%S")

        oauth_no_confirm_list = set()
        for service in self._service_map.values():
            if service.oauth_no_confirm:
                self.log.warning(
                    "Allowing service %s to complete OAuth without confirmation on an authorization web page",
                    service.name,
                )
                oauth_no_confirm_list.add(service.oauth_client_id)

        # configure xsrf cookie
        # (user xsrf_cookie_kwargs works as override)
        xsrf_cookie_kwargs = self.tornado_settings.setdefault("xsrf_cookie_kwargs", {})
        if not xsrf_cookie_kwargs:
            # default to cookie_options
            xsrf_cookie_kwargs.update(self.tornado_settings.get("cookie_options", {}))

        # restrict xsrf cookie to hub base path
        xsrf_cookie_kwargs["path"] = self.hub.base_url

        settings = dict(
            log_function=log_request,
            config=self.config,
            log=self.log,
            db=self.db,
            proxy=self.proxy,
            hub=self.hub,
            activity_resolution=self.activity_resolution,
            admin_users=self.authenticator.admin_users,
            admin_access=self.admin_access,
            api_page_default_limit=self.api_page_default_limit,
            api_page_max_limit=self.api_page_max_limit,
            authenticator=self.authenticator,
            spawner_class=self.spawner_class,
            base_url=self.base_url,
            default_url=self.default_url,
            public_url=urlparse(self.public_url) if self.public_url else "",
            cookie_secret=self.cookie_secret,
            cookie_host_prefix_enabled=self.cookie_host_prefix_enabled,
            cookie_max_age_days=self.cookie_max_age_days,
            redirect_to_server=self.redirect_to_server,
            login_url=login_url,
            logout_url=logout_url,
            static_path=os.path.join(self.data_files_path, 'static'),
            static_url_prefix=url_path_join(self.hub.base_url, 'static/'),
            static_handler_class=CacheControlStaticFilesHandler,
            token_expires_in_max_seconds=self.token_expires_in_max_seconds,
            subdomain_hook=self.subdomain_hook,
            template_path=self.template_paths,
            template_vars=self.template_vars,
            jinja2_env=jinja_env,
            jinja2_env_sync=jinja_env_sync,
            version_hash=version_hash,
            subdomain_host=self.subdomain_host,
            domain=self.domain,
            statsd=self.statsd,
            implicit_spawn_seconds=self.implicit_spawn_seconds,
            allow_named_servers=self.allow_named_servers,
            default_server_name=self._default_server_name,
            named_server_limit_per_user=self.named_server_limit_per_user,
            oauth_provider=self.oauth_provider,
            oauth_no_confirm_list=oauth_no_confirm_list,
            concurrent_spawn_limit=self.concurrent_spawn_limit,
            spawn_throttle_retry_range=self.spawn_throttle_retry_range,
            active_server_limit=self.active_server_limit,
            authenticate_prometheus=self.authenticate_prometheus,
            internal_ssl=self.internal_ssl,
            internal_certs_location=self.internal_certs_location,
            internal_authorities=self.internal_ssl_authorities,
            internal_trust_bundles=self.internal_trust_bundles,
            internal_ssl_key=self.internal_ssl_key,
            internal_ssl_cert=self.internal_ssl_cert,
            internal_ssl_ca=self.internal_ssl_ca,
            trusted_alt_names=self.trusted_alt_names,
            shutdown_on_logout=self.shutdown_on_logout,
            eventlog=self.eventlog,
            app=self,
            xsrf_cookies=True,
        )
        # allow configured settings to have priority
        settings.update(self.tornado_settings)
        self.tornado_settings = settings
        # constructing users requires access to tornado_settings
        self.tornado_settings['users'] = self.users
        self.tornado_settings['services'] = self._service_map

    def init_tornado_application(self):
        """Instantiate the tornado Application object"""
        self.tornado_application = web.Application(
            self.handlers, **self.tornado_settings
        )

    def init_pycurl(self):
        """Configure tornado to use pycurl by default, if available"""
        # use pycurl by default, if available:
        try:
            AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        except ImportError as e:
            self.log.debug(
                "Could not load pycurl: %s\npycurl is recommended if you have a large number of users.",
                e,
            )

    def init_eventlog(self):
        """Set up the event logging system."""
        self.eventlog = EventLogger(parent=self)

        for schema in (Path(here) / "event-schemas").glob("**/*.yaml"):
            self.eventlog.register_event_schema(schema)

    def write_pid_file(self):
        pid = os.getpid()
        if self.pid_file:
            self.log.debug("Writing PID %i to %s", pid, self.pid_file)
            with open(self.pid_file, 'w') as f:
                f.write(str(pid))

    @catch_config_error
    async def initialize(self, *args, **kwargs):
        hub_startup_start_time = time.perf_counter()
        super().initialize(*args, **kwargs)
        if self.generate_config or self.generate_certs or self.subapp:
            return
        if self.extra_args:
            self.exit(
                f"Unrecognized command-line arguments: {' '.join(shlex.quote(arg) for arg in self.extra_args)!r}"
            )
        self._start_future = asyncio.Future()

        def record_start(f):
            startup_time = time.perf_counter() - hub_startup_start_time
            self.log.debug("It took %.3f seconds for the Hub to start", startup_time)
            HUB_STARTUP_DURATION_SECONDS.observe(startup_time)

        self._start_future.add_done_callback(record_start)

        self.load_config_file(self.config_file)
        self.init_logging()
        self.log.info("Running JupyterHub version %s", jupyterhub.__version__)
        if 'JupyterHubApp' in self.config:
            self.log.warning(
                "Use JupyterHub in config, not JupyterHubApp. Outdated config:\n%s",
                '\n'.join(
                    f'JupyterHubApp.{key} = {value!r}'
                    for key, value in self.config.JupyterHubApp.items()
                ),
            )
            cfg = self.config.copy()
            cfg.JupyterHub.merge(cfg.JupyterHubApp)
            self.update_config(cfg)
        self.write_pid_file()

        def _log_cls(name, cls):
            """Log a configured class

            Logs the class and version (if found) of Authenticator
            and Spawner
            """
            # try to guess the version from the top-level module
            # this will work often enough to be useful.
            # no need to be perfect.
            if cls.__module__:
                mod = sys.modules.get(cls.__module__.split('.')[0])
                version = getattr(mod, '__version__', '')
                if version:
                    version = f'-{version}'
            else:
                version = ''
            self.log.info(
                "Using %s: %s.%s%s", name, cls.__module__ or '', cls.__name__, version
            )

        _log_cls("Authenticator", self.authenticator_class)
        _log_cls("Spawner", self.spawner_class)
        _log_cls("Proxy", self.proxy_class)

        self.init_eventlog()
        self.init_pycurl()
        self.init_secrets()
        self.init_internal_ssl()
        self.init_db()
        self.init_hub()
        self.init_proxy()
        self.init_oauth()
        await self.init_role_creation()
        await self.init_users()
        await self.init_groups()
        self.init_services()
        await self.init_api_tokens()
        await self.init_role_assignment()
        await self.init_blocked_users()
        self.init_tornado_settings()
        self.init_handlers()
        self.init_tornado_application()

        # init_spawners can take a while
        init_spawners_timeout = self.init_spawners_timeout
        if init_spawners_timeout < 0:
            # negative timeout means forever (previous, most stable behavior)
            init_spawners_timeout = 86400

        init_start_time = time.perf_counter()
        init_spawners_future = asyncio.ensure_future(self.init_spawners())

        def log_init_time(f):
            n_spawners = f.result()
            spawner_initialization_time = time.perf_counter() - init_start_time
            INIT_SPAWNERS_DURATION_SECONDS.observe(spawner_initialization_time)
            self.log.info(
                "Initialized %i spawners in %.3f seconds",
                n_spawners,
                spawner_initialization_time,
            )

        init_spawners_future.add_done_callback(log_init_time)

        try:
            # don't allow a zero timeout because we still need to be sure
            # that the Spawner objects are defined and pending
            await gen.with_timeout(
                timedelta(seconds=max(init_spawners_timeout, 1)), init_spawners_future
            )
        except AnyTimeoutError:
            self.log.warning(
                "init_spawners did not complete within %i seconds. "
                "Allowing to complete in the background.",
                self.init_spawners_timeout,
            )

        if init_spawners_future.done():
            self.cleanup_oauth_clients()
        else:
            # schedule async operations after init_spawners finishes
            async def finish_init_spawners():
                await init_spawners_future
                # schedule cleanup after spawners are all set up
                # because it relies on the state resolved by init_spawners
                self.cleanup_oauth_clients()
                # trigger a proxy check as soon as all spawners are ready
                # because this may be *after* the check made as part of normal startup.
                # To avoid races with partially-complete start,
                # ensure that start is complete before running this check.
                await self._start_future
                await self.proxy.check_routes(self.users, self._service_map)

            asyncio.ensure_future(finish_init_spawners())
        metrics_collector = self.metrics_collector = PeriodicMetricsCollector(
            parent=self, db=self.db
        )

    async def cleanup(self):
        """Shutdown managed services and various subprocesses. Cleanup runtime files."""

        futures = []

        managed_services = [s for s in self._service_map.values() if s.managed]
        if managed_services:
            self.log.info("Cleaning up %i services...", len(managed_services))
            for service in managed_services:
                await service.stop()

        if self.cleanup_servers:
            self.log.info("Cleaning up single-user servers...")
            # request (async) process termination
            for uid, user in self.users.items():
                for name, spawner in list(user.spawners.items()):
                    if spawner.active:
                        futures.append(asyncio.ensure_future(user.stop(name)))
        else:
            self.log.info("Leaving single-user servers running")

        # clean up proxy while single-user servers are shutting down
        if self.cleanup_proxy:
            if self.proxy.should_start:
                self.log.debug("Stopping proxy")
                await maybe_future(self.proxy.stop())
            else:
                self.log.info("I didn't start the proxy, I can't clean it up")
        else:
            self.log.info("Leaving proxy running")

        # wait for the requests to stop finish:
        for f in futures:
            try:
                await f
            except Exception as e:
                self.log.error("Failed to stop user: %s", e)

        self.db.commit()

        if self.pid_file and os.path.exists(self.pid_file):
            self.log.info("Cleaning up PID file %s", self.pid_file)
            os.remove(self.pid_file)

        self.log.info("...done")

    def write_config_file(self):
        """Write our default config to a .py config file"""
        config_file_dir = os.path.dirname(os.path.abspath(self.config_file))
        if not os.path.isdir(config_file_dir):
            self.exit(
                f"{config_file_dir} does not exist. The destination directory must exist before generating config file."
            )
        if os.path.exists(self.config_file) and not self.answer_yes:
            answer = ''

            def ask():
                prompt = f"Overwrite {self.config_file} with default config? [y/N]"
                try:
                    return input(prompt).lower() or 'n'
                except KeyboardInterrupt:
                    print('')  # empty line
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
        print(f"Writing default config to: {self.config_file}")
        with open(self.config_file, mode='w') as f:
            f.write(config_text)

    @catch_db_error
    async def update_last_activity(self):
        """Update User.last_activity timestamps from the proxy"""
        routes = await self.proxy.get_all_routes()
        users_count = 0
        active_users_count = 0
        now = utcnow(with_tz=False)
        for prefix, route in routes.items():
            route_data = route['data']
            if 'user' not in route_data:
                # not a user route, ignore it
                continue
            if 'server_name' not in route_data:
                continue
            users_count += 1
            if 'last_activity' not in route_data:
                # no last activity data (possibly proxy other than CHP)
                continue
            user = orm.User.find(self.db, route_data['user'])
            if user is None:
                self.log.warning("Found no user for route: %s", route)
                continue
            spawner = user.orm_spawners.get(route_data['server_name'])
            if spawner is None:
                self.log.warning("Found no spawner for route: %s", route)
                continue
            dt = parse_date(route_data['last_activity'])
            if dt.tzinfo:
                # strip timezone info to naive UTC datetime
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

            if user.last_activity:
                user.last_activity = max(user.last_activity, dt)
            else:
                user.last_activity = dt
            if spawner.last_activity:
                spawner.last_activity = max(spawner.last_activity, dt)
            else:
                spawner.last_activity = dt
            if (now - user.last_activity).total_seconds() < self.active_user_window:
                active_users_count += 1
        self.statsd.gauge('users.running', users_count)
        self.statsd.gauge('users.active', active_users_count)

        try:
            self.db.commit()
        except SQLAlchemyError:
            self.log.exception("Rolling back session due to database error")
            self.db.rollback()
            return

        await self.proxy.check_routes(self.users, self._service_map, routes)

    async def start_service(
        self,
        service_name: str,
        service: Service,
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> bool:
        """Start a managed service or poll for external service

        Args:
            service_name (str): Name of the service.
            service (Service): The service object.

        Returns:
            boolean: Returns `True` if the service is started successfully,
            returns `False` otherwise.
        """
        if ssl_context is None:
            ssl_context = make_ssl_context(
                self.internal_ssl_key,
                self.internal_ssl_cert,
                cafile=self.internal_ssl_ca,
                purpose=ssl.Purpose.CLIENT_AUTH,
            )

        msg = f'{service_name} at {service.url}' if service.url else service_name
        if service.managed:
            self.log.info("Starting managed service %s", msg)
            try:
                await service.start()
            except Exception as e:
                self.log.critical(
                    "Failed to start service %s", service_name, exc_info=True
                )
                return False
        else:
            self.log.info("Adding external service %s", msg)

        if service.url:
            tries = 10 if service.managed else 1
            for i in range(tries):
                try:
                    await Server.from_orm(service.orm.server).wait_up(
                        http=True, timeout=1, ssl_context=ssl_context
                    )
                except AnyTimeoutError:
                    if service.managed:
                        status = await service.spawner.poll()
                        if status is not None:
                            self.log.critical(
                                "Service %s exited with status %s",
                                service_name,
                                status,
                            )
                            return False
                else:
                    return True
            else:
                if service.managed:
                    self.log.critical(
                        "Cannot connect to %s service %s",
                        service_name,
                        service.kind,
                    )
                else:
                    self.log.warning(
                        "Cannot connect to %s service %s at %s. Is it running?",
                        service.kind,
                        service_name,
                        service.url,
                    )
                return False
        return True

    async def start(self):
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

        if self.generate_certs:
            self.load_config_file(self.config_file)
            if not self.internal_ssl:
                self.log.warning(
                    "You'll need to enable `internal_ssl` "
                    "in the `jupyterhub_config` file to use "
                    "these certs."
                )
                self.internal_ssl = True
            self.init_internal_ssl()
            self.log.info(
                f"Certificates written to directory `{self.internal_certs_location}`"
            )
            loop.stop()
            return

        # start collecting metrics
        self.metrics_collector.start()

        # start the proxy
        if self.proxy.should_start:
            try:
                await self.proxy.start()
            except Exception as e:
                self.log.critical("Failed to start proxy", exc_info=True)
                self.exit(1)
        else:
            self.log.info("Not starting proxy")

        # verify that we can talk to the proxy before listening.
        # avoids delayed failure if we can't talk to the proxy
        await self.proxy.get_all_routes()

        ssl_context = make_ssl_context(
            self.internal_ssl_key,
            self.internal_ssl_cert,
            cafile=self.internal_ssl_ca,
            purpose=ssl.Purpose.CLIENT_AUTH,
        )

        # start the webserver
        self.http_server = tornado.httpserver.HTTPServer(
            self.tornado_application,
            ssl_options=ssl_context,
            xheaders=True,
            trusted_downstream=self.trusted_downstream_ips,
        )
        bind_url = urlparse(self.hub.bind_url)
        try:
            if bind_url.scheme.startswith('unix+'):
                from tornado.netutil import bind_unix_socket

                socket = bind_unix_socket(unquote(bind_url.netloc))
                self.http_server.add_socket(socket)
            else:
                ip = bind_url.hostname
                port = bind_url.port
                if not port:
                    if bind_url.scheme == 'https':
                        port = 443
                    else:
                        port = 80
                self.http_server.listen(port, address=ip)
            self.log.info("Hub API listening on %s", self.hub.bind_url)
            if self.hub.url != self.hub.bind_url:
                self.log.info("Private Hub API connect url %s", self.hub.url)
        except Exception:
            self.log.error("Failed to bind hub to %s", self.hub.bind_url)
            raise

        # start the service(s)
        for service_name, service in self._service_map.items():
            service_ready = await self.start_service(service_name, service, ssl_context)
            if not service_ready and service.managed:
                self.exit(1)

        await self.proxy.check_routes(self.users, self._service_map)

        # Check services health
        if self.service_check_interval:
            pc = PeriodicCallback(
                self.check_services_health, 1e3 * self.service_check_interval
            )
            self._periodic_callbacks["service_check"] = pc
            pc.start()

        if self.last_activity_interval:
            pc = PeriodicCallback(
                self.update_last_activity, 1e3 * self.last_activity_interval
            )
            self._periodic_callbacks["last_activity"] = pc
            pc.start()

        if self.proxy.should_start:
            self.log.info("JupyterHub is now running at %s", self.proxy.public_url)
        else:
            self.log.info(
                "JupyterHub is now running, internal Hub API at %s", self.hub.url
            )
        # Use atexit for Windows, it doesn't have signal handling support
        if _mswindows:
            atexit.register(self.atexit)
        # register cleanup on both TERM and INT
        self.init_signal()
        self._start_future.set_result(None)

    def init_signal(self):
        loop = asyncio.get_event_loop()
        for s in (signal.SIGTERM, signal.SIGINT):
            if not _mswindows:
                loop.add_signal_handler(
                    s, lambda s=s: asyncio.ensure_future(self.shutdown_cancel_tasks(s))
                )
            else:
                signal.signal(s, self.win_shutdown_cancel_tasks)

        if not _mswindows:
            infosignals = [signal.SIGUSR1]
            if hasattr(signal, 'SIGINFO'):
                infosignals.append(signal.SIGINFO)
            for s in infosignals:
                loop.add_signal_handler(
                    s, lambda s=s: asyncio.ensure_future(self.log_status(s))
                )

    async def log_status(self, sig):
        """Log current status, triggered by SIGINFO (^T in many terminals)"""
        self.log.critical("Received signal %s...", sig.name)
        print_ps_info()
        print_stacks()

    def win_shutdown_cancel_tasks(self, signum, frame):
        self.log.critical("Received signalnum %s, , initiating shutdown...", signum)
        raise SystemExit(128 + signum)

    def _init_asyncio_patch(self):
        """Set default asyncio policy to be compatible with Tornado.

        Tornado 6 (at least) is not compatible with the default
        asyncio implementation on Windows.

        Pick the older SelectorEventLoopPolicy on Windows
        if the known-incompatible default policy is in use.

        Do this as early as possible to make it a low priority and overrideable.

        ref: https://github.com/tornadoweb/tornado/issues/2608

        FIXME: If/when tornado supports the defaults in asyncio,
               remove and bump tornado requirement for py38.
        """
        if sys.platform.startswith("win") and sys.version_info >= (3, 8):
            try:
                from asyncio import (
                    WindowsProactorEventLoopPolicy,
                    WindowsSelectorEventLoopPolicy,
                )
            except ImportError:
                pass
                # not affected
            else:
                if (
                    type(asyncio.get_event_loop_policy())
                    is WindowsProactorEventLoopPolicy
                ):
                    # WindowsProactorEventLoopPolicy is not compatible with Tornado 6.
                    # Fallback to the pre-3.8 default of WindowsSelectorEventLoopPolicy.
                    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

    _atexit_ran = False

    def atexit(self):
        """atexit callback"""
        if self._atexit_ran:
            return
        self._atexit_ran = True
        self._init_asyncio_patch()
        # run the cleanup step (in a new loop, because the interrupted one is unclean)
        asyncio.run(self.cleanup())

    async def shutdown_cancel_tasks(self, sig=None):
        """Cancel all other tasks of the event loop and initiate cleanup"""
        if sig is None:
            self.log.critical("Initiating shutdown...")
        else:
            self.log.critical("Received signal %s, initiating shutdown...", sig.name)

        await self.cleanup()

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        if tasks:
            self.log.debug("Cancelling pending tasks")
            [t.cancel() for t in tasks]

            try:
                await asyncio.wait(tasks)
            except asyncio.CancelledError as e:
                self.log.debug("Caught Task CancelledError. Ignoring")
            except StopAsyncIteration as e:
                self.log.error("Caught StopAsyncIteration Exception", exc_info=True)

            tasks = [t for t in asyncio.all_tasks()]
            for t in tasks:
                self.log.debug("Task status: %s", t)
        self._stop_event_loop()

    def _stop_event_loop(self):
        """In a method to allow tests to not do this"""
        asyncio.get_event_loop().stop()

    def stop(self):
        if not self.io_loop:
            return
        if self.http_server:
            self.http_server.stop()
        if self.metrics_collector:
            self.metrics_collector.stop()
        self.io_loop.add_callback(self.shutdown_cancel_tasks)
        # stop periodic callbacks
        for pc in self._periodic_callbacks.values():
            pc.stop()

    async def start_show_config(self):
        """Async wrapper around base start_show_config method"""
        # We need this because of our custom launch_instance_async,
        # where `start` isn't a blocking call,
        # it only gets async things going
        # and `--show-config` replaces `start` with a blocking function.
        # so our version:
        # 1. calls the original blocking method
        # 2. stops the event loop when we are done, so the process exits
        super().start_show_config()
        self.exit(0)

    async def launch_instance_async(self, argv=None):
        try:
            await self.initialize(argv)
            await self.start()
        except Exception as e:
            self.log.exception("")
            self.exit(1)

    @classmethod
    def launch_instance(cls, argv=None):
        self = cls.instance()
        self._init_asyncio_patch()
        loop = IOLoop(make_current=False)

        try:
            loop.run_sync(partial(self.launch_instance_async, argv))
        except Exception:
            loop.close()
            raise

        try:
            loop.start()
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            loop.stop()
            loop.close()


NewToken.classes.append(JupyterHub)
UpgradeDB.classes.append(JupyterHub)

main = JupyterHub.launch_instance

if __name__ == "__main__":
    # don't invoke __main__.main here because __main__.JupyterHub
    # is not jupyterhub.app.JupyterHub. There will be two!
    from jupyterhub import app

    app.JupyterHub.launch_instance()
