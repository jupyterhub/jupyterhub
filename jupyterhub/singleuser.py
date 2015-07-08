#!/usr/bin/env python3
"""Extend regular notebook server to be aware of multiuser things."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
try:
    from urllib.parse import quote
except ImportError:
    # PY2 Compat
    from urllib import quote

import requests
from jinja2 import ChoiceLoader, FunctionLoader

from tornado import ioloop
from tornado.web import HTTPError


from IPython.utils.traitlets import (
    Integer,
    Unicode,
    CUnicode,
)

from IPython.html.notebookapp import NotebookApp, aliases as notebook_aliases
from IPython.html.auth.login import LoginHandler
from IPython.html.auth.logout import LogoutHandler

from IPython.html.utils import url_path_join


from distutils.version import LooseVersion as V

import IPython
if V(IPython.__version__) < V('3.0'):
    raise ImportError("JupyterHub Requires IPython >= 3.0, found %s" % IPython.__version__)

# Define two methods to attach to AuthenticatedHandler,
# which authenticate via the central auth server.

class JupyterHubLoginHandler(LoginHandler):
    @staticmethod
    def login_available(settings):
        return True
    
    @staticmethod
    def verify_token(self, cookie_name, encrypted_cookie):
        """method for token verification"""
        cookie_cache = self.settings['cookie_cache']
        if encrypted_cookie in cookie_cache:
            # we've seen this token before, don't ask upstream again
            return cookie_cache[encrypted_cookie]
    
        hub_api_url = self.settings['hub_api_url']
        hub_api_key = self.settings['hub_api_key']
        r = requests.get(url_path_join(
            hub_api_url, "authorizations/cookie", cookie_name, quote(encrypted_cookie, safe=''),
        ),
            headers = {'Authorization' : 'token %s' % hub_api_key},
        )
        if r.status_code == 404:
            data = None
        elif r.status_code == 403:
            self.log.error("I don't have permission to verify cookies, my auth token may have expired: [%i] %s", r.status_code, r.reason)
            raise HTTPError(500, "Permission failure checking authorization, I may need to be restarted")
        elif r.status_code >= 500:
            self.log.error("Upstream failure verifying auth token: [%i] %s", r.status_code, r.reason)
            raise HTTPError(502, "Failed to check authorization (upstream problem)")
        elif r.status_code >= 400:
            self.log.warn("Failed to check authorization: [%i] %s", r.status_code, r.reason)
            raise HTTPError(500, "Failed to check authorization")
        else:
            data = r.json()
        cookie_cache[encrypted_cookie] = data
        return data
    
    @staticmethod
    def get_user(self):
        """alternative get_current_user to query the central server"""
        # only allow this to be called once per handler
        # avoids issues if an error is raised,
        # since this may be called again when trying to render the error page
        if hasattr(self, '_cached_user'):
            return self._cached_user
        
        self._cached_user = None
        my_user = self.settings['user']
        encrypted_cookie = self.get_cookie(self.cookie_name)
        if encrypted_cookie:
            auth_data = JupyterHubLoginHandler.verify_token(self, self.cookie_name, encrypted_cookie)
            if not auth_data:
                # treat invalid token the same as no token
                return None
            user = auth_data['name']
            if user == my_user:
                self._cached_user = user
                return user
            else:
                return None
        else:
            self.log.debug("No token cookie")
            return None


class JupyterHubLogoutHandler(LogoutHandler):
    def get(self):
        self.redirect(url_path_join(self.settings['hub_prefix'], 'logout'))


# register new hub related command-line aliases
aliases = dict(notebook_aliases)
aliases.update({
    'user' : 'SingleUserNotebookApp.user',
    'cookie-name': 'SingleUserNotebookApp.cookie_name',
    'hub-prefix': 'SingleUserNotebookApp.hub_prefix',
    'hub-api-url': 'SingleUserNotebookApp.hub_api_url',
    'base-url': 'SingleUserNotebookApp.base_url',
})

page_template = """
{% extends "templates/page.html" %}

{% block header_buttons %}
{{super()}}

<a href='{{hub_control_panel_url}}'
 class='btn btn-default btn-sm navbar-btn pull-right'
 style='margin-right: 4px; margin-left: 2px;'
>
Control Panel</a>
{% endblock %}
"""

class SingleUserNotebookApp(NotebookApp):
    """A Subclass of the regular NotebookApp that is aware of the parent multiuser context."""
    user = CUnicode(config=True)
    def _user_changed(self, name, old, new):
        self.log.name = new
    cookie_name = Unicode(config=True)
    hub_prefix = Unicode(config=True)
    hub_api_url = Unicode(config=True)
    aliases = aliases
    open_browser = False
    trust_xheaders = True
    login_handler_class = JupyterHubLoginHandler
    logout_handler_class = JupyterHubLogoutHandler

    cookie_cache_lifetime = Integer(
        config=True,
        default_value=300,
        allow_none=True,
        help="""
        Time, in seconds, that we cache a validated cookie before requiring
        revalidation with the hub.
        """,
    )

    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    def _log_format_default(self):
        """override default log format to include time"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    def _confirm_exit(self):
        # disable the exit confirmation for background notebook processes
        ioloop.IOLoop.instance().stop()

    def _clear_cookie_cache(self):
        self.log.debug("Clearing cookie cache")
        self.tornado_settings['cookie_cache'].clear()
    
    def start(self):
        # Start a PeriodicCallback to clear cached cookies.  This forces us to
        # revalidate our user with the Hub at least every
        # `cookie_cache_lifetime` seconds.
        if self.cookie_cache_lifetime:
            ioloop.PeriodicCallback(
                self._clear_cookie_cache,
                self.cookie_cache_lifetime * 1e3,
            ).start()
        super(SingleUserNotebookApp, self).start()
    
    def init_webapp(self):
        # load the hub related settings into the tornado settings dict
        env = os.environ
        s = self.tornado_settings
        s['cookie_cache'] = {}
        s['user'] = self.user
        s['hub_api_key'] = env.pop('JPY_API_TOKEN')
        s['hub_prefix'] = self.hub_prefix
        s['cookie_name'] = self.cookie_name
        s['login_url'] = self.hub_prefix
        s['hub_api_url'] = self.hub_api_url
        s['csp_report_uri'] = url_path_join(self.hub_prefix, 'security/csp-report')
        
        super(SingleUserNotebookApp, self).init_webapp()
        self.patch_templates()
    
    def patch_templates(self):
        """Patch page templates to add Hub-related buttons"""
        env = self.web_app.settings['jinja2_env']
        
        env.globals['hub_control_panel_url'] = \
            url_path_join(self.hub_prefix, 'home')
        
        # patch jinja env loading to modify page template
        def get_page(name):
            if name == 'page.html':
                return page_template
        
        orig_loader = env.loader
        env.loader = ChoiceLoader([
            FunctionLoader(get_page),
            orig_loader,
        ])


def main():
    return SingleUserNotebookApp.launch_instance()


if __name__ == "__main__":
    main()
