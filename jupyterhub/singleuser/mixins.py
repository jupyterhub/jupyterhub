#!/usr/bin/env python
"""Mixins to regular notebook server to add JupyterHub auth.

Meant to be compatible with jupyter_server and classic notebook

Use make_singleuser_app to create a compatible Application class
with JupyterHub authentication mixins enabled.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import json
import logging
import os
import random
import secrets
import sys
import warnings
from datetime import timezone
from importlib import import_module
from pathlib import Path
from textwrap import dedent
from urllib.parse import urlparse

from jinja2 import ChoiceLoader, FunctionLoader
from tornado import ioloop
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.web import RequestHandler
from traitlets import (
    Any,
    Bool,
    Bytes,
    CUnicode,
    Integer,
    TraitError,
    Unicode,
    default,
    import_item,
    observe,
    validate,
)
from traitlets.config import Configurable

from .._version import __version__, _check_version
from ..log import log_request
from ..services.auth import HubOAuth, HubOAuthCallbackHandler, HubOAuthenticated
from ..utils import (
    _bool_env,
    exponential_backoff,
    isoformat,
    make_ssl_context,
    url_path_join,
)
from ._disable_user_config import _disable_user_config, _exclude_home

# Authenticate requests with the Hub


class HubAuthenticatedHandler(HubOAuthenticated):
    """Class we are going to patch-in for authentication with the Hub"""

    @property
    def allow_admin(self):
        return self.settings.get(
            'admin_access', os.getenv('JUPYTERHUB_ADMIN_ACCESS') or False
        )

    @property
    def hub_auth(self):
        return self.settings['hub_auth']

    @property
    def hub_users(self):
        return {self.settings['user']}

    @property
    def hub_groups(self):
        if self.settings['group']:
            return {self.settings['group']}
        return set()


class JupyterHubLoginHandlerMixin:
    """LoginHandler that hooks up Hub authentication"""

    @staticmethod
    def login_available(settings):
        return True

    @staticmethod
    def is_token_authenticated(handler):
        """Is the request token-authenticated?"""
        if getattr(handler, '_cached_hub_user', None) is None:
            # ensure get_user has been called, so we know if we're token-authenticated
            handler.get_current_user()
        return getattr(handler, '_token_authenticated', False)

    @staticmethod
    def get_user(handler):
        """alternative get_current_user to query the Hub

        Thus shouldn't be called anymore because HubAuthenticatedHandler
        should have already overridden get_current_user().

        Keep here to protect uncommon circumstance of multiple BaseHandlers
        from missing auth.

        e.g. when multiple BaseHandler classes are used.
        """
        if HubAuthenticatedHandler not in handler.__class__.mro():
            warnings.warn(
                f"Expected to see HubAuthenticatedHandler in {handler.__class__}.mro(),"
                " patching in at call time. Hub authentication is still applied.",
                RuntimeWarning,
                stacklevel=2,
            )
            # patch HubAuthenticated into the instance
            handler.__class__ = type(
                handler.__class__.__name__,
                (HubAuthenticatedHandler, handler.__class__),
                {},
            )
            # patch into the class itself so this doesn't happen again for the same class
            patch_base_handler(handler.__class__)
        return handler.get_current_user()

    @classmethod
    def validate_security(cls, app, ssl_options=None):
        """Prevent warnings about security from base class"""
        return


class JupyterHubLogoutHandlerMixin:
    def get(self):
        self.settings['hub_auth'].clear_cookie(self)
        self.redirect(
            self.settings['hub_host']
            + url_path_join(self.settings['hub_prefix'], 'logout')
        )


class OAuthCallbackHandlerMixin(HubOAuthCallbackHandler):
    """Mixin IPythonHandler to get the right error pages, etc."""

    @property
    def hub_auth(self):
        return self.settings['hub_auth']


# register new hub related command-line aliases
aliases = {
    'user': 'SingleUserNotebookApp.user',
    'group': 'SingleUserNotebookApp.group',
    'hub-prefix': 'SingleUserNotebookApp.hub_prefix',
    'hub-host': 'SingleUserNotebookApp.hub_host',
    'hub-api-url': 'SingleUserNotebookApp.hub_api_url',
    'base-url': 'SingleUserNotebookApp.base_url',
}
flags = {
    'disable-user-config': (
        {'SingleUserNotebookApp': {'disable_user_config': True}},
        "Disable user-controlled configuration of the notebook server.",
    )
}


class SingleUserNotebookAppMixin(Configurable):
    """A Subclass of the regular NotebookApp that is aware of the parent multiuser context."""

    description = dedent(
        """
    Single-user server for JupyterHub. Extends the Jupyter Notebook server.

    Meant to be invoked by JupyterHub Spawners, not directly.
    """
    )

    examples = ""
    subcommands = {}
    version = __version__

    # must be set in mixin subclass
    # make_singleuser_app sets these
    # aliases = aliases
    # flags = flags
    # login_handler_class = JupyterHubLoginHandler
    # logout_handler_class = JupyterHubLogoutHandler
    # oauth_callback_handler_class = OAuthCallbackHandler
    # classes = NotebookApp.classes + [HubOAuth]

    # disable single-user app's localhost checking
    allow_remote_access = True

    # don't store cookie secrets
    cookie_secret_file = ''
    # always generate a new cookie secret on launch
    # ensures that each spawn clears any cookies from previous session,
    # triggering OAuth again
    cookie_secret = Bytes()

    def _cookie_secret_default(self):
        return secrets.token_bytes(32)

    user = CUnicode().tag(config=True)
    group = CUnicode().tag(config=True)

    @default('user')
    def _default_user(self):
        return os.environ.get('JUPYTERHUB_USER') or ''

    @default('group')
    def _default_group(self):
        return os.environ.get('JUPYTERHUB_GROUP') or ''

    @observe('user')
    def _user_changed(self, change):
        self.log.name = change.new

    @default("default_url")
    def _default_url(self):
        return os.environ.get("JUPYTERHUB_DEFAULT_URL", "/tree/")

    hub_host = Unicode().tag(config=True)

    hub_prefix = Unicode('/hub/').tag(config=True)

    @default('keyfile')
    def _keyfile_default(self):
        return os.environ.get('JUPYTERHUB_SSL_KEYFILE') or ''

    @default('certfile')
    def _certfile_default(self):
        return os.environ.get('JUPYTERHUB_SSL_CERTFILE') or ''

    @default('client_ca')
    def _client_ca_default(self):
        return os.environ.get('JUPYTERHUB_SSL_CLIENT_CA') or ''

    @default('hub_prefix')
    def _hub_prefix_default(self):
        base_url = os.environ.get('JUPYTERHUB_BASE_URL') or '/'
        return base_url + 'hub/'

    hub_api_url = Unicode().tag(config=True)

    @default('hub_api_url')
    def _hub_api_url_default(self):
        return os.environ.get('JUPYTERHUB_API_URL') or 'http://127.0.0.1:8081/hub/api'

    # defaults for some configurables that may come from service env variables:
    @default('base_url')
    def _base_url_default(self):
        return os.environ.get('JUPYTERHUB_SERVICE_PREFIX') or '/'

    # Note: this may be removed if notebook module is >= 5.0.0b1
    @validate('base_url')
    def _validate_base_url(self, proposal):
        """ensure base_url starts and ends with /"""
        value = proposal.value
        if not value.startswith('/'):
            value = '/' + value
        if not value.endswith('/'):
            value = value + '/'
        return value

    @default('port')
    def _port_default(self):
        if os.environ.get('JUPYTERHUB_SERVICE_URL'):
            url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
            if url.port:
                return url.port
            elif url.scheme == 'http':
                return 80
            elif url.scheme == 'https':
                return 443
        return 8888

    @default('ip')
    def _ip_default(self):
        if os.environ.get('JUPYTERHUB_SERVICE_URL'):
            url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
            if url.hostname:
                return url.hostname
        return '127.0.0.1'

    # disable some single-user configurables
    token = ''
    open_browser = False
    quit_button = False
    trust_xheaders = True

    port_retries = (
        0  # disable port-retries, since the Spawner will tell us what port to use
    )

    disable_user_config = Bool(
        False,
        help="""Disable user configuration of single-user server.

        Prevents user-writable files that normally configure the single-user server
        from being loaded, ensuring admins have full control of configuration.
        """,
    ).tag(config=True)

    @default("disable_user_config")
    def _default_disable_user_config(self):
        return _bool_env("JUPYTERHUB_DISABLE_USER_CONFIG")

    @default("root_dir")
    def _default_root_dir(self):
        if os.environ.get("JUPYTERHUB_ROOT_DIR"):
            proposal = {"value": os.environ["JUPYTERHUB_ROOT_DIR"]}
            # explicitly call validator, not called on default values
            return self._notebook_dir_validate(proposal)
        else:
            return os.getcwd()

    # notebook_dir is used by the classic notebook server
    # root_dir is the future in jupyter server
    @default("notebook_dir")
    def _default_notebook_dir(self):
        return self._default_root_dir()

    @validate("notebook_dir", "root_dir")
    def _notebook_dir_validate(self, proposal):
        value = os.path.expanduser(proposal['value'])
        # Strip any trailing slashes
        # *except* if it's root
        _, path = os.path.splitdrive(value)
        if path == os.sep:
            return value
        value = value.rstrip(os.sep)
        if not os.path.isabs(value):
            # If we receive a non-absolute path, make it absolute.
            value = os.path.abspath(value)
        if not os.path.isdir(value):
            raise TraitError("No such notebook dir: %r" % value)
        return value

    @default('log_level')
    def _log_level_default(self):
        if _bool_env("JUPYTERHUB_DEBUG"):
            return logging.DEBUG
        else:
            return logging.INFO

    @default('log_datefmt')
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    @default('log_format')
    def _log_format_default(self):
        """override default log format to include time"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    def _confirm_exit(self):
        # disable the exit confirmation for background notebook processes
        self.io_loop.add_callback_from_signal(self.io_loop.stop)

    def migrate_config(self):
        if self.disable_user_config:
            # disable config-migration when user config is disabled
            return
        else:
            super().migrate_config()

    @property
    def config_file_paths(self):
        path = super().config_file_paths

        if self.disable_user_config:
            # filter out user-writable config dirs if user config is disabled
            path = list(_exclude_home(path))
        return path

    @property
    def nbextensions_path(self):
        path = super().nbextensions_path

        if self.disable_user_config:
            path = list(_exclude_home(path))
        return path

    @validate('static_custom_path')
    def _validate_static_custom_path(self, proposal):
        path = proposal['value']
        if self.disable_user_config:
            path = list(_exclude_home(path))
        return path

    # create dynamic default http client,
    # configured with any relevant ssl config
    hub_http_client = Any()

    @default('hub_http_client')
    def _default_client(self):
        ssl_context = make_ssl_context(
            self.keyfile, self.certfile, cafile=self.client_ca
        )
        AsyncHTTPClient.configure(None, defaults={"ssl_options": ssl_context})
        return AsyncHTTPClient()

    async def check_hub_version(self):
        """Test a connection to my Hub

        - exit if I can't connect at all
        - check version and warn on sufficient mismatch
        """
        client = self.hub_http_client
        RETRIES = 5
        for i in range(1, RETRIES + 1):
            try:
                resp = await client.fetch(self.hub_api_url)
            except Exception:
                self.log.exception(
                    "Failed to connect to my Hub at %s (attempt %i/%i). Is it running?",
                    self.hub_api_url,
                    i,
                    RETRIES,
                )
                await asyncio.sleep(min(2**i, 16))
            else:
                break
        else:
            self.exit(1)

        hub_version = resp.headers.get('X-JupyterHub-Version')
        _check_version(hub_version, __version__, self.log)

    server_name = Unicode()

    @default('server_name')
    def _server_name_default(self):
        return os.environ.get('JUPYTERHUB_SERVER_NAME', '')

    hub_activity_url = Unicode(
        config=True, help="URL for sending JupyterHub activity updates"
    )

    @default('hub_activity_url')
    def _default_activity_url(self):
        return os.environ.get('JUPYTERHUB_ACTIVITY_URL', '')

    hub_activity_interval = Integer(
        300,
        config=True,
        help="""
        Interval (in seconds) on which to update the Hub
        with our latest activity.
        """,
    )

    @default('hub_activity_interval')
    def _default_activity_interval(self):
        env_value = os.environ.get('JUPYTERHUB_ACTIVITY_INTERVAL')
        if env_value:
            return int(env_value)
        else:
            return 300

    _last_activity_sent = Any(allow_none=True)

    async def notify_activity(self):
        """Notify jupyterhub of activity"""
        client = self.hub_http_client
        last_activity = self.web_app.last_activity()
        if not last_activity:
            self.log.debug("No activity to send to the Hub")
            return
        if last_activity:
            # protect against mixed timezone comparisons
            if not last_activity.tzinfo:
                # assume naive timestamps are utc
                self.log.warning("last activity is using naive timestamps")
                last_activity = last_activity.replace(tzinfo=timezone.utc)

        if self._last_activity_sent and last_activity < self._last_activity_sent:
            self.log.debug("No activity since %s", self._last_activity_sent)
            return

        last_activity_timestamp = isoformat(last_activity)

        async def notify():
            self.log.debug("Notifying Hub of activity %s", last_activity_timestamp)
            req = HTTPRequest(
                url=self.hub_activity_url,
                method='POST',
                headers={
                    "Authorization": f"token {self.hub_auth.api_token}",
                    "Content-Type": "application/json",
                },
                body=json.dumps(
                    {
                        'servers': {
                            self.server_name: {'last_activity': last_activity_timestamp}
                        },
                        'last_activity': last_activity_timestamp,
                    }
                ),
            )
            try:
                await client.fetch(req)
            except Exception:
                self.log.exception("Error notifying Hub of activity")
                return False
            else:
                return True

        await exponential_backoff(
            notify,
            fail_message="Failed to notify Hub of activity",
            start_wait=1,
            max_wait=15,
            timeout=60,
        )
        self._last_activity_sent = last_activity

    async def keep_activity_updated(self):
        if not self.hub_activity_url or not self.hub_activity_interval:
            self.log.warning("Activity events disabled")
            return
        self.log.info(
            "Updating Hub with activity every %s seconds", self.hub_activity_interval
        )
        while True:
            try:
                await self.notify_activity()
            except Exception as e:
                self.log.exception("Error notifying Hub of activity")
            # add 20% jitter to the interval to avoid alignment
            # of lots of requests from user servers
            t = self.hub_activity_interval * (1 + 0.2 * (random.random() - 0.5))
            await asyncio.sleep(t)

    def _log_app_versions(self):
        """Log application versions at startup

        Logs versions of jupyterhub and singleuser-server base versions (jupyterlab, jupyter_server, notebook)
        """
        self.log.info(f"Starting jupyterhub single-user server version {__version__}")

        # don't log these package versions
        seen = {"jupyterhub", "traitlets", "jupyter_core", "builtins"}

        for cls in self.__class__.mro():
            module_name = cls.__module__.partition(".")[0]
            if module_name not in seen:
                seen.add(module_name)
                try:
                    mod = import_module(module_name)
                    mod_version = getattr(mod, "__version__")
                except Exception:
                    mod_version = ""
                self.log.info(
                    f"Extending {cls.__module__}.{cls.__name__} from {module_name} {mod_version}"
                )

    # load test extension, if we're testing
    def init_server_extension_config(self):
        """
        Overloads a method in classic notebook server's NotebookApp class
        (notebook < 7) to conditionally enable a jupyterhub test extension.

        ref: https://github.com/jupyter/notebook/blob/v6.5.2/notebook/notebookapp.py#L1982
        """
        super().init_server_extension_config()
        if os.getenv("JUPYTERHUB_SINGLEUSER_TEST_EXTENSION") == "1":
            self.log.warning("Enabling jupyterhub test extension, classic edition")
            self.nbserver_extensions["jupyterhub.tests.extension"] = True

    def find_server_extensions(self):
        """
        Overloads a method in jupyter_server's ServerApp class (lab or notebook
        >=7) to conditionally enable a jupyterhub test extension.

        ref: https://github.com/jupyter-server/jupyter_server/blob/v2.2.1/jupyter_server/serverapp.py#L2238
        """
        super().find_server_extensions()
        if os.getenv("JUPYTERHUB_SINGLEUSER_TEST_EXTENSION") == "1":
            self.log.warning("Enabling jupyterhub test extension")
            self.jpserver_extensions["jupyterhub.tests.extension"] = True

    def initialize(self, argv=None):
        if self.disable_user_config:
            _disable_user_config(self)
        # disable trash by default
        # this can be re-enabled by config
        self.config.FileContentsManager.delete_to_trash = False
        # load default-url env at higher priority than `@default`,
        # which may have their own _defaults_ which should not override explicit default_url config
        # via e.g. c.Spawner.default_url. Seen in jupyterlab's SingleUserLabApp.
        default_url = os.environ.get("JUPYTERHUB_DEFAULT_URL")
        if default_url:
            self.config[self.__class__.__name__].default_url = default_url
        self._log_app_versions()
        # call our init_ioloop very early
        # jupyter-server calls it too late, notebook doesn't define it yet
        # only called in jupyter-server >= 1.9
        self.init_ioloop()
        super().initialize(argv)
        self.patch_templates()

    def init_ioloop(self):
        """init_ioloop added in jupyter-server 1.9"""
        # avoid deprecated access to current event loop
        if getattr(self, "io_loop", None) is None:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                # not running, make our own loop
                self.io_loop = ioloop.IOLoop(make_current=False)
            else:
                # running, use IOLoop.current
                self.io_loop = ioloop.IOLoop.current()

        # Make our event loop the 'current' event loop.
        # FIXME: this shouldn't be necessary, but it is.
        # notebookapp (<=6.4, at least), and
        # jupyter-server (<=1.17.0, at least) still need the 'current' event loop to be defined
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.io_loop.make_current()

    def init_httpserver(self):
        self.io_loop.run_sync(super().init_httpserver)

    def start(self):
        self.log.info("Starting jupyterhub-singleuser server version %s", __version__)
        # start by hitting Hub to check version
        self.io_loop.run_sync(self.check_hub_version)
        self.io_loop.add_callback(self.keep_activity_updated)
        super().start()

    def init_hub_auth(self):
        api_token = None
        if os.getenv('JPY_API_TOKEN'):
            # Deprecated env variable (as of 0.7.2)
            api_token = os.environ['JPY_API_TOKEN']
        if os.getenv('JUPYTERHUB_API_TOKEN'):
            api_token = os.environ['JUPYTERHUB_API_TOKEN']

        if not api_token:
            self.exit(
                "JUPYTERHUB_API_TOKEN env is required to run jupyterhub-singleuser. Did you launch it manually?"
            )
        self.hub_auth = HubOAuth(
            parent=self,
            api_token=api_token,
            api_url=self.hub_api_url,
            hub_prefix=self.hub_prefix,
            base_url=self.base_url,
            keyfile=self.keyfile,
            certfile=self.certfile,
            client_ca=self.client_ca,
        )
        self.hub_host = self.hub_auth.hub_host
        # smoke check
        if not self.hub_auth.oauth_client_id:
            raise ValueError("Missing OAuth client ID")

    def init_webapp(self):
        # load the hub-related settings into the tornado settings dict
        self.init_hub_auth()
        s = self.tornado_settings
        # if the user has configured a log function in the tornado settings, do not override it
        s.setdefault('log_function', log_request)
        s['user'] = self.user
        s['group'] = self.group
        s['hub_prefix'] = self.hub_prefix
        s['hub_host'] = self.hub_host
        s['hub_auth'] = self.hub_auth
        s['page_config_hook'] = self.page_config_hook
        csp_report_uri = s['csp_report_uri'] = self.hub_host + url_path_join(
            self.hub_prefix, 'security/csp-report'
        )
        headers = s.setdefault('headers', {})
        headers['X-JupyterHub-Version'] = __version__
        # set default CSP to prevent iframe embedding across jupyterhub components
        headers.setdefault(
            'Content-Security-Policy',
            ';'.join(["frame-ancestors 'none'", "report-uri " + csp_report_uri]),
        )
        super().init_webapp()

        # add OAuth callback
        self.web_app.add_handlers(
            r".*$",
            [
                (
                    urlparse(self.hub_auth.oauth_redirect_uri).path,
                    self.oauth_callback_handler_class,
                )
            ],
        )

        # apply X-JupyterHub-Version to *all* request handlers (even redirects)
        self.patch_default_headers()

    def page_config_hook(self, handler, page_config):
        """JupyterLab page config hook

        Adds JupyterHub info to page config.

        Places the JupyterHub API token in PageConfig.token.

        Only has effect on jupyterlab_server >=2.9
        """
        page_config["token"] = self.hub_auth.get_token(handler) or ""
        return page_config

    def patch_default_headers(self):
        if hasattr(RequestHandler, '_orig_set_default_headers'):
            return
        RequestHandler._orig_set_default_headers = RequestHandler.set_default_headers

        def set_jupyterhub_header(self):
            self._orig_set_default_headers()
            self.set_header('X-JupyterHub-Version', __version__)

        RequestHandler.set_default_headers = set_jupyterhub_header

    def patch_templates(self):
        """Patch page templates to add Hub-related buttons"""

        self.jinja_template_vars['logo_url'] = self.hub_host + url_path_join(
            self.hub_prefix, 'logo'
        )
        self.jinja_template_vars['hub_host'] = self.hub_host
        self.jinja_template_vars['hub_prefix'] = self.hub_prefix
        self.jinja_template_vars['hub_control_panel_url'] = (
            self.hub_host + url_path_join(self.hub_prefix, 'home')
        )

        settings = self.web_app.settings
        # patch classic notebook jinja env
        jinja_envs = []
        if 'jinja2_env' in settings:
            # default jinja env (should we do this on jupyter-server, or only notebook?)
            jinja_envs.append(settings['jinja2_env'])
        for ext_name in ("notebook", "nbclassic"):
            env_name = f"{ext_name}_jinja2_env"
            if env_name in settings:
                # when running with jupyter-server, classic notebook (nbclassic server extension or notebook v7)
                # gets its own jinja env, which needs the same patch
                jinja_envs.append(settings[env_name])

        # patch jinja env loading to get modified template, only for base page.html
        template_dir = Path(__file__).resolve().parent.joinpath("templates")
        with template_dir.joinpath("page.html").open() as f:
            page_template = f.read()

        def get_page(name):
            if name == 'page.html':
                return page_template

        for jinja_env in jinja_envs:
            jinja_env.loader = ChoiceLoader(
                [FunctionLoader(get_page), jinja_env.loader]
            )

    def load_server_extensions(self):
        # Loading LabApp sets $JUPYTERHUB_API_TOKEN on load, which is incorrect
        r = super().load_server_extensions()
        # clear the token in PageConfig at this step
        # so that cookie auth is used
        # FIXME: in the future,
        # it would probably make sense to set page_config.token to the token
        # from the current request.
        if 'page_config_data' in self.web_app.settings:
            self.web_app.settings['page_config_data']['token'] = ''
        return r


def detect_base_package(App):
    """Detect the base package for an App class

    Will return 'notebook' or 'jupyter_server'
    based on which package App subclasses from.

    Will return None if neither is identified (e.g. fork package, or duck-typing).
    """
    # guess notebook or jupyter_server based on App class inheritance
    for cls in App.mro():
        pkg = cls.__module__.split(".", 1)[0]
        if pkg in {"notebook", "jupyter_server"}:
            return pkg
    return None


def _nice_cls_repr(cls):
    """Nice repr of classes, e.g. 'module.submod.Class'

    Also accepts tuples of classes
    """
    return f"{cls.__module__}.{cls.__name__}"


def patch_base_handler(BaseHandler, log=None):
    """Patch HubAuthenticated into a base handler class

    so anything inheriting from BaseHandler uses Hub authentication.
    This works *even after* subclasses have imported and inherited from BaseHandler.

    .. versionadded: 1.5
        Made available as an importable utility
    """
    if log is None:
        log = logging.getLogger()

    if HubAuthenticatedHandler not in BaseHandler.__bases__:
        new_bases = (HubAuthenticatedHandler,) + BaseHandler.__bases__
        log.info(
            "Patching auth into {mod}.{name}({old_bases}) -> {name}({new_bases})".format(
                mod=BaseHandler.__module__,
                name=BaseHandler.__name__,
                old_bases=', '.join(
                    _nice_cls_repr(cls) for cls in BaseHandler.__bases__
                ),
                new_bases=', '.join(_nice_cls_repr(cls) for cls in new_bases),
            )
        )
        BaseHandler.__bases__ = new_bases
        # We've now inserted our class as a parent of BaseHandler,
        # but we also need to ensure BaseHandler *itself* doesn't
        # override the public tornado API methods we have inserted.
        # If they are defined in BaseHandler, explicitly replace them with our methods.
        for name in ("get_current_user", "get_login_url"):
            if name in BaseHandler.__dict__:
                log.debug(
                    f"Overriding {BaseHandler}.{name} with HubAuthenticatedHandler.{name}"
                )
                method = getattr(HubAuthenticatedHandler, name)
                setattr(BaseHandler, name, method)
    return BaseHandler


def _patch_app_base_handlers(app):
    """Patch Hub Authentication into the base handlers of an app

    Patches HubAuthenticatedHandler into:

    - App.base_handler_class (if defined)
    - jupyter_server's JupyterHandler (if already imported)
    - notebook's IPythonHandler (if already imported)
    """
    BaseHandler = app_base_handler = getattr(app, "base_handler_class", None)

    base_handlers = []
    if BaseHandler is not None:
        base_handlers.append(BaseHandler)

    # patch jupyter_server and notebook handlers if they have been imported
    for base_handler_name in [
        "jupyter_server.base.handlers.JupyterHandler",
        "notebook.base.handlers.IPythonHandler",
    ]:
        modname, _ = base_handler_name.rsplit(".", 1)
        if modname in sys.modules:
            root_mod = modname.partition(".")[0]
            if root_mod == "notebook":
                import notebook

                if int(notebook.__version__.partition(".")[0]) >= 7:
                    # notebook 7 is a server extension,
                    # it doesn't have IPythonHandler anymore
                    continue
            base_handlers.append(import_item(base_handler_name))

    if not base_handlers:
        pkg = detect_base_package(app.__class__)
        if pkg == "jupyter_server":
            BaseHandler = import_item("jupyter_server.base.handlers.JupyterHandler")
        elif pkg == "notebook":
            BaseHandler = import_item("notebook.base.handlers.IPythonHandler")
        else:
            raise ValueError(
                f"{app.__class__.__name__}.base_handler_class must be defined"
            )
        base_handlers.append(BaseHandler)

    # patch-in HubAuthenticatedHandler to base handler classes
    for BaseHandler in base_handlers:
        patch_base_handler(BaseHandler)

    # return the first entry
    return base_handlers[0]


def make_singleuser_app(App):
    """Make and return a singleuser notebook app

    given existing notebook or jupyter_server Application classes,
    mix-in jupyterhub auth.

    Instances of App must have the following attributes defining classes:

    - .login_handler_class
    - .logout_handler_class
    - .base_handler_class (only required if not a subclass of the default app
      in jupyter_server or notebook)

    App should be a subclass of `notebook.notebookapp.NotebookApp`
    or `jupyter_server.serverapp.ServerApp`.
    """

    empty_parent_app = App()
    log = empty_parent_app.log

    # detect base handler classes
    if not getattr(empty_parent_app, "login_handler_class", None) and hasattr(
        empty_parent_app, "identity_provider_class"
    ):
        # Jupyter Server 2 moves the login handler classes to the identity provider
        has_handlers = empty_parent_app.identity_provider_class(parent=empty_parent_app)
    else:
        # prior to Jupyter Server 2, the app itself had handler class config
        has_handlers = empty_parent_app
    LoginHandler = has_handlers.login_handler_class
    LogoutHandler = has_handlers.logout_handler_class
    BaseHandler = _patch_app_base_handlers(empty_parent_app)

    # create Handler classes from mixins + bases

    class JupyterHubLoginHandler(JupyterHubLoginHandlerMixin, LoginHandler):
        pass

    class JupyterHubLogoutHandler(JupyterHubLogoutHandlerMixin, LogoutHandler):
        pass

    class OAuthCallbackHandler(OAuthCallbackHandlerMixin, BaseHandler):
        pass

    # create merged aliases & flags
    merged_aliases = {}
    merged_aliases.update(empty_parent_app.aliases or {})
    merged_aliases.update(aliases)

    merged_flags = {}
    merged_flags.update(empty_parent_app.flags or {})
    merged_flags.update(flags)

    # create mixed-in App class, bringing it all together
    class SingleUserNotebookApp(SingleUserNotebookAppMixin, App):
        aliases = merged_aliases
        flags = merged_flags
        classes = empty_parent_app.classes + [HubOAuth]

        login_handler_class = JupyterHubLoginHandler
        logout_handler_class = JupyterHubLogoutHandler
        oauth_callback_handler_class = OAuthCallbackHandler

        def initialize(self, *args, **kwargs):
            result = super().initialize(*args, **kwargs)
            # run patch again after initialize, so extensions have already been loaded
            # probably a no-op most of the time
            _patch_app_base_handlers(self)
            return result

    return SingleUserNotebookApp
