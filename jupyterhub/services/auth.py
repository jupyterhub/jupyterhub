"""Authenticating services with JupyterHub

Cookies are sent to the Hub for verification, replying with a JSON model describing the authenticated user.

HubAuth can be used in any application, even outside tornado.

HubAuthenticated is a mixin class for tornado handlers that should authenticate with the Hub.
"""

import os
import re
import socket
import time
from urllib.parse import quote
import warnings

import requests

from tornado.log import app_log
from tornado.web import HTTPError

from traitlets.config import Configurable
from traitlets import Unicode, Integer, Instance, default, observe

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


class HubAuth(Configurable):
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

    # where is the hub
    api_url = Unicode(os.environ.get('JUPYTERHUB_API_URL') or 'http://127.0.0.1:8081/hub/api',
        help="""The base API URL of the Hub.

        Typically http://hub-ip:hub-port/hub/api
        """
    ).tag(config=True)

    login_url = Unicode('/hub/login',
        help="""The login URL of the Hub
        
        Typically /hub/login
        """
    ).tag(config=True)

    api_token = Unicode(os.environ.get('JUPYTERHUB_API_TOKEN', ''),
        help="""API key for accessing Hub API.

        Generate with `jupyterhub token [username]` or add to JupyterHub.services config.
        """
    ).tag(config=True)

    cookie_name = Unicode('jupyterhub-services',
        help="""The name of the cookie I should be looking for"""
    ).tag(config=True)
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

        try:
            r = requests.get(url,
                headers = {
                    'Authorization' : 'token %s' % self.api_token,
                },
            )
        except requests.ConnectionError:
            msg = "Failed to connect to Hub API at %r." % self.api_url
            msg += "  Is the Hub accessible at this URL (from host: %s)?" % socket.gethostname()
            if '127.0.0.1' in self.api_url:
                msg += "  Make sure to set c.JupyterHub.hub_ip to an IP accessible to" + \
                       " single-user servers if the servers are not on the same host as the Hub."
            raise HTTPError(500, msg)

        data = None
        if r.status_code == 404:
            app_log.warning("No Hub user identified for request")
        elif r.status_code == 403:
            app_log.error("I don't have permission to check authorization with JupyterHub, my auth token may have expired: [%i] %s", r.status_code, r.reason)
            raise HTTPError(500, "Permission failure checking authorization, I may need a new token")
        elif r.status_code >= 500:
            app_log.error("Upstream failure verifying auth token: [%i] %s", r.status_code, r.reason)
            raise HTTPError(502, "Failed to check authorization (upstream problem)")
        elif r.status_code >= 400:
            app_log.warning("Failed to check authorization: [%i] %s", r.status_code, r.reason)
            raise HTTPError(500, "Failed to check authorization")
        else:
            data = r.json()
            app_log.debug("Received request from Hub user %s", data)

        if use_cache:
            # cache result
            self.cache[cache_key] = data
        return data


    def user_for_cookie(self, encrypted_cookie, use_cache=True):
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
            cache_key='cookie:%s' % encrypted_cookie,
            use_cache=use_cache,
        )

    def user_for_token(self, token, use_cache=True):
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
            cache_key='token:%s' % token,
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

        # check token first
        token = self.get_token(handler)
        if token:
            user_model = self.user_for_token(token)
            if user_model:
                handler._token_authenticated = True

        # no token, check cookie
        if user_model is None:
            encrypted_cookie = handler.get_cookie(self.cookie_name)
            if encrypted_cookie:
                user_model = self.user_for_cookie(encrypted_cookie)

        # cache result
        handler._cached_hub_user = user_model
        if not user_model:
            app_log.debug("No user identified")
        return user_model


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
    @property
    def hub_auth(self):
        if self._hub_auth is None:
            self._hub_auth = HubAuth()
        return self._hub_auth

    @hub_auth.setter
    def hub_auth(self, auth):
        self._hub_auth = auth

    def get_login_url(self):
        """Return the Hub's login URL"""
        return self.hub_auth.login_url

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
        kind = model.get('kind', 'user')
        if self.allow_all:
            app_log.debug("Allowing Hub %s %s (all Hub users and services allowed)", kind, name)
            return model

        if kind == 'service':
            # it's a service, check hub_services
            if self.hub_services and name in self.hub_services:
                app_log.debug("Allowing whitelisted Hub service %s", name)
                return model
            else:
                app_log.warning("Not allowing Hub service %s", name)
                return None

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
            return None

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
        self._hub_auth_user_cache = self.check_hub_user(user_model)
        return self._hub_auth_user_cache

