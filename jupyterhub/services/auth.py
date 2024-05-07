"""Authenticating services with JupyterHub.

Tokens are sent to the Hub for verification.
The Hub replies with a JSON model describing the authenticated user.

This contains two levels of authentication:

- :class:`HubOAuth` - Use OAuth 2 to authenticate browsers with the Hub.
  This should be used for any service that should respond to browser requests
  (i.e. most services).

- :class:`HubAuth` - token-only authentication, for a service that only need to handle token-authenticated API requests

The ``Auth`` classes (:class:`HubAuth`, :class:`HubOAuth`)
can be used in any application, even outside tornado.
They contain reference implementations of talking to the Hub API
to resolve a token to a user.

The ``Authenticated`` classes (:class:`HubAuthenticated`, :class:`HubOAuthenticated`)
are mixins for tornado handlers that should authenticate with the Hub.

If you are using OAuth, you will also need to register an oauth callback handler to complete the oauth process.
A tornado implementation is provided in :class:`HubOAuthCallbackHandler`.

"""

import asyncio
import hashlib
import json
import os
import random
import re
import secrets
import socket
import string
import time
import warnings
from functools import partial
from http import HTTPStatus
from unittest import mock
from urllib.parse import urlencode, urlparse

from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import url_concat
from tornado.log import app_log
from tornado.web import HTTPError, RequestHandler
from tornado.websocket import WebSocketHandler
from traitlets import (
    Any,
    Bool,
    Dict,
    Instance,
    Integer,
    Set,
    Unicode,
    default,
    observe,
    validate,
)
from traitlets.config import SingletonConfigurable

from .._xsrf_utils import (
    _anonymous_xsrf_id,
    _needs_check_xsrf,
    _set_xsrf_cookie,
    check_xsrf_cookie,
    get_xsrf_token,
)
from ..scopes import _intersect_expanded_scopes
from ..utils import _bool_env, get_browser_protocol, url_path_join


def check_scopes(required_scopes, scopes):
    """Check that required_scope(s) are in scopes

    Returns the subset of scopes matching required_scopes,
    which is truthy if any scopes match any required scopes.

    Correctly resolves scope filters *except* for groups -> user,
    e.g. require: access:server!user=x, have: access:server!group=y
    will not grant access to user x even if user x is in group y.

    Parameters
    ----------

    required_scopes: set
        The set of scopes required.
    scopes: set
        The set (or list) of scopes to check against required_scopes

    Returns
    -------
    relevant_scopes: set
        The set of scopes in required_scopes that are present in scopes,
        which is truthy if any required scopes are present,
        and falsy otherwise.
    """
    if isinstance(required_scopes, str):
        required_scopes = {required_scopes}

    intersection = _intersect_expanded_scopes(required_scopes, scopes)
    # re-intersect with required_scopes in case the intersection
    # applies stricter filters than required_scopes declares
    # e.g. required_scopes = {'read:users'} and intersection has only {'read:users!user=x'}
    return set(required_scopes) & intersection


class _ExpiringDict(dict):
    """Dict-like cache for Hub API requests

    Values will expire after max_age seconds.

    A monotonic timer is used (time.monotonic).

    A max_age of 0 means cache forever.
    """

    max_age = 0
    purge_interval = 0

    def __init__(self, max_age=0, purge_interval="max_age"):
        self.max_age = max_age
        if purge_interval == "max_age":
            # default behavior: use max_age
            purge_interval = max_age
        self.purge_interval = purge_interval
        self.timestamps = {}
        self.values = {}
        self._last_purge = time.monotonic()

    def __len__(self):
        return len(self.values)

    def __setitem__(self, key, value):
        """Store key and record timestamp"""
        self._maybe_purge()
        self.timestamps[key] = time.monotonic()
        self.values[key] = value

    def __repr__(self):
        """include values and timestamps in repr"""
        now = time.monotonic()
        return repr(
            {
                key: '{value} (age={age:.0f}s)'.format(
                    value=repr(value)[:16] + '...', age=now - self.timestamps[key]
                )
                for key, value in self.values.items()
            }
        )

    def _check_age(self, key):
        """Check timestamp for a key"""
        if key not in self.values:
            # not registered, nothing to do
            return
        now = time.monotonic()
        timestamp = self.timestamps[key]
        if self.max_age > 0 and timestamp + self.max_age < now:
            self.values.pop(key)
            self.timestamps.pop(key)
        self._maybe_purge()

    def __contains__(self, key):
        """dict check for `key in dict`"""
        self._check_age(key)
        return key in self.values

    def __getitem__(self, key):
        """Check age before returning value"""
        self._check_age(key)
        return self.values[key]

    def __delitem__(self, key):
        del self.values[key]
        del self.timestamps[key]

    def get(self, key, default=None):
        """dict-like get"""
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default="_raise"):
        """Remove and return an item"""
        if key in self:
            value = self.values.pop(key)
            del self.timestamps[key]
            return value
        else:
            if default == "_raise":
                raise KeyError(key)
            else:
                return default

    def clear(self):
        """Clear the cache"""
        self.values.clear()
        self.timestamps.clear()
        self._last_purge = time.monotonic()

    # extended methods
    def _maybe_purge(self):
        """purge expired values _if_ it's been purge_interval since the last purge

        Called on every get/set, to keep the expired values clear.
        """
        if not self.purge_interval > 0:
            return
        now = time.monotonic()
        if self._last_purge < (now - self.purge_interval):
            self.purge_expired()

    def purge_expired(self):
        """Purge all expired values"""
        if not self.max_age > 0:
            return
        now = self._last_purge = time.monotonic()
        cutoff = now - self.max_age
        for key in list(self.timestamps):
            timestamp = self.timestamps[key]
            if timestamp < cutoff:
                del self[key]


class HubAuth(SingletonConfigurable):
    """A class for authenticating with JupyterHub

    This can be used by any application.

    Use this base class only for direct, token-authenticated applications
    (web APIs).
    For applications that support direct visits from browsers,
    use HubOAuth to enable OAuth redirect-based authentication.


    If using tornado, use via :class:`HubAuthenticated` mixin.
    If using manually, use the ``.user_for_token(token_value)`` method
    to identify the user owning a given token.

    The following config must be set:

    - api_token (token for authenticating with JupyterHub API),
      fetched from the JUPYTERHUB_API_TOKEN env by default.

    The following config MAY be set:

    - api_url: the base URL of the Hub's internal API,
      fetched from JUPYTERHUB_API_URL by default.
    - cookie_cache_max_age: the number of seconds responses
      from the Hub should be cached.
    """

    hub_host = Unicode(
        '',
        help="""The public host of JupyterHub

        Only used if JupyterHub is spreading servers across subdomains.
        """,
    ).tag(config=True)

    @default('hub_host')
    def _default_hub_host(self):
        return os.getenv('JUPYTERHUB_HOST', '')

    base_url = Unicode(
        os.getenv('JUPYTERHUB_SERVICE_PREFIX') or '/',
        help="""The base URL prefix of this application

        e.g. /services/service-name/ or /user/name/

        Default: get from JUPYTERHUB_SERVICE_PREFIX
        """,
    ).tag(config=True)

    @validate('base_url')
    def _add_slash(self, proposal):
        """Ensure base_url starts and ends with /"""
        value = proposal['value']
        if not value.startswith('/'):
            value = '/' + value
        if not value.endswith('/'):
            value = value + '/'
        return value

    # where is the hub
    api_url = Unicode(
        os.getenv('JUPYTERHUB_API_URL') or 'http://127.0.0.1:8081/hub/api',
        help="""The base API URL of the Hub.

        Typically `http://hub-ip:hub-port/hub/api`
        Default: $JUPYTERHUB_API_URL
        """,
    ).tag(config=True)

    @default('api_url')
    def _api_url(self):
        env_url = os.getenv('JUPYTERHUB_API_URL')
        if env_url:
            return env_url
        else:
            return 'http://127.0.0.1:8081' + url_path_join(self.hub_prefix, 'api')

    api_token = Unicode(
        help="""API key for accessing Hub API.

        Default: $JUPYTERHUB_API_TOKEN

        Loaded from services configuration in jupyterhub_config.
        Will be auto-generated for hub-managed services.
        """,
    ).tag(config=True)

    @default("api_token")
    def _default_api_token(self):
        return os.getenv('JUPYTERHUB_API_TOKEN', '')

    hub_prefix = Unicode(
        '/hub/',
        help="""The URL prefix for the Hub itself.

        Typically /hub/
        Default: $JUPYTERHUB_BASE_URL
        """,
    ).tag(config=True)

    @default('hub_prefix')
    def _default_hub_prefix(self):
        return url_path_join(os.getenv('JUPYTERHUB_BASE_URL') or '/', 'hub') + '/'

    login_url = Unicode(
        '',
        help="""The login URL to use, if any.
        
        The base HubAuth class doesn't support login via URL,
        and will raise 403 on `@web.authenticated` requests without a valid token.
        
        An empty string here raises 403 errors instead of redirecting.
        
        HubOAuth will redirect to /hub/api/oauth2/authorize.
        """,
    ).tag(config=True)

    keyfile = Unicode(
        os.getenv('JUPYTERHUB_SSL_KEYFILE', ''),
        help="""The ssl key to use for requests

        Use with certfile
        """,
    ).tag(config=True)

    certfile = Unicode(
        os.getenv('JUPYTERHUB_SSL_CERTFILE', ''),
        help="""The ssl cert to use for requests

        Use with keyfile
        """,
    ).tag(config=True)

    client_ca = Unicode(
        os.getenv('JUPYTERHUB_SSL_CLIENT_CA', ''),
        help="""The ssl certificate authority to use to verify requests

        Use with keyfile and certfile
        """,
    ).tag(config=True)

    allow_token_in_url = Bool(
        _bool_env("JUPYTERHUB_ALLOW_TOKEN_IN_URL", default=False),
        help="""Allow requests to pages with ?token=... in the URL
        
        This allows starting a user session by sharing a URL with credentials,
        bypassing authentication with the Hub.
        
        If False, tokens in URLs will be ignored by the server,
        except on websocket requests.
        
        Has no effect on websocket requests,
        which can only reliably authenticate via token in the URL,
        as recommended by browser Websocket implementations.

        This will default to False in JupyterHub 5.

        .. versionadded:: 4.1

        .. versionchanged:: 5.0
            default changed to False
        """,
    ).tag(config=True)

    allow_websocket_cookie_auth = Bool(
        _bool_env("JUPYTERHUB_ALLOW_WEBSOCKET_COOKIE_AUTH", default=True),
        help="""Allow websocket requests with only cookie for authentication

        Cookie-authenticated websockets cannot be protected from other user servers unless per-user domains are used.
        Disabling cookie auth on websockets protects user servers from each other,
        but may break some user applications.
        Per-user domains eliminate the need to lock this down.
        
        JupyterLab 4.1.2 and Notebook 6.5.6, 7.1.0 will not work
        because they rely on cookie authentication without
        API or XSRF tokens.
        
        .. versionadded:: 4.1
        """,
    ).tag(config=True)

    cookie_options = Dict(
        help="""Additional options to pass when setting cookies.

        Can include things like `expires_days=None` for session-expiry
        or `secure=True` if served on HTTPS and default HTTPS discovery fails
        (e.g. behind some proxies).
        """
    ).tag(config=True)

    @default('cookie_options')
    def _default_cookie_options(self):
        # load default from env
        options_env = os.environ.get('JUPYTERHUB_COOKIE_OPTIONS')
        if options_env:
            return json.loads(options_env)
        else:
            return {}

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
        
        Set via $JUPYTERHUB_COOKIE_HOST_PREFIX_ENABLED
        """,
    ).tag(config=True)

    @default("cookie_host_prefix_enabled")
    def _default_cookie_host_prefix_enabled(self):
        return _bool_env("JUPYTERHUB_COOKIE_HOST_PREFIX_ENABLED")

    @property
    def cookie_path(self):
        """
        Path prefix on which to set cookies

        self.base_url, but '/' when cookie_host_prefix_enabled is True
        """
        if self.cookie_host_prefix_enabled:
            return "/"
        else:
            return self.base_url

    cookie_cache_max_age = Integer(help="DEPRECATED. Use cache_max_age")

    @observe('cookie_cache_max_age')
    def _deprecated_cookie_cache(self, change):
        warnings.warn(
            "cookie_cache_max_age is deprecated in JupyterHub 0.8. Use cache_max_age instead."
        )
        self.cache_max_age = change.new

    cache_max_age = Integer(
        300,
        help="""The maximum time (in seconds) to cache the Hub's responses for authentication.

        A larger value reduces load on the Hub and occasional response lag.
        A smaller value reduces propagation time of changes on the Hub (rare).

        Default: 300 (five minutes)
        """,
    ).tag(config=True)
    cache = Instance(_ExpiringDict, allow_none=False)

    @default('cache')
    def _default_cache(self):
        return _ExpiringDict(self.cache_max_age)

    @property
    def oauth_scopes(self):
        warnings.warn(
            "HubAuth.oauth_scopes is deprecated in JupyterHub 3.0. Use .access_scopes",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.access_scopes

    access_scopes = Set(
        Unicode(),
        help="""OAuth scopes to use for allowing access.

        Get from $JUPYTERHUB_OAUTH_ACCESS_SCOPES by default.
        """,
    ).tag(config=True)

    @default('access_scopes')
    def _default_scopes(self):
        env_scopes = os.getenv('JUPYTERHUB_OAUTH_ACCESS_SCOPES')
        if not env_scopes:
            # deprecated name (since 3.0)
            env_scopes = os.getenv('JUPYTERHUB_OAUTH_SCOPES')
        if env_scopes:
            return set(json.loads(env_scopes))
        # scopes not specified, use service name if defined
        service_name = os.getenv("JUPYTERHUB_SERVICE_NAME")
        if service_name:
            return {f'access:services!service={service_name}'}
        return set()

    _pool = Any(help="Thread pool for running async methods in the background")

    @default("_pool")
    def _new_pool(self):
        # start a single ThreadPool in the background
        from concurrent.futures import ThreadPoolExecutor

        pool = ThreadPoolExecutor(1)
        # create an event loop in the thread
        pool.submit(self._setup_asyncio_thread).result()
        return pool

    def _setup_asyncio_thread(self):
        """Create asyncio loop

        To be called from the background thread,
        so that any thread-local state is setup correctly
        """
        self._thread_loop = asyncio.new_event_loop()

    def _synchronize(self, async_f, *args, **kwargs):
        """Call an async method in our background thread"""
        future = self._pool.submit(
            lambda: self._thread_loop.run_until_complete(async_f(*args, **kwargs))
        )
        return future.result()

    def _call_coroutine(self, sync, async_f, *args, **kwargs):
        """Call an async coroutine function, either blocking or returning an awaitable

        if not sync: calls function directly, returning awaitable
        else: Block on a call in our background thread, return actual result
        """
        if not sync:
            return async_f(*args, **kwargs)
        else:
            return self._synchronize(async_f, *args, **kwargs)

    async def _check_hub_authorization(
        self, url, api_token, cache_key=None, use_cache=True
    ):
        """Identify a user with the Hub

        Args:
            url (str): The API URL to check the Hub for authorization
                       (e.g. http://127.0.0.1:8081/hub/api/user)
            cache_key (str): The key for checking the cache
            use_cache (bool): Specify use_cache=False to skip cached cookie values (default: True)

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.

        Raises an HTTPError if the request failed for a reason other than no such user.
        """
        if use_cache:
            if cache_key is None:
                raise ValueError("cache_key is required when using cache")
            # check for a cached reply, so we don't check with the Hub if we don't have to
            try:
                return self.cache[cache_key]
            except KeyError:
                app_log.debug("HubAuth cache miss: %s", cache_key)

        data = await self._api_request(
            'GET',
            url,
            headers={"Authorization": "token " + api_token},
            allow_403=True,
        )
        if data is None:
            app_log.warning("No Hub user identified for request")
        else:
            app_log.debug("Received request from Hub user %s", data)
        if use_cache:
            # cache result
            self.cache[cache_key] = data
        return data

    async def _api_request(self, method, url, **kwargs):
        """Make an API request"""
        allow_403 = kwargs.pop('allow_403', False)
        headers = kwargs.setdefault('headers', {})
        headers.setdefault('Authorization', f'token {self.api_token}')
        # translate requests args to tornado's
        if self.certfile:
            kwargs["client_cert"] = self.certfile
        if self.keyfile:
            kwargs["client_key"] = self.keyfile
        if self.client_ca:
            kwargs["ca_certs"] = self.client_ca
        req = HTTPRequest(
            url,
            method=method,
            **kwargs,
        )
        try:
            r = await AsyncHTTPClient().fetch(req, raise_error=False)
        except Exception as e:
            app_log.error("Error connecting to %s: %s", self.api_url, e)
            msg = f"Failed to connect to Hub API at {self.api_url!r}."
            msg += f"  Is the Hub accessible at this URL (from host: {socket.gethostname()})?"
            if '127.0.0.1' in self.api_url:
                msg += (
                    "  Make sure to set c.JupyterHub.hub_ip to an IP accessible to"
                    + " single-user servers if the servers are not on the same host as the Hub."
                )
            raise HTTPError(500, msg)

        data = None
        try:
            status = HTTPStatus(r.code)
        except ValueError:
            app_log.error(
                f"Unknown error checking authorization with JupyterHub: {r.code}"
            )
            app_log.error(r.body.decode("utf8", "replace"))

        response_text = r.body.decode("utf8", "replace")
        if status.value == 403 and allow_403:
            pass
        elif status.value == 403:
            app_log.error(
                "I don't have permission to check authorization with JupyterHub, my auth token may have expired: [%i] %s",
                status.value,
                status.description,
            )
            app_log.error(response_text)
            raise HTTPError(
                500, "Permission failure checking authorization, I may need a new token"
            )
        elif status.value >= 500:
            app_log.error(
                "Upstream failure verifying auth token: [%i] %s",
                status.value,
                status.description,
            )
            app_log.error(response_text)
            raise HTTPError(502, "Failed to check authorization (upstream problem)")
        elif status.value >= 400:
            app_log.warning(
                "Failed to check authorization: [%i] %s",
                status.value,
                status.description,
            )
            app_log.warning(response_text)
            msg = "Failed to check authorization"
            # pass on error from oauth failure
            try:
                response = json.loads(response_text)
                # prefer more specific 'error_description', fallback to 'error'
                description = response.get(
                    "error_description", response.get("error", "Unknown error")
                )
            except Exception:
                pass
            else:
                msg += ": " + description
            raise HTTPError(500, msg)
        else:
            data = json.loads(response_text)

        return data

    def user_for_cookie(self, encrypted_cookie, use_cache=True, session_id=''):
        """Deprecated and removed. Use HubOAuth to authenticate browsers."""
        raise RuntimeError(
            "Identifying users by shared cookie is removed in JupyterHub 2.0. Use OAuth tokens."
        )

    def user_for_token(self, token, use_cache=True, session_id='', *, sync=True):
        """Ask the Hub to identify the user for a given token.

        .. versionadded:: 2.4
            async support via `sync` argument.

        Args:
            token (str): the token
            use_cache (bool): Specify use_cache=False to skip cached cookie values (default: True)
            sync (bool): whether to block for the result or return an awaitable

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.

            The 'name' field contains the user's name.
        """
        return self._call_coroutine(
            sync,
            self._check_hub_authorization,
            url=url_path_join(
                self.api_url,
                "user",
            ),
            api_token=token,
            cache_key='token:{}:{}'.format(
                session_id,
                hashlib.sha256(token.encode("utf8", "replace")).hexdigest(),
            ),
            use_cache=use_cache,
        )

    auth_header_name = 'Authorization'
    auth_header_pat = re.compile(r'(?:token|bearer)\s+(.+)', re.IGNORECASE)

    def _get_token_url(self, handler):
        """Get the token from the URL

        Always run for websockets,
        otherwise run only if self.allow_token_in_url
        """
        fetch_mode = handler.request.headers.get("Sec-Fetch-Mode", "unspecified")
        if self.allow_token_in_url or fetch_mode == "websocket":
            return handler.get_argument("token", "")
        return ""

    def get_token(self, handler, in_cookie=True):
        """Get the token authenticating a request

        .. versionchanged:: 2.2
          in_cookie added.
          Previously, only URL params and header were considered.
          Pass `in_cookie=False` to preserve that behavior.

        - in URL parameters: ?token=<token>
        - in header: Authorization: token <token>
        - in cookie (stored after oauth), if in_cookie is True

        Args:
            handler (tornado.web.RequestHandler): the current request handler
        """
        user_token = self._get_token_url(handler)
        if not user_token:
            # get it from Authorization header
            m = self.auth_header_pat.match(
                handler.request.headers.get(self.auth_header_name, '')
            )
            if m:
                user_token = m.group(1)
        if not user_token and in_cookie:
            user_token = self._get_token_cookie(handler)
        return user_token

    def _get_token_cookie(self, handler):
        """Base class doesn't store tokens in cookies"""
        return None

    async def _get_user_cookie(self, handler):
        """Get the user model from a cookie"""
        # overridden in HubOAuth to store the access token after oauth
        return None

    def get_session_id(self, handler):
        """Get the jupyterhub session id

        from the jupyterhub-session-id cookie.

        Args:
            handler (tornado.web.RequestHandler): the current request handler
        """
        return handler.get_cookie('jupyterhub-session-id', '')

    def get_user(self, handler, *, sync=True):
        """Get the Hub user for a given tornado handler.

        Checks cookie with the Hub to identify the current user.

        .. versionadded:: 2.4
            async support via `sync` argument.

        Args:
            handler (tornado.web.RequestHandler): the current request handler
            sync (bool): whether to block for the result or return an awaitable

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.

            The 'name' field contains the user's name.
        """
        return self._call_coroutine(sync, self._get_user, handler)

    def _patch_xsrf(self, handler):
        """Overridden in HubOAuth

        HubAuth base class doesn't handle xsrf,
        which is only relevant for cookie-based auth
        """
        return

    async def _get_user(self, handler):
        # only allow this to be called once per handler
        # avoids issues if an error is raised,
        # since this may be called again when trying to render the error page
        if hasattr(handler, '_cached_hub_user'):
            return handler._cached_hub_user

        # patch XSRF checks, which will apply after user check
        self._patch_xsrf(handler)

        handler._cached_hub_user = user_model = None
        session_id = self.get_session_id(handler)

        # check token first, ignoring cookies
        # because some checks are different when a request
        # is token-authenticated (CORS-related)
        token = self.get_token(handler, in_cookie=False)
        if token:
            user_model = await self.user_for_token(
                token, session_id=session_id, sync=False
            )
            if user_model:
                handler._token_authenticated = True

        # no token, check cookie
        if user_model is None:
            user_model = await self._get_user_cookie(handler)

        # cache result
        handler._cached_hub_user = user_model
        if not user_model:
            app_log.debug("No user identified")
        return user_model

    def check_scopes(self, required_scopes, user):
        """Check whether the user has required scope(s)"""
        return check_scopes(required_scopes, set(user["scopes"]))

    def _persist_url_token_if_set(self, handler):
        """Persist ?token=... from URL in cookie if set

        for use in future cookie-authenticated requests.

        Allows initiating an authenticated session
        via /user/name/?token=abc...,
        otherwise only the initial request will be authenticated.

        No-op if no token URL parameter is given.
        """
        url_token = handler.get_argument('token', '')
        if not url_token:
            # no token to persist
            return
        # only do this if the token in the URL is the source of authentication
        if not getattr(handler, '_token_authenticated', False):
            return
        if not hasattr(self, 'set_cookie'):
            # only HubOAuth can persist cookies
            return
        fetch_mode = handler.request.headers.get("Sec-Fetch-Mode", "navigate")
        if isinstance(handler, WebSocketHandler) or fetch_mode != "navigate":
            # don't do this on websockets or non-navigate requests
            return
        self.log.info(
            "Storing token from url in cookie for %s",
            handler.request.remote_ip,
        )
        self.set_cookie(handler, url_token)


class HubOAuth(HubAuth):
    """HubAuth using OAuth for login instead of cookies set by the Hub.

    Use this class if you want users to be able to visit your service with a browser.
    They will be authenticated via OAuth with the Hub.

    .. versionadded: 0.8
    """

    # Overrides of HubAuth API

    @default('login_url')
    def _login_url(self):
        return url_concat(
            self.oauth_authorization_url,
            {
                'client_id': self.oauth_client_id,
                'redirect_uri': self.oauth_redirect_uri,
                'response_type': 'code',
            },
        )

    @property
    def cookie_name(self):
        """Use OAuth client_id for cookie name

        because we don't want to use the same cookie name
        across OAuth clients.
        """
        cookie_name = self.oauth_client_id
        if self.cookie_host_prefix_enabled:
            cookie_name = "__Host-" + cookie_name
        return cookie_name

    @property
    def state_cookie_name(self):
        """The cookie name for storing OAuth state

        This cookie is only live for the duration of the OAuth handshake.
        """
        return self.cookie_name + '-oauth-state'

    def _get_token_cookie(self, handler):
        """Base class doesn't store tokens in cookies"""
        if hasattr(handler, "_hub_auth_token_cookie"):
            return handler._hub_auth_token_cookie

        fetch_mode = handler.request.headers.get("Sec-Fetch-Mode", "unset")
        if fetch_mode == "websocket" and not self.allow_websocket_cookie_auth:
            # disallow cookie auth on websockets
            return None

        token = handler.get_secure_cookie(self.cookie_name)
        if token:
            # decode cookie bytes
            token = token.decode('ascii', 'replace')
        return token

    def _get_xsrf_token_id(self, handler):
        """Get contents for xsrf token for a given Handler

        This is the value to be encrypted & signed in the xsrf token
        """
        token = self._get_token_cookie(handler)
        session_id = self.get_session_id(handler)
        if token:
            token_hash = hashlib.sha256(token.encode("ascii", "replace")).hexdigest()
            if not session_id:
                session_id = _anonymous_xsrf_id(handler)
        else:
            token_hash = _anonymous_xsrf_id(handler)
        return f"{session_id}:{token_hash}".encode("ascii", "replace")

    def _patch_xsrf(self, handler):
        """Patch handler to inject JuptyerHub xsrf token behavior"""
        if isinstance(handler, HubAuthenticated):
            # doesn't need patch
            return

        # patch in our xsrf token handling
        # overrides tornado and jupyter_server defaults,
        # but not others.
        # subclasses will still inherit our overridden behavior,
        # but their overrides (if any) will take precedence over ours
        # such as jupyter-server-proxy
        for cls in handler.__class__.__mro__:
            # search for the nearest parent class defined
            # in one of the 'base' Handler-defining packages.
            # In current implementations, this will
            # generally be jupyter_server.base.handlers.JupyterHandler
            # or tornado.web.RequestHandler,
            # but doing it this way ensures consistent results
            if (cls.__module__ or '').partition('.')[0] not in {
                "jupyter_server",
                "notebook",
                "tornado",
            }:
                continue
            # override check_xsrf_cookie where it's defined
            if "check_xsrf_cookie" in cls.__dict__:
                if "_get_xsrf_token_id" in cls.__dict__:
                    # already patched
                    return
                cls._xsrf_token_id = property(self._get_xsrf_token_id)
                cls.xsrf_token = property(
                    partial(get_xsrf_token, cookie_path=self.base_url)
                )
                cls.check_xsrf_cookie = lambda handler: self.check_xsrf_cookie(handler)

    def check_xsrf_cookie(self, handler):
        """check_xsrf_cookie patch

        Applies JupyterHub check_xsrf_cookie if not token authenticated
        """
        if getattr(handler, '_token_authenticated', False) or handler.settings.get(
            "disable_check_xsrf", False
        ):
            return
        check_xsrf_cookie(handler)

    def _clear_cookie(self, handler, cookie_name, **kwargs):
        """Clear a cookie, handling __Host- prefix"""
        # Set-Cookie is rejected without 'secure',
        # this includes clearing cookies!
        if cookie_name.startswith("__Host-"):
            kwargs["path"] = "/"
            kwargs["secure"] = True
        return handler.clear_cookie(cookie_name, **kwargs)

    async def _get_user_cookie(self, handler):
        # check xsrf if needed
        token = self._get_token_cookie(handler)
        session_id = self.get_session_id(handler)
        if token and _needs_check_xsrf(handler):
            # call handler.check_xsrf_cookie instead of self.check_xsrf_cookie
            # to allow subclass overrides
            try:
                handler.check_xsrf_cookie()
            except HTTPError as e:
                self.log.debug(
                    f"Not accepting cookie auth on {handler.request.method} {handler.request.path}: {e.log_message}"
                )
                # don't proceed with cookie auth unless xsrf is okay
                # don't raise either, because that makes a mess
                return None

        if token:
            user_model = await self.user_for_token(
                token, session_id=session_id, sync=False
            )
            if user_model is None:
                app_log.warning("Token stored in cookie may have expired")
                self._clear_cookie(handler, self.cookie_name, path=self.cookie_path)
            return user_model

    # HubOAuth API

    oauth_client_id = Unicode(
        help="""The OAuth client ID for this application.

        Use JUPYTERHUB_CLIENT_ID by default.
        """
    ).tag(config=True)

    @default('oauth_client_id')
    def _client_id(self):
        return os.getenv('JUPYTERHUB_CLIENT_ID', '')

    @validate('oauth_client_id', 'api_token')
    def _ensure_not_empty(self, proposal):
        if not proposal.value:
            raise ValueError(f"{proposal.trait.name} cannot be empty.")
        return proposal.value

    oauth_redirect_uri = Unicode(
        help="""OAuth redirect URI

        Should generally be /base_url/oauth_callback
        """
    ).tag(config=True)

    @default('oauth_redirect_uri')
    def _default_redirect(self):
        return os.getenv('JUPYTERHUB_OAUTH_CALLBACK_URL') or url_path_join(
            self.base_url, 'oauth_callback'
        )

    oauth_authorization_url = Unicode(
        '/hub/api/oauth2/authorize',
        help="The URL to redirect to when starting the OAuth process",
    ).tag(config=True)

    @default('oauth_authorization_url')
    def _auth_url(self):
        return self.hub_host + url_path_join(self.hub_prefix, 'api/oauth2/authorize')

    oauth_token_url = Unicode(
        help="""The URL for requesting an OAuth token from JupyterHub"""
    ).tag(config=True)

    @default('oauth_token_url')
    def _token_url(self):
        return url_path_join(self.api_url, 'oauth2/token')

    def token_for_code(self, code, *, sync=True):
        """Get token for OAuth temporary code

        This is the last step of OAuth login.
        Should be called in OAuth Callback handler.

        Args:
            code (str): oauth code for finishing OAuth login
        Returns:
            token (str): JupyterHub API Token
        """
        return self._call_coroutine(sync, self._token_for_code, code)

    async def _token_for_code(self, code):
        # GitHub specifies a POST request yet requires URL parameters
        params = dict(
            client_id=self.oauth_client_id,
            client_secret=self.api_token,
            grant_type='authorization_code',
            code=code,
            redirect_uri=self.oauth_redirect_uri,
        )

        token_reply = await self._api_request(
            'POST',
            self.oauth_token_url,
            body=urlencode(params).encode('utf8'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )

        return token_reply['access_token']

    # state-related

    oauth_state_max_age = Integer(
        600,
        config=True,
        help="""Max age (seconds) of oauth state.
        
        Governs both oauth state cookie Max-Age,
        as well as the in-memory _oauth_states cache.
        """,
    )
    _oauth_states = Instance(
        _ExpiringDict,
        allow_none=False,
        help="""
        Store oauth state info for each oauth request, such as next_url
        
        The oauth state field only contains the oauth state _id_ of each pending request,
        while other information such as the cookie name, next_url
        are stored in this dictionary.
        """,
    )

    @default('_oauth_states')
    def _default_oauth_states(self):
        return _ExpiringDict(max_age=self.oauth_state_max_age)

    def set_state_cookie(self, handler, next_url=None):
        """Generate an OAuth state and store it in a cookie

        Parameters
        ----------
        handler : RequestHandler
            A tornado RequestHandler
        next_url : str
            The page to redirect to on successful login

        Returns
        -------
        state : str
            The OAuth state that has been stored in the cookie (url safe, base64-encoded)
        """
        extra_state = {}
        if handler.get_cookie(self.state_cookie_name):
            # oauth state cookie is already set
            # use a randomized cookie suffix to avoid collisions
            # in case of concurrent logins
            app_log.warning("Detected unused OAuth state cookies")
            cookie_suffix = ''.join(
                random.choice(string.ascii_letters) for i in range(8)
            )
            cookie_name = f'{self.state_cookie_name}-{cookie_suffix}'
            extra_state['cookie_name'] = cookie_name
        else:
            cookie_name = self.state_cookie_name
        state_id = self.generate_state(next_url, **extra_state)
        kwargs = {
            'path': self.cookie_path,
            'httponly': True,
            # Expire oauth state cookie in ten minutes.
            # Usually this will be cleared by completed login
            # in less than a few seconds.
            # OAuth that doesn't complete shouldn't linger too long.
            'max_age': 600,
        }
        public_url = os.getenv("JUPYTERHUB_PUBLIC_URL")
        if public_url:
            if urlparse(public_url).scheme == 'https':
                kwargs['secure'] = True
        else:
            if get_browser_protocol(handler.request) == 'https':
                kwargs['secure'] = True

        # don't allow overriding some fields
        no_override_keys = set(kwargs.keys()) | {"expires_days", "expires"}

        # load user cookie overrides
        for key, value in self.cookie_options.items():
            # don't include overrides
            if key.lower() not in no_override_keys:
                kwargs[key] = value
        handler.set_secure_cookie(cookie_name, state_id, **kwargs)
        return state_id

    def generate_state(self, next_url=None, **extra_state):
        """Generate a state string, given a next_url redirect target

        The state info is stored locally in self._oauth_states,
        and only the state id is returned for use in the oauth state field (cookie, redirect param)

        Parameters
        ----------
        next_url : str
            The URL of the page to redirect to on successful login.

        Returns
        -------
        state_id (str): The state string to be used as a cookie value.
        """
        state_id = secrets.token_urlsafe(16)
        state = {'next_url': next_url}
        if extra_state:
            state.update(extra_state)
        self._oauth_states[state_id] = state
        return state_id

    def clear_oauth_state(self, state_id):
        """Clear persisted oauth state"""
        self._oauth_states.pop(state_id, None)
        self._oauth_states.purge_expired()

    def clear_oauth_state_cookies(self, handler):
        """Clear persisted oauth state"""
        for cookie_name, cookie in handler.request.cookies.items():
            if cookie_name.startswith(self.state_cookie_name):
                self._clear_cookie(
                    handler,
                    cookie_name,
                    path=self.cookie_path,
                )

    def _decode_state(self, state_id, /):
        return self._oauth_states.get(state_id, {})

    def get_next_url(self, state_id='', /):
        """Get the next_url for redirection, given an encoded OAuth state"""
        state = self._decode_state(state_id)
        return state.get('next_url') or self.base_url

    def get_state_cookie_name(self, state_id='', /):
        """Get the cookie name for oauth state, given an encoded OAuth state

        Cookie name is stored in the state itself because the cookie name
        is randomized to deal with races between concurrent oauth sequences.
        """
        state = self._decode_state(state_id)
        return state.get('cookie_name') or self.state_cookie_name

    def set_cookie(self, handler, access_token):
        """Set a cookie recording OAuth result"""
        kwargs = {'path': self.cookie_path, 'httponly': True}
        if (
            get_browser_protocol(handler.request) == 'https'
            or self.cookie_host_prefix_enabled
        ):
            kwargs['secure'] = True
        # load user cookie overrides
        kwargs.update(self.cookie_options)
        app_log.debug(
            "Setting oauth cookie for %s: %s, %s",
            handler.request.remote_ip,
            self.cookie_name,
            kwargs,
        )
        handler.set_secure_cookie(self.cookie_name, access_token, **kwargs)
        # set updated xsrf token cookie,
        # which changes after login
        handler._hub_auth_token_cookie = access_token
        _set_xsrf_cookie(
            handler,
            handler._xsrf_token_id,
            cookie_path=self.base_url,
            authenticated=True,
        )

    def clear_cookie(self, handler):
        """Clear the OAuth cookie

        Args:
            handler (tornado.web.RequestHandler): the current request handler
        """
        self._clear_cookie(handler, self.cookie_name, path=self.cookie_path)


class UserNotAllowed(Exception):
    """Exception raised when a user is identified and not allowed"""

    def __init__(self, model):
        self.model = model

    def __str__(self):
        return '<{cls} {kind}={name}>'.format(
            cls=self.__class__.__name__,
            kind=self.model['kind'],
            name=self.model['name'],
        )


class HubAuthenticated:
    """Mixin for tornado handlers that are authenticated with JupyterHub

    A handler that mixes this in must have the following attributes/properties:

    - .hub_auth: A HubAuth instance
    - .hub_scopes: A set of JupyterHub 2.0 OAuth scopes to allow.
      Default comes from .hub_auth.oauth_access_scopes,
      which in turn is set by $JUPYTERHUB_OAUTH_ACCESS_SCOPES
      Default values include:
      - 'access:services', 'access:services!service={service_name}' for services
      - 'access:servers', 'access:servers!user={user}',
      'access:servers!server={user}/{server_name}'
      for single-user servers

    If hub_scopes is not used (e.g. JupyterHub 1.x),
    these additional properties can be used:

    - .allow_admin: If True, allow any admin user.
      Default: False.
    - .hub_users: A set of usernames to allow.
      If left unspecified or None, username will not be checked.
    - .hub_groups: A set of group names to allow.
      If left unspecified or None, groups will not be checked.
    - .allow_admin: Is admin user access allowed or not
      If left unspecified or False, admin user won't have an access.

    Examples::

        class MyHandler(HubAuthenticated, web.RequestHandler):
            def initialize(self, hub_auth):
                self.hub_auth = hub_auth

            @web.authenticated
            def get(self):
                ...

    """

    # deprecated, pre-2.0 allow sets
    hub_services = None  # set of allowed services
    hub_users = None  # set of allowed users
    hub_groups = None  # set of allowed groups
    allow_admin = False  # allow any admin user access

    @property
    def hub_scopes(self):
        """Set of allowed scopes (use hub_auth.access_scopes by default)"""
        return self.hub_auth.access_scopes or None

    @property
    def allow_all(self):
        """Property indicating that all successfully identified user
        or service should be allowed.
        """
        return (
            self.hub_scopes is None
            and self.hub_services is None
            and self.hub_users is None
            and self.hub_groups is None
            and not self.allow_admin
        )

    # self.hub_auth must be a HubAuth instance.
    # If nothing specified, use default config,
    # which will be configured with defaults
    # based on JupyterHub environment variables for services.
    _hub_auth = None
    hub_auth_class = HubAuth

    @property
    def hub_auth(self):
        if self._hub_auth is None:
            self._hub_auth = self.hub_auth_class.instance()
        return self._hub_auth

    @hub_auth.setter
    def hub_auth(self, auth):
        self._hub_auth = auth

    _hub_login_url = None

    def get_login_url(self):
        """Return the Hub's login URL"""
        if self._hub_login_url is not None:
            # cached value, don't call this more than once per handler
            return self._hub_login_url

        if not self.hub_auth.login_url:
            # HubOAuth is required for login via redirect,
            # base class can only raise to avoid redirect loops
            raise HTTPError(403)

        # temporary override at setting level,
        # to allow any subclass overrides of get_login_url to preserve their effect
        # for example, APIHandler raises 403 to prevent redirects
        with mock.patch.dict(
            self.application.settings, {"login_url": self.hub_auth.login_url}
        ):
            login_url = super().get_login_url()
        app_log.debug("Redirecting to login url: %s", login_url)

        if isinstance(self.hub_auth, HubOAuth):
            # add state argument to OAuth url
            # must do this _after_ allowing get_login_url to raise
            # so we don't set unused cookies
            state = self.hub_auth.set_state_cookie(self, next_url=self.request.uri)
            login_url = url_concat(login_url, {'state': state})
        self._hub_login_url = login_url
        return login_url

    def check_hub_user(self, model):
        """Check whether Hub-authenticated user or service should be allowed.

        Returns the input if the user should be allowed, None otherwise.

        Override for custom logic in authenticating users.

        Args:
            user_model (dict): the user or service model returned from :class:`HubAuth`
        Returns:
            user_model (dict): The user model if the user should be allowed, None otherwise.
        """

        name = model['name']
        kind = model.setdefault('kind', 'user')

        if self.allow_all:
            app_log.debug(
                "Allowing Hub %s %s (all Hub users and services allowed)", kind, name
            )
            return model

        if self.hub_scopes:
            scopes = self.hub_auth.check_scopes(self.hub_scopes, model)
            if scopes:
                app_log.debug(
                    f"Allowing Hub {kind} {name} based on oauth scopes {scopes}"
                )
                return model
            else:
                app_log.warning(
                    f"Not allowing Hub {kind} {name}: missing required scopes"
                )
                app_log.debug(
                    f"Hub {kind} {name} needs scope(s) {self.hub_scopes}, has scope(s) {model['scopes']}"
                )
                # if hub_scopes are used, *only* hub_scopes are used
                # note: this means successful authentication, but insufficient permission
                raise UserNotAllowed(model)

        # proceed with the pre-2.0 way if hub_scopes is not set
        warnings.warn(
            "hub_scopes ($JUPYTERHUB not set, proceeding with pre-2.0 authentication",
            DeprecationWarning,
        )

        if self.allow_admin and model.get('admin', False):
            app_log.debug("Allowing Hub admin %s", name)
            return model

        if kind == 'service':
            # it's a service, check hub_services
            if self.hub_services and name in self.hub_services:
                app_log.debug("Allowing Hub service %s", name)
                return model
            else:
                app_log.warning("Not allowing Hub service %s", name)
                raise UserNotAllowed(model)

        if self.hub_users and name in self.hub_users:
            # user in allowed list
            app_log.debug("Allowing Hub user %s", name)
            return model
        elif self.hub_groups and set(model['groups']).intersection(self.hub_groups):
            allowed_groups = set(model['groups']).intersection(self.hub_groups)
            app_log.debug(
                "Allowing Hub user %s in group(s) %s",
                name,
                ','.join(sorted(allowed_groups)),
            )
            # group in allowed list
            return model
        else:
            app_log.warning("Not allowing Hub user %s", name)
            raise UserNotAllowed(model)

    def get_current_user(self):
        """Tornado's authentication method

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.
        """
        if hasattr(self, '_hub_auth_user_cache'):
            return self._hub_auth_user_cache
        user_model = self.hub_auth.get_user(self)
        if not user_model:
            self._hub_auth_user_cache = None
            return
        try:
            self._hub_auth_user_cache = self.check_hub_user(user_model)
        except UserNotAllowed:
            # cache None, in case get_user is called again while processing the error
            self._hub_auth_user_cache = None

            # Override redirect so if/when tornado @web.authenticated
            # tries to redirect to login URL, 403 will be raised instead.
            # This is not the best, but avoids problems that can be caused
            # when get_current_user is allowed to raise.
            def raise_on_redirect(*args, **kwargs):
                raise HTTPError(
                    403, "{kind} {name} is not allowed.".format(**user_model)
                )

            self.redirect = raise_on_redirect
            return
        except Exception:
            self._hub_auth_user_cache = None
            raise

        self.hub_auth._persist_url_token_if_set(self)
        return self._hub_auth_user_cache

    @property
    def _xsrf_token_id(self):
        if hasattr(self, "__xsrf_token_id"):
            return self.__xsrf_token_id
        if not isinstance(self.hub_auth, HubOAuth):
            return ""
        return self.hub_auth._get_xsrf_token_id(self)

    @_xsrf_token_id.setter
    def _xsrf_token_id(self, value):
        self.__xsrf_token_id = value

    @property
    def xsrf_token(self):
        return get_xsrf_token(self, cookie_path=self.hub_auth.base_url)

    def check_xsrf_cookie(self):
        return self.hub_auth.check_xsrf_cookie(self)


class HubOAuthenticated(HubAuthenticated):
    """Simple subclass of HubAuthenticated using OAuth instead of old shared cookies"""

    hub_auth_class = HubOAuth


class HubOAuthCallbackHandler(HubOAuthenticated, RequestHandler):
    """OAuth Callback handler

    Finishes the OAuth flow, setting a cookie to record the user's info.

    Should be registered at ``SERVICE_PREFIX/oauth_callback``

    .. versionadded: 0.8
    """

    async def get(self):
        error = self.get_argument("error", False)
        if error:
            msg = self.get_argument("error_description", error)
            raise HTTPError(400, f"Error in oauth: {msg}")

        code = self.get_argument("code", False)
        if not code:
            raise HTTPError(400, "OAuth callback made without a token")

        # validate OAuth state
        arg_state = self.get_argument("state", None)
        if arg_state is None:
            raise HTTPError(400, "OAuth state is missing. Try logging in again.")
        cookie_name = self.hub_auth.get_state_cookie_name(arg_state)
        cookie_state = self.get_secure_cookie(cookie_name)
        # clear cookie state now that we've consumed it
        if cookie_state:
            self.hub_auth.clear_oauth_state_cookies(self)
        else:
            # completing oauth with stale state, but already logged in.
            # stop here and redirect to default URL
            # don't complete oauth (no new token), but do complete redirecting to the destination
            if self.current_user:
                app_log.warning("Attempting oauth completion after already logging in.")
                self.hub_auth.clear_oauth_state_cookies(self)
                next_url = self.hub_auth.get_next_url(arg_state)
                self.redirect(next_url)
                return

        if isinstance(cookie_state, bytes):
            cookie_state = cookie_state.decode('ascii', 'replace')

        # check that state matches
        if arg_state != cookie_state:
            app_log.warning(
                "oauth state argument %r != cookie %s=%r",
                arg_state,
                cookie_name,
                cookie_state,
            )
            raise HTTPError(403, "oauth state does not match. Try logging in again.")
        next_url = self.hub_auth.get_next_url(cookie_state)
        # clear consumed state from _oauth_states cache now that we're done with it
        self.hub_auth.clear_oauth_state(cookie_state)
        # clear _all_ oauth state cookies on success
        # This prevents multiple concurrent logins in the same browser,
        # which is probably okay.
        self.hub_auth.clear_oauth_state_cookies(self)

        token = await self.hub_auth.token_for_code(code, sync=False)
        session_id = self.hub_auth.get_session_id(self)
        user_model = await self.hub_auth.user_for_token(
            token, session_id=session_id, sync=False
        )
        if user_model is None:
            raise HTTPError(500, "oauth callback failed to identify a user")
        app_log.info("Logged-in user %s", user_model['name'])
        app_log.debug("User model %s", user_model)
        self.hub_auth.set_cookie(self, token)
        self.redirect(next_url or self.hub_auth.base_url)
