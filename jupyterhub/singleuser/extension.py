"""
Integrate JupyterHub auth with Jupyter Server as a Server Extension

Instead of earlier versions, implemented via subclassing jupyter-notebook's NotebookApp.
This code runs only in each user's Jupyter Server process.

Jupyter Server 2 provides two new APIs:

- IdentityProvider, which authenticates the user making the request
- Authorizer, which determines whether an authenticated user is authorized to take a particular action

This Extension implements both for resolving permissions with JupyterHub scopes.
By default, in JupyterHub we only _authenticate_ users with sufficient `access:servers` permissions,
therefore the JupyterHub Authorizer allows any authenticated user to take any action,
but custom deployments may refine these permission to enable e.g. read-only access.

- Jupyter Server extension documentation: https://jupyter-server.readthedocs.io/en/latest/developers/extensions.html
- Jupyter Server authentication API documentation: https://jupyter-server.readthedocs.io/en/latest/operators/security.html

Requires Jupyter Server 2.0, which in turn requires Python 3.7.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import timezone
from functools import wraps
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

from jupyter_server.auth import Authorizer, IdentityProvider, User
from jupyter_server.auth.logout import LogoutHandler
from jupyter_server.extension.application import ExtensionApp
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import url_concat
from tornado.web import HTTPError
from traitlets import Any, Bool, Instance, Integer, Unicode, default

from jupyterhub._version import __version__, _check_version
from jupyterhub.log import log_request
from jupyterhub.services.auth import HubOAuth, HubOAuthCallbackHandler
from jupyterhub.utils import (
    _bool_env,
    exponential_backoff,
    isoformat,
    make_ssl_context,
    url_path_join,
)

from ._disable_user_config import _disable_user_config

SINGLEUSER_TEMPLATES_DIR = str(Path(__file__).parent.resolve().joinpath("templates"))


def _exclude_home(path_list):
    """Filter out any entries in a path list that are in my home directory.

    Used to disable per-user configuration.
    """
    home = os.path.expanduser('~/')
    for p in path_list:
        if not p.startswith(home):
            yield p


class JupyterHubLogoutHandler(LogoutHandler):
    def get(self):
        hub_auth = self.identity_provider.hub_auth
        # clear token stored in single-user cookie (set by hub_auth)
        hub_auth.clear_cookie(self)
        # redirect to hub to begin logging out of JupyterHub itself
        self.redirect(hub_auth.hub_host + url_path_join(hub_auth.hub_prefix, "logout"))


class JupyterHubUser(User):
    """Subclass jupyter_server User to store JupyterHub user info"""

    # not dataclass fields,
    # so these aren't returned in the identity model via the REST API.
    # The could be, though!
    hub_user: dict

    def __init__(self, hub_user):
        self.hub_user = hub_user
        super().__init__(username=self.hub_user["name"])


class JupyterHubOAuthCallbackHandler(HubOAuthCallbackHandler):
    """Callback handler for completing OAuth with JupyterHub"""

    def initialize(self, hub_auth):
        self.hub_auth = hub_auth


class JupyterHubIdentityProvider(IdentityProvider):
    """Identity Provider for JupyterHub OAuth

    Replacement for JupyterHub's HubAuthenticated mixin
    """

    logout_handler_class = JupyterHubLogoutHandler

    hub_auth = Instance(HubOAuth)

    @property
    def token(self):
        return self.hub_auth.api_token

    token_generated = False

    @default("hub_auth")
    def _default_hub_auth(self):
        # HubAuth gets most of its config from the environment
        return HubOAuth(parent=self)

    def _patch_xsrf(self, handler):
        self.hub_auth._patch_xsrf(handler)

    def _patch_get_login_url(self, handler):
        original_get_login_url = handler.get_login_url

        _hub_login_url = None

        def get_login_url():
            """Return the Hub's login URL, to begin login redirect"""
            nonlocal _hub_login_url
            if _hub_login_url is not None:
                # cached value, don't call this more than once per handler
                return _hub_login_url
            # temporary override at settings level,
            # to allow any subclass overrides of get_login_url to preserve their effect;
            # for example, APIHandler raises 403 to prevent redirects
            with mock.patch.dict(
                handler.application.settings, {"login_url": self.hub_auth.login_url}
            ):
                login_url = original_get_login_url()
            self.log.debug("Redirecting to login url: %s", login_url)
            # add state argument to OAuth url
            # must do this _after_ allowing get_login_url to raise
            # so we don't set unused cookies
            state = self.hub_auth.set_state_cookie(
                handler, next_url=handler.request.uri
            )
            _hub_login_url = url_concat(login_url, {'state': state})
            return _hub_login_url

        handler.get_login_url = get_login_url

    async def get_user(self, handler):
        if hasattr(handler, "_jupyterhub_user"):
            return handler._jupyterhub_user
        self._patch_get_login_url(handler)
        self._patch_xsrf(handler)
        user = await self.hub_auth.get_user(handler, sync=False)
        if user is None:
            handler._jupyterhub_user = None
            return None
        # check access scopes - don't allow even authenticated
        # users with no access to this service past this stage.
        # this is technically the Authorizer's job (below),
        # but the IdentityProvider is the only protection on handlers
        # decorated only with tornado's `@web.authenticated`,
        # that haven't adopted the Jupyter Server 2 authorization decorators.
        # so we check access scopes here, to be safe.
        self.log.debug(
            f"Checking user {user['name']} with scopes {user['scopes']} against {self.hub_auth.access_scopes}"
        )
        scopes = self.hub_auth.check_scopes(self.hub_auth.access_scopes, user)
        if scopes:
            self.log.debug(f"Allowing user {user['name']} with scopes {scopes}")
        else:
            self.log.warning(f"Not allowing user {user['name']}")

            # User is authenticated, but not authorized.
            # Override redirect so if/when tornado @web.authenticated
            # tries to redirect to login URL, 403 will be raised instead.
            # This is not the best, but avoids problems that can be caused
            # when get_current_user is allowed to raise,
            # and avoids redirect loops for users who are logged it,
            # but not allowed to access this resource.
            def raise_on_redirect(*args, **kwargs):
                raise HTTPError(403, "{kind} {name} is not allowed.".format(**user))

            handler.redirect = raise_on_redirect

            return None
        handler._jupyterhub_user = JupyterHubUser(user)
        self.hub_auth._persist_url_token_if_set(handler)
        return handler._jupyterhub_user

    def get_handlers(self):
        """Register our OAuth callback handler"""
        return [
            ("/logout", self.logout_handler_class),
            (
                "/oauth_callback",
                JupyterHubOAuthCallbackHandler,
                {"hub_auth": self.hub_auth},
            ),
        ]

    def validate_security(self, app, ssl_options=None):
        """Prevent warnings about security from base class"""
        return

    def page_config_hook(self, handler, page_config):
        """JupyterLab page config hook

        Adds JupyterHub info to page config.

        Places the JupyterHub API token in PageConfig.token.

        Only has effect on jupyterlab_server >=2.9
        """
        user = handler.current_user
        # originally implemented in jupyterlab's LabApp
        page_config["hubUser"] = user.name if user else ""
        page_config["hubPrefix"] = hub_prefix = self.hub_auth.hub_prefix
        page_config["hubHost"] = self.hub_auth.hub_host
        page_config["shareUrl"] = url_path_join(hub_prefix, "user-redirect")
        page_config["hubServerName"] = os.environ.get("JUPYTERHUB_SERVER_NAME", "")
        page_config["token"] = self.hub_auth.get_token(handler) or ""
        return page_config


class JupyterHubAuthorizer(Authorizer):
    """Authorizer that looks for permissions in JupyterHub scopes.

    Currently only checks the `access:servers` scope(s),
    which ought to be redundant with checks already in `JupyterHubIdentityProvider` for safety.
    """

    @property
    def hub_auth(self):
        return self.identity_provider.hub_auth

    def is_authorized(self, handler, user, action, resource):
        """
        Return whether the authenticated user has permission to perform `action` on `resource`.

        Currently: action and resource are ignored,
        and only the `access:servers` scope is checked.

        This method can be overridden (in combination with custom scopes) to implement granular permissions,
        such as read-only access or access to subsets of the server.
        """

        # This check for access scopes is redundant
        # with the IdentityProvider above,
        # but better to be redundant than allow unauthorized actions.
        # If we remove a redundant check,
        # it should be the one in the identity provider,
        # not this one.
        have_scopes = self.hub_auth.check_scopes(
            self.hub_auth.oauth_scopes, user.hub_user
        )
        self.log.debug(
            f"{user.username} has permissions {have_scopes} required to {action} on {resource}"
        )
        return bool(have_scopes)


def _fatal_errors(f):
    """Decorator to make errors fatal to the server app

    Ensures our extension is loaded or the server exits,
    rather than starting a server without jupyterhub auth enabled.
    """

    @wraps(f)
    def wrapped(self, *args, **kwargs):
        try:
            r = f(self, *args, **kwargs)
        except Exception:
            self.log.exception("Failed to load JupyterHubSingleUser server extension")
            self.exit(1)

    return wrapped


class JupyterHubSingleUser(ExtensionApp):
    """Jupyter Server extension entrypoint.

    Enables JupyterHub authentication
    and some JupyterHub-specific configuration from environment variables

    Server extensions are loaded before the rest of the server is set up
    """

    name = app_namespace = "jupyterhub-singleuser"
    version = __version__
    load_other_extensions = os.environ.get(
        "JUPYTERHUB_SINGLEUSER_LOAD_OTHER_EXTENSIONS", "1"
    ) not in {"", "0"}

    # Most of this is _copied_ from the SingleUserNotebookApp mixin,
    # which will be deprecated over time
    # (i.e. once we can _require_ jupyter server 2.0)

    # this is a _class_ attribute to deal with the lifecycle
    # of when it's loaded vs when it's checked
    disable_user_config = False

    hub_auth = Instance(HubOAuth)

    @default("hub_auth")
    def _default_hub_auth(self):
        # HubAuth gets most of its config from the environment
        return HubOAuth(parent=self)

    # create dynamic default http client,
    # configured with any relevant ssl config
    hub_http_client = Any()

    @default('hub_http_client')
    def _default_client(self):
        ssl_context = make_ssl_context(
            self.hub_auth.keyfile,
            self.hub_auth.certfile,
            cafile=self.hub_auth.client_ca,
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
                resp = await client.fetch(self.hub_auth.api_url)
            except Exception:
                self.log.exception(
                    "Failed to connect to my Hub at %s (attempt %i/%i). Is it running?",
                    self.hub_auth.api_url,
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
        last_activity = self.serverapp.web_app.last_activity()
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
        self.log.info(
            f"Starting jupyterhub single-user server extension version {__version__}"
        )

    @_fatal_errors
    def load_config_file(self):
        """Load JupyterHub singleuser config from the environment"""
        self._log_app_versions()
        if not os.environ.get('JUPYTERHUB_SERVICE_URL'):
            raise KeyError("Missing required environment $JUPYTERHUB_SERVICE_URL")

        cfg = self.config.ServerApp
        cfg.identity_provider_class = JupyterHubIdentityProvider

        # disable some single-user features
        cfg.allow_remote_access = True
        cfg.open_browser = False
        cfg.trust_xheaders = True
        cfg.quit_button = False
        cfg.port_retries = 0
        cfg.answer_yes = True
        self.config.FileContentsManager.delete_to_trash = False

        # load Spawner.notebook_dir configuration, if given
        root_dir = os.getenv("JUPYTERHUB_ROOT_DIR", None)
        if root_dir:
            cfg.root_dir = os.path.expanduser(root_dir)

        # load http server config from environment
        url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
        if url.port:
            cfg.port = url.port
        elif url.scheme == 'http':
            cfg.port = 80
        elif url.scheme == 'https':
            cfg.port = 443
        if url.hostname:
            cfg.ip = url.hostname
        else:
            cfg.ip = "127.0.0.1"

        cfg.base_url = os.environ.get('JUPYTERHUB_SERVICE_PREFIX') or '/'

        # load default_url at all kinds of priority,
        # to make sure it has the desired effect
        cfg.default_url = self.default_url = self.get_default_url()

        # load internal SSL configuration
        cfg.keyfile = os.environ.get('JUPYTERHUB_SSL_KEYFILE') or ''
        cfg.certfile = os.environ.get('JUPYTERHUB_SSL_CERTFILE') or ''
        cfg.client_ca = os.environ.get('JUPYTERHUB_SSL_CLIENT_CA') or ''
        if cfg.certfile:
            self.serverapp.log.info(f"Using SSL cert {cfg.certfile}")

        # Jupyter Server default: config files have higher priority than extensions,
        # by:
        # 1. load config files and CLI
        # 2. load extension config
        # 3. merge file config into extension config

        # we invert that by merging our extension config into server config before
        # they get merged the other way
        # this way config from this extension should always have highest priority

        # but this also puts our config above _CLI_ options,
        # and CLI should come before env,
        # so merge that into _our_ config before loading
        if self.serverapp.cli_config:
            for cls_name, cls_config in self.serverapp.cli_config.items():
                if cls_name in self.config:
                    self.config[cls_name].merge(cls_config)

        self.serverapp.update_config(self.config)

        # config below here has _lower_ priority than user config
        self.config.NotebookApp.extra_template_paths.append(SINGLEUSER_TEMPLATES_DIR)

    @default("default_url")
    def get_default_url(self):
        # 1. explicit via _user_ config (?)
        if 'default_url' in self.serverapp.config.ServerApp:
            default_url = self.serverapp.config.ServerApp.default_url
            self.log.info(f"Using default url from user config: {default_url}")
            return default_url

        # 2. explicit via JupyterHub admin config (c.Spawner.default_url)
        default_url = os.environ.get("JUPYTERHUB_DEFAULT_URL")
        if default_url:
            self.log.info(
                f"Using default url from environment $JUPYTERHUB_DEFAULT_URL: {default_url}"
            )
            return default_url

        # 3. look for known UI extensions
        # priority:
        # 1. lab
        # 2. nbclassic
        # 3. retro

        extension_points = self.serverapp.extension_manager.extension_points
        for name in ["lab", "retro", "nbclassic"]:
            if name in extension_points:
                default_url = extension_points[name].app.default_url
                if default_url and default_url != "/":
                    self.log.info(
                        f"Using default url from server extension {name}: {default_url}"
                    )
                    return default_url

        self.log.warning(
            "No default url found in config or known extensions, searching other extensions for default_url"
        )
        # 3. _any_ UI extension
        # 2. discover other extensions
        for (
            name,
            extension_point,
        ) in extension_points.items():
            app = extension_point.app
            if app is self or not app:
                continue
            default_url = app.default_url
            if default_url and default_url != "/":
                self.log.info(
                    f"Using default url from server extension {name}: {default_url}"
                )
                return default_url

        self.log.warning(
            "Found no extension with a default URL, UI will likely be unavailable"
        )
        return "/"

    def initialize_templates(self):
        """Patch classic-noteboook page templates to add Hub-related buttons"""

        app = self.serverapp

        jinja_template_vars = app.jinja_template_vars

        # override template vars
        jinja_template_vars['logo_url'] = self.hub_auth.hub_host + url_path_join(
            self.hub_auth.hub_prefix, 'logo'
        )
        jinja_template_vars['hub_control_panel_url'] = (
            self.hub_auth.hub_host + url_path_join(self.hub_auth.hub_prefix, 'home')
        )

    _activity_task = None

    @_fatal_errors
    def initialize(self, args=None):
        # initialize takes place after
        # 1. config has been loaded
        # 2. Configurables instantiated
        # 3. serverapp.web_app set up

        super().initialize()
        app = self.serverapp
        app.web_app.settings["page_config_hook"] = (
            app.identity_provider.page_config_hook
        )
        # disable xsrf_cookie checks by Tornado, which run too early
        # checks in Jupyter Server are unconditional
        app.web_app.settings["xsrf_cookies"] = False
        # if the user has configured a log function in the tornado settings, do not override it
        if not 'log_function' in app.config.ServerApp.get('tornado_settings', {}):
            app.web_app.settings["log_function"] = log_request
        # add jupyterhub version header
        headers = app.web_app.settings.setdefault("headers", {})
        headers["X-JupyterHub-Version"] = __version__

        # check jupyterhub version
        app.io_loop.run_sync(self.check_hub_version)

        # set default CSP to prevent iframe embedding across jupyterhub components
        headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")

        async def _start_activity():
            self._activity_task = asyncio.ensure_future(self.keep_activity_updated())

        app.io_loop.run_sync(_start_activity)

    async def stop_extension(self):
        if self._activity_task:
            self._activity_task.cancel()

    disable_user_config = Bool()

    @default("disable_user_config")
    def _defaut_disable_user_config(self):
        return _bool_env("JUPYTERHUB_DISABLE_USER_CONFIG")

    @classmethod
    def make_serverapp(cls, **kwargs):
        """Instantiate the ServerApp

        Override to customize the ServerApp before it loads any configuration
        """
        serverapp = super().make_serverapp(**kwargs)
        if _bool_env("JUPYTERHUB_DISABLE_USER_CONFIG"):
            # disable user-controllable config
            _disable_user_config(serverapp)

        if _bool_env("JUPYTERHUB_SINGLEUSER_TEST_EXTENSION"):
            serverapp.log.warning("Enabling jupyterhub test extension")
            serverapp.jpserver_extensions["jupyterhub.tests.extension"] = True

        return serverapp


main = JupyterHubSingleUser.launch_instance

if __name__ == "__main__":
    main()
