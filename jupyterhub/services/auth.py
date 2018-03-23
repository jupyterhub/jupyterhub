"""Authenticating services with JupyterHub.

Cookies are sent to the Hub for verification. The Hub replies with a JSON
model describing the authenticated user.

``HubAuth`` can be used in any application, even outside tornado.

``HubAuthenticated`` is a mixin class for tornado handlers that should
authenticate with the Hub.

"""

import base64
import json
import os
import random
import re
import socket
import string
import time
from urllib.parse import quote, urlencode
import uuid
import warnings

import requests

from tornado.gen import coroutine
from tornado.log import app_log
from tornado.httputil import url_concat
from tornado.web import HTTPError, RequestHandler

from traitlets.config import SingletonConfigurable
from traitlets import (
    Unicode, Integer, Instance, Dict,
    default, observe, validate,
)

from ..utils import url_path_join


class _ExpiringDict(dict):
    """Dict-like cache for Hub API requests

    Values will expire after max_age seconds.

    A monotonic timer is used (time.monotonic).

    A max_age of 0 means cache forever.
    """

    max_age = 0

    def __init__(self, max_age=0):
        self.max_age = max_age
        self.timestamps = {}
        self.values = {}

    def __setitem__(self, key, value):
        """Store key and record timestamp"""
        self.timestamps[key] = time.monotonic()
        self.values[key] = value

    def __repr__(self):
        """include values and timestamps in repr"""
        now = time.monotonic()
        return repr({
            key: '{value} (age={age:.0f}s)'.format(
                value=repr(value)[:16] + '...',
                age=now-self.timestamps[key],
            )
            for key, value in self.values.items()
        })

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

    def __contains__(self, key):
        """dict check for `key in dict`"""
        self._check_age(key)
        return key in self.values

    def __getitem__(self, key):
        """Check age before returning value"""
        self._check_age(key)
        return self.values[key]

    def get(self, key, default=None):
        """dict-like get:"""
        try:
            return self[key]
        except KeyError:
            return default


class HubAuth(SingletonConfigurable):
    """A class for authenticating with JupyterHub

    This can be used by any application.

    If using tornado, use via :class:`HubAuthenticated` mixin.
    If using manually, use the ``.user_for_cookie(cookie_value)`` method
    to identify the user corresponding to a given cookie value.

    The following config must be set:

    - api_token (token for authenticating with JupyterHub API),
      fetched from the JUPYTERHUB_API_TOKEN env by default.

    The following config MAY be set:

    - api_url: the base URL of the Hub's internal API,
      fetched from JUPYTERHUB_API_URL by default.
    - cookie_cache_max_age: the number of seconds responses
      from the Hub should be cached.
    - login_url (the *public* ``/hub/login`` URL of the Hub).
    - cookie_name: the name of the cookie I should be using,
      if different from the default (unlikely).

    """

    hub_host = Unicode('',
        help="""The public host of JupyterHub
        
        Only used if JupyterHub is spreading servers across subdomains.
        """
    ).tag(config=True)
    @default('hub_host')
    def _default_hub_host(self):
        return os.getenv('JUPYTERHUB_HOST', '')

    base_url = Unicode(os.getenv('JUPYTERHUB_SERVICE_PREFIX') or '/',
        help="""The base URL prefix of this application

        e.g. /services/service-name/ or /user/name/

        Default: get from JUPYTERHUB_SERVICE_PREFIX
        """
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
    api_url = Unicode(os.getenv('JUPYTERHUB_API_URL') or 'http://127.0.0.1:8081/hub/api',
        help="""The base API URL of the Hub.

        Typically `http://hub-ip:hub-port/hub/api`
        """
    ).tag(config=True)
    @default('api_url')
    def _api_url(self):
        env_url = os.getenv('JUPYTERHUB_API_URL')
        if env_url:
            return env_url
        else:
            return 'http://127.0.0.1:8081' + url_path_join(self.hub_prefix, 'api')
    
    api_token = Unicode(os.getenv('JUPYTERHUB_API_TOKEN', ''),
        help="""API key for accessing Hub API.

        Generate with `jupyterhub token [username]` or add to JupyterHub.services config.
        """
    ).tag(config=True)

    hub_prefix = Unicode('/hub/',
        help="""The URL prefix for the Hub itself.

        Typically /hub/
        """
    ).tag(config=True)
    @default('hub_prefix')
    def _default_hub_prefix(self):
        return url_path_join(os.getenv('JUPYTERHUB_BASE_URL') or '/', 'hub') + '/'

    login_url = Unicode('/hub/login',
        help="""The login URL to use

        Typically /hub/login
        """
    ).tag(config=True)
    @default('login_url')
    def _default_login_url(self):
        return self.hub_host + url_path_join(self.hub_prefix, 'login')

    cookie_name = Unicode('jupyterhub-services',
        help="""The name of the cookie I should be looking for"""
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

    cookie_cache_max_age = Integer(help="DEPRECATED. Use cache_max_age")
    @observe('cookie_cache_max_age')
    def _deprecated_cookie_cache(self, change):
        warnings.warn("cookie_cache_max_age is deprecated in JupyterHub 0.8. Use cache_max_age instead.")
        self.cache_max_age = change.new

    cache_max_age = Integer(300,
        help="""The maximum time (in seconds) to cache the Hub's responses for authentication.

        A larger value reduces load on the Hub and occasional response lag.
        A smaller value reduces propagation time of changes on the Hub (rare).

        Default: 300 (five minutes)
        """
    ).tag(config=True)
    cache = Instance(_ExpiringDict, allow_none=False)
    @default('cache')
    def _default_cache(self):
        return _ExpiringDict(self.cache_max_age)

    def _check_hub_authorization(self, url, cache_key=None, use_cache=True):
        """Identify a user with the Hub
        
        Args:
            url (str): The API URL to check the Hub for authorization
                       (e.g. http://127.0.0.1:8081/hub/api/authorizations/token/abc-def)
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
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
            else:
                app_log.debug("Cache miss: %s" % cache_key)

        data = self._api_request('GET', url, allow_404=True)
        if data is None:
            app_log.warning("No Hub user identified for request")
        else:
            app_log.debug("Received request from Hub user %s", data)
        if use_cache:
            # cache result
            self.cache[cache_key] = data
        return data

    def _api_request(self, method, url, **kwargs):
        """Make an API request"""
        allow_404 = kwargs.pop('allow_404', False)
        headers = kwargs.setdefault('headers', {})
        headers.setdefault('Authorization', 'token %s' % self.api_token)
        try:
            r = requests.request(method, url, **kwargs)
        except requests.ConnectionError as e:
            app_log.error("Error connecting to %s: %s", self.api_url, e)
            msg = "Failed to connect to Hub API at %r." % self.api_url
            msg += "  Is the Hub accessible at this URL (from host: %s)?" % socket.gethostname()
            if '127.0.0.1' in self.api_url:
                msg += "  Make sure to set c.JupyterHub.hub_ip to an IP accessible to" + \
                       " single-user servers if the servers are not on the same host as the Hub."
            raise HTTPError(500, msg)

        data = None
        if r.status_code == 404 and allow_404:
            pass
        elif r.status_code == 403:
            app_log.error("I don't have permission to check authorization with JupyterHub, my auth token may have expired: [%i] %s", r.status_code, r.reason)
            app_log.error(r.text)
            raise HTTPError(500, "Permission failure checking authorization, I may need a new token")
        elif r.status_code >= 500:
            app_log.error("Upstream failure verifying auth token: [%i] %s", r.status_code, r.reason)
            app_log.error(r.text)
            raise HTTPError(502, "Failed to check authorization (upstream problem)")
        elif r.status_code >= 400:
            app_log.warning("Failed to check authorization: [%i] %s", r.status_code, r.reason)
            app_log.warning(r.text)
            raise HTTPError(500, "Failed to check authorization")
        else:
            data = r.json()

        return data

    def user_for_cookie(self, encrypted_cookie, use_cache=True, session_id=''):
        """Ask the Hub to identify the user for a given cookie.

        Args:
            encrypted_cookie (str): the cookie value (not decrypted, the Hub will do that)
            use_cache (bool): Specify use_cache=False to skip cached cookie values (default: True)

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.

            The 'name' field contains the user's name.
        """
        return self._check_hub_authorization(
            url=url_path_join(self.api_url,
                          "authorizations/cookie",
                          self.cookie_name,
                          quote(encrypted_cookie, safe='')),
            cache_key='cookie:{}:{}'.format(session_id, encrypted_cookie),
            use_cache=use_cache,
        )

    def user_for_token(self, token, use_cache=True, session_id=''):
        """Ask the Hub to identify the user for a given token.

        Args:
            token (str): the token
            use_cache (bool): Specify use_cache=False to skip cached cookie values (default: True)

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.

            The 'name' field contains the user's name.
        """
        return self._check_hub_authorization(
            url=url_path_join(self.api_url,
                "authorizations/token",
                quote(token, safe='')),
            cache_key='token:{}:{}'.format(session_id, token),
            use_cache=use_cache,
        )

    auth_header_name = 'Authorization'
    auth_header_pat = re.compile('token\s+(.+)', re.IGNORECASE)

    def get_token(self, handler):
        """Get the user token from a request

        - in URL parameters: ?token=<token>
        - in header: Authorization: token <token>
        """

        user_token = handler.get_argument('token', '')
        if not user_token:
            # get it from Authorization header
            m = self.auth_header_pat.match(handler.request.headers.get(self.auth_header_name, ''))
            if m:
                user_token = m.group(1)
        return user_token

    def _get_user_cookie(self, handler):
        """Get the user model from a cookie"""
        encrypted_cookie = handler.get_cookie(self.cookie_name)
        session_id = self.get_session_id(handler)
        if encrypted_cookie:
            return self.user_for_cookie(encrypted_cookie, session_id=session_id)

    def get_session_id(self, handler):
        """Get the jupyterhub session id

        from the jupyterhub-session-id cookie.
        """
        return handler.get_cookie('jupyterhub-session-id', '')

    def get_user(self, handler):
        """Get the Hub user for a given tornado handler.

        Checks cookie with the Hub to identify the current user.

        Args:
            handler (tornado.web.RequestHandler): the current request handler

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.

            The 'name' field contains the user's name.
        """

        # only allow this to be called once per handler
        # avoids issues if an error is raised,
        # since this may be called again when trying to render the error page
        if hasattr(handler, '_cached_hub_user'):
            return handler._cached_hub_user

        handler._cached_hub_user = user_model = None
        session_id = self.get_session_id(handler)

        # check token first
        token = self.get_token(handler)
        if token:
            user_model = self.user_for_token(token, session_id=session_id)
            if user_model:
                handler._token_authenticated = True

        # no token, check cookie
        if user_model is None:
            user_model = self._get_user_cookie(handler)

        # cache result
        handler._cached_hub_user = user_model
        if not user_model:
            app_log.debug("No user identified")
        return user_model


class HubOAuth(HubAuth):
    """HubAuth using OAuth for login instead of cookies set by the Hub.

    .. versionadded: 0.8
    """

    # Overrides of HubAuth API

    @default('login_url')
    def _login_url(self):
        return url_concat(self.oauth_authorization_url, {
            'client_id': self.oauth_client_id,
            'redirect_uri': self.oauth_redirect_uri,
            'response_type': 'code',
        })

    @property
    def cookie_name(self):
        """Use OAuth client_id for cookie name

        because we don't want to use the same cookie name
        across OAuth clients.
        """
        return self.oauth_client_id

    @property
    def state_cookie_name(self):
        """The cookie name for storing OAuth state

        This cookie is only live for the duration of the OAuth handshake.
        """
        return self.cookie_name + '-oauth-state'

    def _get_user_cookie(self, handler):
        token = handler.get_secure_cookie(self.cookie_name)
        session_id = self.get_session_id(handler)
        if token:
            token = token.decode('ascii', 'replace')
            user_model = self.user_for_token(token, session_id=session_id)
            if user_model is None:
                app_log.warning("Token stored in cookie may have expired")
                handler.clear_cookie(self.cookie_name)
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
            raise ValueError("%s cannot be empty." % proposal.trait.name)
        return proposal.value

    oauth_redirect_uri = Unicode(
        help="""OAuth redirect URI
        
        Should generally be /base_url/oauth_callback
        """
    ).tag(config=True)
    @default('oauth_redirect_uri')
    def _default_redirect(self):
        return os.getenv('JUPYTERHUB_OAUTH_CALLBACK_URL') or url_path_join(self.base_url, 'oauth_callback')

    oauth_authorization_url = Unicode('/hub/api/oauth2/authorize',
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

    def token_for_code(self, code):
        """Get token for OAuth temporary code
        
        This is the last step of OAuth login.
        Should be called in OAuth Callback handler.
        
        Args:
            code (str): oauth code for finishing OAuth login
        Returns:
            token (str): JupyterHub API Token
        """
        # GitHub specifies a POST request yet requires URL parameters
        params = dict(
            client_id=self.oauth_client_id,
            client_secret=self.api_token,
            grant_type='authorization_code',
            code=code,
            redirect_uri=self.oauth_redirect_uri,
        )

        token_reply = self._api_request('POST', self.oauth_token_url,
            data=urlencode(params).encode('utf8'),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            })

        return token_reply['access_token']

    def _encode_state(self, state):
        """Encode a state dict as url-safe base64"""
        # trim trailing `=` because = is itself not url-safe!
        json_state = json.dumps(state)
        return base64.urlsafe_b64encode(
            json_state.encode('utf8')
        ).decode('ascii').rstrip('=')

    def _decode_state(self, b64_state):
        """Decode a base64 state

        Always returns a dict.
        The dict will be empty if the state is invalid.
        """
        if isinstance(b64_state, str):
            b64_state = b64_state.encode('ascii')
        if len(b64_state) != 4:
            # restore padding
            b64_state = b64_state + (b'=' * (4 - len(b64_state) % 4))
        try:
            json_state = base64.urlsafe_b64decode(b64_state).decode('utf8')
        except ValueError:
            app_log.error("Failed to b64-decode state: %r", b64_state)
            return {}
        try:
            return json.loads(json_state)
        except ValueError:
            app_log.error("Failed to json-decode state: %r", json_state)
            return {}

    def set_state_cookie(self, handler, next_url=None):
        """Generate an OAuth state and store it in a cookie

        Parameters
        ----------
        handler (RequestHandler): A tornado RequestHandler
        next_url (str): The page to redirect to on successful login

        Returns
        -------
        state (str): The OAuth state that has been stored in the cookie (url safe, base64-encoded)
        """
        extra_state = {}
        if handler.get_cookie(self.state_cookie_name):
            # oauth state cookie is already set
            # use a randomized cookie suffix to avoid collisions
            # in case of concurrent logins
            app_log.warning("Detected unused OAuth state cookies")
            cookie_suffix = ''.join(random.choice(string.ascii_letters) for i in range(8))
            cookie_name = '{}-{}'.format(self.state_cookie_name, cookie_suffix)
            extra_state['cookie_name'] = cookie_name
        else:
            cookie_name = self.state_cookie_name
        b64_state = self.generate_state(next_url, **extra_state)
        kwargs = {
            'path': self.base_url,
            'httponly': True,
            # Expire oauth state cookie in ten minutes.
            # Usually this will be cleared by completed login
            # in less than a few seconds.
            # OAuth that doesn't complete shouldn't linger too long.
            'max_age': 600,
        }
        if handler.request.protocol == 'https':
            kwargs['secure'] = True
        # load user cookie overrides
        kwargs.update(self.cookie_options)
        handler.set_secure_cookie(
            cookie_name,
            b64_state,
            **kwargs
        )
        return b64_state

    def generate_state(self, next_url=None, **extra_state):
        """Generate a state string, given a next_url redirect target

        Parameters
        ----------
        next_url (str): The URL of the page to redirect to on successful login.

        Returns
        -------
        state (str): The base64-encoded state string.
        """
        state = {
            'uuid': uuid.uuid4().hex,
            'next_url': next_url,
        }
        state.update(extra_state)
        return self._encode_state(state)

    def get_next_url(self, b64_state=''):
        """Get the next_url for redirection, given an encoded OAuth state"""
        state = self._decode_state(b64_state)
        return state.get('next_url') or self.base_url

    def get_state_cookie_name(self, b64_state=''):
        """Get the cookie name for oauth state, given an encoded OAuth state

        Cookie name is stored in the state itself because the cookie name
        is randomized to deal with races between concurrent oauth sequences.
        """
        state = self._decode_state(b64_state)
        return state.get('cookie_name') or self.state_cookie_name

    def set_cookie(self, handler, access_token):
        """Set a cookie recording OAuth result"""
        kwargs = {
            'path': self.base_url,
            'httponly': True,
        }
        if handler.request.protocol == 'https':
            kwargs['secure'] = True
        # load user cookie overrides
        kwargs.update(self.cookie_options)
        app_log.debug("Setting oauth cookie for %s: %s, %s",
            handler.request.remote_ip, self.cookie_name, kwargs)
        handler.set_secure_cookie(
            self.cookie_name,
            access_token,
            **kwargs
        )
    def clear_cookie(self, handler):
        """Clear the OAuth cookie"""
        handler.clear_cookie(self.cookie_name, path=self.base_url)


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


class HubAuthenticated(object):
    """Mixin for tornado handlers that are authenticated with JupyterHub

    A handler that mixes this in must have the following attributes/properties:

    - .hub_auth: A HubAuth instance
    - .hub_users: A set of usernames to allow.
      If left unspecified or None, username will not be checked.
    - .hub_groups: A set of group names to allow.
      If left unspecified or None, groups will not be checked.

    Examples::

        class MyHandler(HubAuthenticated, web.RequestHandler):
            hub_users = {'inara', 'mal'}

            def initialize(self, hub_auth):
                self.hub_auth = hub_auth

            @web.authenticated
            def get(self):
                ...

    """
    hub_services = None # set of allowed services
    hub_users = None # set of allowed users
    hub_groups = None # set of allowed groups
    allow_admin = False # allow any admin user access
    
    @property
    def allow_all(self):
        """Property indicating that all successfully identified user
        or service should be allowed.
        """
        return (self.hub_services is None
            and self.hub_users is None
            and self.hub_groups is None)

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

    def get_login_url(self):
        """Return the Hub's login URL"""
        login_url = self.hub_auth.login_url
        if isinstance(self.hub_auth, HubOAuth):
            # add state argument to OAuth url
            state = self.hub_auth.set_state_cookie(self, next_url=self.request.uri)
            login_url = url_concat(login_url, {'state': state})
        app_log.debug("Redirecting to login url: %s", login_url)
        return login_url

    def check_hub_user(self, model):
        """Check whether Hub-authenticated user or service should be allowed.

        Returns the input if the user should be allowed, None otherwise.

        Override if you want to check anything other than the username's presence in hub_users list.

        Args:
            model (dict): the user or service model returned from :class:`HubAuth`
        Returns:
            user_model (dict): The user model if the user should be allowed, None otherwise.
        """

        name = model['name']
        kind = model.setdefault('kind', 'user')
        if self.allow_all:
            app_log.debug("Allowing Hub %s %s (all Hub users and services allowed)", kind, name)
            return model

        if self.allow_admin and model.get('admin', False):
            app_log.debug("Allowing Hub admin %s", name)
            return model

        if kind == 'service':
            # it's a service, check hub_services
            if self.hub_services and name in self.hub_services:
                app_log.debug("Allowing whitelisted Hub service %s", name)
                return model
            else:
                app_log.warning("Not allowing Hub service %s", name)
                raise UserNotAllowed(model)

        if self.hub_users and name in self.hub_users:
            # user in whitelist
            app_log.debug("Allowing whitelisted Hub user %s", name)
            return model
        elif self.hub_groups and set(model['groups']).intersection(self.hub_groups):
            allowed_groups = set(model['groups']).intersection(self.hub_groups)
            app_log.debug("Allowing Hub user %s in group(s) %s", name, ','.join(sorted(allowed_groups)))
            # group in whitelist
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
        except UserNotAllowed as e:
            # cache None, in case get_user is called again while processing the error
            self._hub_auth_user_cache = None
            # Override redirect so if/when tornado @web.authenticated
            # tries to redirect to login URL, 403 will be raised instead.
            # This is not the best, but avoids problems that can be caused
            # when get_current_user is allowed to raise.
            def raise_on_redirect(*args, **kwargs):
                raise HTTPError(403, "{kind} {name} is not allowed.".format(**user_model))
            self.redirect = raise_on_redirect
            return
        except Exception:
            self._hub_auth_user_cache = None
            raise

        # store ?token=... tokens passed via url in a cookie for future requests
        url_token = self.get_argument('token', '')
        if (
            user_model
            and url_token
            and getattr(self, '_token_authenticated', False)
            and hasattr(self.hub_auth, 'set_cookie')
        ):
            # authenticated via `?token=`
            # set a cookie for future requests
            # hub_auth.set_cookie is only available on HubOAuth
            self.hub_auth.set_cookie(self, url_token)
        return self._hub_auth_user_cache


class HubOAuthenticated(HubAuthenticated):
    """Simple subclass of HubAuthenticated using OAuth instead of old shared cookies"""
    hub_auth_class = HubOAuth


class HubOAuthCallbackHandler(HubOAuthenticated, RequestHandler):
    """OAuth Callback handler

    Finishes the OAuth flow, setting a cookie to record the user's info.

    Should be registered at ``SERVICE_PREFIX/oauth_callback``

    .. versionadded: 0.8
    """
    
    @coroutine
    def get(self):
        code = self.get_argument("code", False)
        if not code:
            raise HTTPError(400, "oauth callback made without a token")

        # validate OAuth state
        arg_state = self.get_argument("state", None)
        if arg_state is None:
            raise HTTPError("oauth state is missing. Try logging in again.")
        cookie_name = self.hub_auth.get_state_cookie_name(arg_state)
        cookie_state = self.get_secure_cookie(cookie_name)
        # clear cookie state now that we've consumed it
        self.clear_cookie(cookie_name, path=self.hub_auth.base_url)
        if isinstance(cookie_state, bytes):
            cookie_state = cookie_state.decode('ascii', 'replace')
        # check that state matches
        if arg_state != cookie_state:
            app_log.warning("oauth state %r != %r", arg_state, cookie_state)
            raise HTTPError(403, "oauth state does not match. Try logging in again.")
        next_url = self.hub_auth.get_next_url(cookie_state)
        # TODO: make async (in a Thread?)
        token = self.hub_auth.token_for_code(code)
        session_id = self.hub_auth.get_session_id(self)
        user_model = self.hub_auth.user_for_token(token, session_id=session_id)
        if user_model is None:
            raise HTTPError(500, "oauth callback failed to identify a user")
        app_log.info("Logged-in user %s", user_model)
        self.hub_auth.set_cookie(self, token)
        self.redirect(next_url or self.hub_auth.base_url)


