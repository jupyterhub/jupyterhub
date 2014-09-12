"""Miscellaneous utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import socket
import time
from subprocess import check_call, CalledProcessError, STDOUT, PIPE

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


def token_authenticated(method):
    """decorator for a method authenticated only by the Authorization token header"""
    def check_token(self, *args, **kwargs):
        if self.get_current_user_token() is None:
            raise web.HTTPError(403)
        return method(self, *args, **kwargs)
    check_token.__name__ = method.__name__
    check_token.__doc__ = method.__doc__
    return check_token


def authenticated_403(method):
    """decorator like web.authenticated, but raise 403 instead of redirect to login"""
    def check_user(self, *args, **kwargs):
        if self.get_current_user() is None:
            raise web.HTTPError(403)
        return method(self, *args, **kwargs)
    check_token.__name__ = method.__name__
    check_token.__doc__ = method.__doc__
    return check_token
