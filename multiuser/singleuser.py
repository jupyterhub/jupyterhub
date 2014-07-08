#!/usr/bin/env python
"""Extend regular notebook server to be aware of multi-user things."""

import os

import requests

from tornado import web

from IPython.utils.traitlets import Unicode

from IPython.html import utils
from IPython.html.notebookapp import NotebookApp


# Define two methods to attach to AuthenticatedHandler,
# which authenticate via the central auth server.


def verify_token(self, token):
    """monkeypatch method for token verification"""
    token_cache = self.settings['token_cache']
    if token in token_cache:
        # we've seen this token before, don't ask upstream again
        return token_cache[token]
    
    multiuser_api_url = self.settings['multiuser_api_url']
    multiuser_api_key = self.settings['multiuser_api_key']
    r = requests.get(utils.url_path_join(
        multiuser_api_url, "authorizations", token,
    ),
        headers = {'Authorization' : 'token %s' % multiuser_api_key}
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
            raise web.HTTPError(403, "User %s does not have access to %s" % (user, my_user))
    else:
        self.log.debug("No token cookie")
        return None


# register new multi-user related command-line aliases
aliases = NotebookApp.aliases.get_default_value()
aliases.update({
    'user' : 'SingleUserNotebookApp.user',
    'cookie-name': 'SingleUserNotebookApp.cookie_name',
    'multiuser-prefix': 'SingleUserNotebookApp.multiuser_prefix',
    'multiuser-api-url': 'SingleUserNotebookApp.multiuser_api_url',
    'base-url': 'SingleUserNotebookApp.base_url',
})


class SingleUserNotebookApp(NotebookApp):
    """A Subclass of the regular NotebookApp that is aware of the parent multi-user context."""
    user = Unicode(config=True)
    cookie_name = Unicode(config=True)
    multiuser_prefix = Unicode(config=True)
    multiuser_api_url = Unicode(config=True)
    aliases = aliases
    browser = False
    
    def init_webapp(self):
        # monkeypatch authentication to use the multi-user
        from IPython.html.base.handlers import AuthenticatedHandler
        AuthenticatedHandler.verify_token = verify_token
        AuthenticatedHandler.get_current_user = get_current_user
        
        # load the multi-user related settings into the tornado settings dict
        env = os.environ
        s = self.webapp_settings
        s['token_cache'] = {}
        s['user'] = self.user
        s['multiuser_api_key'] = env.get('IPY_API_TOKEN', '')
        s['cookie_secret'] = env.get('IPY_COOKIE_SECRET', '')
        s['cookie_name'] = self.cookie_name
        s['login_url'] = utils.url_path_join(self.multiuser_prefix, 'login')
        s['multiuser_api_url'] = self.multiuser_api_url
        super(SingleUserNotebookApp, self).init_webapp()


def main():
    return SingleUserNotebookApp.launch_instance()


if __name__ == "__main__":
    main()
