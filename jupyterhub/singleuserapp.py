#!/usr/bin/env python
"""Extend regular notebook server to be aware of multiuser things."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os

import requests

from tornado import ioloop
from tornado import web

from IPython.utils.traitlets import Unicode

from IPython.html.notebookapp import NotebookApp

from IPython.html.utils import url_path_join


from distutils.version import LooseVersion as V

import IPython
if V(IPython.__version__) < V('2.2'):
    raise ImportError("JupyterHub Requires IPython >= 2.2, found %s" % IPython.__version__)

# Define two methods to attach to AuthenticatedHandler,
# which authenticate via the central auth server.


def verify_token(self, token):
    """monkeypatch method for token verification"""
    token_cache = self.settings['token_cache']
    if token in token_cache:
        # we've seen this token before, don't ask upstream again
        return token_cache[token]
    
    hub_api_url = self.settings['hub_api_url']
    hub_api_key = self.settings['hub_api_key']
    r = requests.get(url_path_join(
        hub_api_url, "authorizations", token,
    ),
        headers = {'Authorization' : 'token %s' % hub_api_key}
    )
    if r.status_code == 404:
        data = {'user' : ''}
    else:
        r.raise_for_status()
        data = r.json()
    token_cache[token] = data
    return data


def get_current_user(self):
    """alternative get_current_user to query the central server"""
    my_user = self.settings['user']
    token = self.get_cookie(self.cookie_name, '')
    if token:
        auth_data = self.verify_token(token)
        if not auth_data:
            # treat invalid token the same as no token
            return None
        user = auth_data['user']
        if user == my_user:
            return user
        else:
            return None
    else:
        self.log.debug("No token cookie")
        return None


# register new hub related command-line aliases
aliases = NotebookApp.aliases.get_default_value()
aliases.update({
    'user' : 'SingleUserNotebookApp.user',
    'cookie-name': 'SingleUserNotebookApp.cookie_name',
    'hub-prefix': 'SingleUserNotebookApp.hub_prefix',
    'hub-api-url': 'SingleUserNotebookApp.hub_api_url',
    'base-url': 'SingleUserNotebookApp.base_url',
})


class SingleUserNotebookApp(NotebookApp):
    """A Subclass of the regular NotebookApp that is aware of the parent multiuser context."""
    user = Unicode(config=True)
    cookie_name = Unicode(config=True)
    hub_prefix = Unicode(config=True)
    hub_api_url = Unicode(config=True)
    aliases = aliases
    open_browser = False
    
    def _confirm_exit(self):
        # disable the exit confirmation for background notebook processes
        ioloop.IOLoop.instance().stop()
    
    def init_kernel_argv(self):
        """construct the kernel arguments"""
        # FIXME: This is 2.x-compat, remove when 3.x is requred
        self.kernel_argv = ["--profile-dir", self.profile_dir.location]
    
    def init_webapp(self):
        # monkeypatch authentication to use the hub
        from IPython.html.base.handlers import AuthenticatedHandler
        AuthenticatedHandler.verify_token = verify_token
        AuthenticatedHandler.get_current_user = get_current_user
        
        # redirect logout to the hub
        from IPython.html.auth.logout import LogoutHandler
        
        app = self
        def logout_get(self):
            self.redirect(url_path_join(app.hub_prefix, 'logout'),
                permanent=False,
            )
        LogoutHandler.get = logout_get
        
        # load the hub related settings into the tornado settings dict
        env = os.environ
        # FIXME: IPython < 3 compat
        s = getattr(self, 'tornado_settings',
                getattr(self, 'webapp_settings')
        )
        s['token_cache'] = {}
        s['user'] = self.user
        s['hub_api_key'] = env.pop('JPY_API_TOKEN', '')
        s['cookie_secret'] = env.pop('JPY_COOKIE_SECRET', '')
        s['cookie_name'] = self.cookie_name
        s['login_url'] = url_path_join(self.hub_prefix, 'login')
        s['hub_api_url'] = self.hub_api_url
        super(SingleUserNotebookApp, self).init_webapp()


def main():
    return SingleUserNotebookApp.launch_instance()


if __name__ == "__main__":
    main()
