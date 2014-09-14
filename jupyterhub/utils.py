"""Miscellaneous utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import socket
import time
from tornado import web

from IPython.html.utils import url_path_join

def random_port():
    """get a single random port"""
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_for_server(ip, port, timeout=10):
    """wait for a server to show up at ip:port"""
    tic = time.time()
    while time.time() - tic < timeout:
        try:
            socket.create_connection((ip, port))
        except socket.error:
            time.sleep(0.1)
        else:
            break

def auth_decorator(check_auth):
    """Make an authentication decorator

    I heard you like decorators, so I put a decorator
    in your decorator, so you can decorate while you decorate.
    """
    def decorator(method):
        def decorated(self, *args, **kwargs):
            check_auth(self)
            return method(self, *args)
        decorated.__name__ = method.__name__
        decorated.__doc__ = method.__doc__
        return decorated

    decorator.__name__ = check_auth.__name__
    decorator.__doc__ = check_auth.__doc__
    return decorator

@auth_decorator
def token_authenticated(self):
    """decorator for a method authenticated only by the Authorization token header

    (no cookies)
    """
    if self.get_current_user_token() is None:
        raise web.HTTPError(403)

@auth_decorator
def authenticated_403(self):
    """like web.authenticated, but raise 403 instead of redirect to login"""
    if self.get_current_user() is None:
        raise web.HTTPError(403)

@auth_decorator
def admin_only(self):
    """decorator for restricting access to admin users"""
    user = self.get_current_user()
    if user is None or not user.admin:
        raise web.HTTPError(403)
