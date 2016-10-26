"""Authenticating services with JupyterHub

Cookies are sent to the Hub for verification, replying with a JSON model describing the authenticated user.

HubAuth can be used in any application, even outside tornado.

HubAuthenticated is a mixin class for tornado handlers that should authenticate with the Hub.
"""

import os
import socket
import time
from urllib.parse import quote

import requests

from tornado.log import app_log
from tornado.web import HTTPError

from traitlets.config import Configurable
from traitlets import Unicode, Integer, Instance, default

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
    cookie_cache_max_age = Integer(300,
        help="""The maximum time (in seconds) to cache the Hub's response for cookie authentication.

        A larger value reduces load on the Hub and occasional response lag.
        A smaller value reduces propagation time of changes on the Hub (rare).

        Default: 300 (five minutes)
        """
    ).tag(config=True)
    cookie_cache = Instance(_ExpiringDict, allow_none=False)
    @default('cookie_cache')
    def _cookie_cache(self):
        return _ExpiringDict(self.cookie_cache_max_age)

    def user_for_cookie(self, encrypted_cookie, use_cache=True):
        """Ask the Hub to identify the user for a given cookie.

        Args:
            encrypted_cookie (str): the cookie value (not decrypted, the Hub will do that)
            use_cache (bool): Specify use_cache=False to skip cached cookie values (default: True)

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.

            The 'name' field contains the user's name.
        """
        if use_cache:
            cached = self.cookie_cache.get(encrypted_cookie)
            if cached is not None:
                return cached
        try:
            r = requests.get(
                url_path_join(self.api_url,
                              "authorizations/cookie",
                              self.cookie_name,
                              quote(encrypted_cookie, safe=''),
                ),
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

        if r.status_code == 404:
            data = None
        elif r.status_code == 403:
            app_log.error("I don't have permission to verify cookies, my auth token may have expired: [%i] %s", r.status_code, r.reason)
            raise HTTPError(500, "Permission failure checking authorization, I may need a new token")
        elif r.status_code >= 500:
            app_log.error("Upstream failure verifying auth token: [%i] %s", r.status_code, r.reason)
            raise HTTPError(502, "Failed to check authorization (upstream problem)")
        elif r.status_code >= 400:
            app_log.warning("Failed to check authorization: [%i] %s", r.status_code, r.reason)
            raise HTTPError(500, "Failed to check authorization")
        else:
            data = r.json()
        self.cookie_cache[encrypted_cookie] = data
        return data

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

        handler._cached_hub_user = None
        encrypted_cookie = handler.get_cookie(self.cookie_name)
        if encrypted_cookie:
            user_model = self.user_for_cookie(encrypted_cookie)
            handler._cached_hub_user = user_model
            return user_model
        else:
            app_log.debug("No token cookie")
            return None


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
    hub_users = None # set of allowed users
    hub_groups = None # set of allowed groups
    
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

    def check_hub_user(self, user_model):
        """Check whether Hub-authenticated user should be allowed.

        Returns the input if the user should be allowed, None otherwise.

        Override if you want to check anything other than the username's presence in hub_users list.

        Args:
            user_model (dict): the user model returned from :class:`HubAuth`
        Returns:
            user_model (dict): The user model if the user should be allowed, None otherwise.
        """
        if self.hub_users is None and self.hub_groups is None:
            # no whitelist specified, allow any authenticated Hub user
            return user_model
        name = user_model['name']
        if self.hub_users and name in self.hub_users:
            # user in whitelist
            return user_model
        elif self.hub_groups and set(user_model['groups']).union(self.hub_groups):
            # group in whitelist
            return user_model
        else:
            app_log.warning("Not allowing Hub user %s" % name)
            return None

    def get_current_user(self):
        """Tornado's authentication method

        Returns:
            user_model (dict): The user model, if a user is identified, None if authentication fails.
        """
        user_model = self.hub_auth.get_user(self)
        if not user_model:
            return
        return self.check_hub_user(user_model)

