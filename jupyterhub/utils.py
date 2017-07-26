"""Miscellaneous utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from binascii import b2a_hex
import random
import errno
import hashlib
from hmac import compare_digest
import os
import socket
from threading import Thread
import uuid
import warnings

from tornado import web, gen, ioloop
from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.log import app_log


def random_port():
    """Get a single random port."""
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# ISO8601 for strptime with/without milliseconds
ISO8601_ms = '%Y-%m-%dT%H:%M:%S.%fZ'
ISO8601_s = '%Y-%m-%dT%H:%M:%SZ'


def can_connect(ip, port):
    """Check if we can connect to an ip:port.

    Return True if we can connect, False otherwise.
    """
    if ip in {'', '0.0.0.0'}:
        ip = '127.0.0.1'
    try:
        socket.create_connection((ip, port)).close()
    except socket.error as e:
        if e.errno not in {errno.ECONNREFUSED, errno.ETIMEDOUT}:
            app_log.error("Unexpected error connecting to %s:%i %s", ip, port, e)
        return False
    else:
        return True

@gen.coroutine
def exponential_backoff(
        pass_func,
        fail_message,
        start_wait=0.2,
        scale_factor=2,
        max_wait=5,
        timeout=10,
        *args, **kwargs):
    """
    Exponentially backoff until pass_func is true.

    This function will wait with exponential backoff + random jitter for as
    many iterations as needed, with maximum timeout timeout. If pass_func is
    still returning false at the end of timeout, a TimeoutError will be raised.

    It'll start waiting at start_wait, scaling up by continuously multiplying itself
    by scale_factor until pass_func returns true. It'll never wait for more than
    max_wait seconds per iteration.

    *args and **kwargs are passed to pass_func. pass_func maybe a future, although
    that is not entirely recommended.

    It'll return the value of pass_func when it's truthy!
    """
    loop = ioloop.IOLoop.current()
    deadline = loop.time() + timeout
    scale = 1
    while True:
        ret = yield gen.maybe_future(pass_func(*args, **kwargs))
        # Truthy!
        if ret:
            return ret
        remaining = deadline - loop.time()
        if remaining < 0:
            # timeout exceeded
            break
        # Add some random jitter to improve performance
        # This makes sure that we don't overload any single iteration
        # of the tornado loop with too many things
        # See https://www.awsarchitectureblog.com/2015/03/backoff.html
        # for a good example of why and how this helps. We're using their
        # full Jitter implementation equivalent.
        dt = min(max_wait, remaining, random.uniform(0, start_wait * scale))
        scale *= scale_factor
        yield gen.sleep(dt)
    raise TimeoutError(fail_message)


@gen.coroutine
def wait_for_server(ip, port, timeout=10):
    """Wait for any server to show up at ip:port."""
    if ip in {'', '0.0.0.0'}:
        ip = '127.0.0.1'
    yield exponential_backoff(
        lambda: can_connect(ip, port),
        "Server at {ip}:{port} didn't respond in {timeout} seconds".format(ip=ip, port=port, timeout=timeout)
    )


@gen.coroutine
def wait_for_http_server(url, timeout=10):
    """Wait for an HTTP Server to respond at url.

    Any non-5XX response code will do, even 404.
    """
    client = AsyncHTTPClient()
    @gen.coroutine
    def is_reachable():
        try:
            r = yield client.fetch(url, follow_redirects=False)
            return r
        except HTTPError as e:
            if e.code >= 500:
                # failed to respond properly, wait and try again
                if e.code != 599:
                    # we expect 599 for no connection,
                    # but 502 or other proxy error is conceivable
                    app_log.warning(
                        "Server at %s responded with error: %s", url, e.code)
            else:
                app_log.debug("Server at %s responded with %s", url, e.code)
                return e.response
        except (OSError, socket.error) as e:
            if e.errno not in {errno.ECONNABORTED, errno.ECONNREFUSED, errno.ECONNRESET}:
                app_log.warning("Failed to connect to %s (%s)", url, e)
        return False
    re = yield exponential_backoff(
        is_reachable,
        "Server at {url} didn't respond in {timeout} seconds".format(url=url, timeout=timeout)
    )
    return re


# Decorators for authenticated Handlers
def auth_decorator(check_auth):
    """Make an authentication decorator.

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
    """Decorator for method authenticated only by Authorization token header

    (no cookies)
    """
    if self.get_current_user_token() is None:
        raise web.HTTPError(403)


@auth_decorator
def authenticated_403(self):
    """Decorator for method to raise 403 error instead of redirect to login

    Like tornado.web.authenticated, this decorator raises a 403 error
    instead of redirecting to login.
    """
    if self.get_current_user() is None:
        raise web.HTTPError(403)


@auth_decorator
def admin_only(self):
    """Decorator for restricting access to admin users"""
    user = self.get_current_user()
    if user is None or not user.admin:
        raise web.HTTPError(403)


# Token utilities

def new_token(*args, **kwargs):
    """Generator for new random tokens

    For now, just UUIDs.
    """
    return uuid.uuid4().hex


def hash_token(token, salt=8, rounds=16384, algorithm='sha512'):
    """Hash a token, and return it as `algorithm:salt:hash`.

    If `salt` is an integer, a random salt of that many bytes will be used.
    """
    h = hashlib.new(algorithm)
    if isinstance(salt, int):
        salt = b2a_hex(os.urandom(salt))
    if isinstance(salt, bytes):
        bsalt = salt
        salt = salt.decode('utf8')
    else:
        bsalt = salt.encode('utf8')
    btoken = token.encode('utf8', 'replace')
    h.update(bsalt)
    for i in range(rounds):
        h.update(btoken)
    digest = h.hexdigest()

    return "{algorithm}:{rounds}:{salt}:{digest}".format(**locals())


def compare_token(compare, token):
    """Compare a token with a hashed token.

    Uses the same algorithm and salt of the hashed token for comparison.
    """
    algorithm, srounds, salt, _ = compare.split(':')
    hashed = hash_token(token, salt=salt, rounds=int(srounds), algorithm=algorithm).encode('utf8')
    compare = compare.encode('utf8')
    if compare_digest(compare, hashed):
        return True
    return False


def url_path_join(*pieces):
    """Join components of url into a relative url.

    Use to prevent double slash when joining subpath. This will leave the
    initial and final / in place.

    Copied from `notebook.utils.url_path_join`.
    """
    initial = pieces[0].startswith('/')
    final = pieces[-1].endswith('/')
    stripped = [ s.strip('/') for s in pieces ]
    result = '/'.join(s for s in stripped if s)

    if initial:
        result = '/' + result
    if final:
        result = result + '/'
    if result == '//':
        result = '/'

    return result


def default_server_name(user):
    """Return the default name for a new server for a given user.

    Will be the first available integer string, e.g. '1' or '2'.
    """
    existing_names = set(user.spawners)
    # if there are 5 servers, count from 1 to 6
    for n in range(1, len(existing_names) + 2):
        name = str(n)
        if name not in existing_names:
            return name
    raise RuntimeError("It should be impossible to get here")

