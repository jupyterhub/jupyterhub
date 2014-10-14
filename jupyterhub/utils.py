"""Miscellaneous utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import binascii
import errno
import os
import socket
from tornado import web, gen, ioloop
from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.log import app_log

from IPython.html.utils import url_path_join

try:
    # make TimeoutError importable on Python >= 3.3
    TimeoutError = TimeoutError
except NameError:
    # python < 3.3
    class TimeoutError(Exception):
        pass

def random_port():
    """get a single random port"""
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

# ISO8601 for strptime with/without milliseconds
ISO8601_ms = '%Y-%m-%dT%H:%M:%S.%fZ'
ISO8601_s = '%Y-%m-%dT%H:%M:%SZ'

def random_hex(nbytes):
    """Return nbytes random bytes as a unicode hex string

    It will have length nbytes * 2
    """
    return binascii.hexlify(os.urandom(nbytes)).decode('ascii')

@gen.coroutine
def wait_for_server(ip, port, timeout=10):
    """wait for any server to show up at ip:port"""
    loop = ioloop.IOLoop.current()
    tic = loop.time()
    while loop.time() - tic < timeout:
        try:
            socket.create_connection((ip, port))
        except socket.error as e:
            if e.errno != errno.ECONNREFUSED:
                app_log.error("Unexpected error waiting for %s:%i %s",
                    ip, port, e
                )
            yield gen.Task(loop.add_timeout, loop.time() + 0.1)
        else:
            return
    raise TimeoutError

@gen.coroutine
def wait_for_http_server(url, timeout=10):
    """Wait for an HTTP Server to respond at url
    
    Any non-5XX response code will do, even 404.
    """
    loop = ioloop.IOLoop.current()
    tic = loop.time()
    client = AsyncHTTPClient()
    while loop.time() - tic < timeout:
        try:
            r = yield client.fetch(url, follow_redirects=False)
        except HTTPError as e:
            if e.code >= 500:
                # failed to respond properly, wait and try again
                if e.code != 599:
                    # we expect 599 for no connection,
                    # but 502 or other proxy error is conceivable
                    app_log.warn("Server at %s responded with error: %s", url, e.code)
                yield gen.Task(loop.add_timeout, loop.time() + 0.25)
            else:
                app_log.debug("Server at %s responded with %s", url, e.code)
                return
        except (OSError, socket.error) as e:
            if e.errno not in {errno.ECONNABORTED, errno.ECONNREFUSED, errno.ECONNRESET}:
                app_log.warn("Failed to connect to %s (%s)", url, e)
            yield gen.Task(loop.add_timeout, loop.time() + 0.25)
        else:
            return
    
    raise TimeoutError

def auth_decorator(check_auth):
    """Make an authentication decorator

    I heard you like decorators, so I put a decorator
    in your decorator, so you can decorate while you decorate.
    """
    def decorator(method):
        def decorated(self, *args, **kwargs):
            check_auth(self)
            return method(self, *args, **kwargs)
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
