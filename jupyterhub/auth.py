"""Simple PAM authenticator"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from tornado import gen
import simplepam

from IPython.config import LoggingConfigurable
from IPython.utils.traitlets import Unicode, Set

from .utils import url_path_join

class Authenticator(LoggingConfigurable):
    """A class for authentication.
    
    The API is one method, `authenticate`, a tornado gen.coroutine.
    """
    
    whitelist = Set(config=True,
        help="""Username whitelist.
        
        Use this to restrict which users can login.
        If empty, allow any user to attempt login.
        """
    )
    custom_html = Unicode('')
    
    @gen.coroutine
    def authenticate(self, handler, data):
        """Authenticate a user with login form data.
        
        This must be a tornado gen.coroutine.
        It must return the username on successful authentication,
        and return None on failed authentication.
        """
    
    def login_url(self, base_url):
        """Override to register a custom login handler"""
        return url_path_join(base_url, 'login')
    
    def logout_url(self, base_url):
        """Override to register a custom logout handler"""
        return url_path_join(base_url, 'logout')
    
    def get_handlers(self, app):
        """Return any custom handlers the authenticator needs to register
        
        (e.g. for OAuth)
        """
        return []


class PAMAuthenticator(Authenticator):
    encoding = Unicode('utf8', config=True,
        help="""The encoding to use for PAM """
    )
    service = Unicode('login', config=True,
        help="""The PAM service to use for authentication."""
    )
    
    @gen.coroutine
    def authenticate(self, handler, data):
        """Authenticate with PAM, and return the username if login is successful.
    
        Return None otherwise.
        """
        username = data['username']
        if self.whitelist and username not in self.whitelist:
            return
        # simplepam wants bytes, not unicode
        # see simplepam#3
        busername = username.encode(self.encoding)
        bpassword = data['password'].encode(self.encoding)
        if simplepam.authenticate(busername, bpassword, service=self.service):
            raise gen.Return(username)
    