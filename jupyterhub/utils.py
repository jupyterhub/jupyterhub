"""Miscellaneous utilities"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import concurrent.futures
import errno
import hashlib
import inspect
import os
import random
import socket
import ssl
import sys
import threading
import uuid
import warnings
from binascii import b2a_hex
from datetime import datetime
from datetime import timezone
from hmac import compare_digest
from operator import itemgetter

from async_generator import aclosing
from async_generator import async_generator
from async_generator import asynccontextmanager
from async_generator import yield_
from tornado import gen
from tornado import ioloop
from tornado import web
from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPError
from tornado.log import app_log
from tornado.platform.asyncio import to_asyncio_future


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


def isoformat(dt):
    """Render a datetime object as an ISO 8601 UTC timestamp

    Naive datetime objects are assumed to be UTC
    """
    # allow null timestamps to remain None without
    # having to check if isoformat should be called
    if dt is None:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat() + 'Z'


def can_connect(ip, port):
    """Check if we can connect to an ip:port.

    Return True if we can connect, False otherwise.
    """
    if ip in {'', '0.0.0.0', '::'}:
        ip = '127.0.0.1'
    try:
        socket.create_connection((ip, port)).close()
    except socket.error as e:
        if e.errno not in {errno.ECONNREFUSED, errno.ETIMEDOUT}:
            app_log.error("Unexpected error connecting to %s:%i %s", ip, port, e)
        return False
    else:
        return True


def make_ssl_context(keyfile, certfile, cafile=None, verify=True, check_hostname=True):
    """Setup context for starting an https server or making requests over ssl.
    """
    if not keyfile or not certfile:
        return None
    purpose = ssl.Purpose.SERVER_AUTH if verify else ssl.Purpose.CLIENT_AUTH
    ssl_context = ssl.create_default_context(purpose, cafile=cafile)
    ssl_context.load_default_certs()
    ssl_context.load_cert_chain(certfile, keyfile)
    ssl_context.check_hostname = check_hostname
    return ssl_context


async def exponential_backoff(
    pass_func,
    fail_message,
    start_wait=0.2,
    scale_factor=2,
    max_wait=5,
    timeout=10,
    timeout_tolerance=0.1,
    *args,
    **kwargs
):
    """
    Exponentially backoff until `pass_func` is true.

    The `pass_func` function will wait with **exponential backoff** and
    **random jitter** for as many needed iterations of the Tornado loop,
    until reaching maximum `timeout` or truthiness. If `pass_func` is still
    returning false at `timeout`, a `TimeoutError` will be raised.

    The first iteration will begin with a wait time of `start_wait` seconds.
    Each subsequent iteration's wait time will scale up by continuously
    multiplying itself by `scale_factor`. This continues for each iteration
    until `pass_func` returns true or an iteration's wait time has reached
    the `max_wait` seconds per iteration.

    `pass_func` may be a future, although that is not entirely recommended.

    Parameters
    ----------
    pass_func
        function that is to be run
    fail_message : str
        message for a `TimeoutError`
    start_wait : optional
        initial wait time for the first iteration in seconds
    scale_factor : optional
        a multiplier to increase the wait time for each iteration
    max_wait : optional
        maximum wait time per iteration in seconds
    timeout : optional
        maximum time of total wait in seconds
    timeout_tolerance : optional
        a small multiplier used to add jitter to `timeout`'s deadline
    *args, **kwargs
        passed to `pass_func(*args, **kwargs)`

    Returns
    -------
    value of `pass_func(*args, **kwargs)`

    Raises
    ------
    TimeoutError
        If `pass_func` is still false at the end of the `timeout` period.

    Notes
    -----
    See https://www.awsarchitectureblog.com/2015/03/backoff.html
    for information about the algorithm and examples. We're using their
    full Jitter implementation equivalent.
    """
    loop = ioloop.IOLoop.current()
    deadline = loop.time() + timeout
    # add jitter to the deadline itself to prevent re-align of a bunch of
    # timing out calls once the deadline is reached.
    if timeout_tolerance:
        tol = timeout_tolerance * timeout
        deadline = random.uniform(deadline - tol, deadline + tol)
    scale = 1
    while True:
        ret = await maybe_future(pass_func(*args, **kwargs))
        # Truthy!
        if ret:
            return ret
        remaining = deadline - loop.time()
        if remaining < 0:
            # timeout exceeded
            break
        # add some random jitter to improve performance
        # this prevents overloading any single tornado loop iteration with
        # too many things
        dt = min(max_wait, remaining, random.uniform(0, start_wait * scale))
        if dt < max_wait:
            scale *= scale_factor
        await gen.sleep(dt)
    raise TimeoutError(fail_message)


async def wait_for_server(ip, port, timeout=10):
    """Wait for any server to show up at ip:port."""
    if ip in {'', '0.0.0.0', '::'}:
        ip = '127.0.0.1'
    await exponential_backoff(
        lambda: can_connect(ip, port),
        "Server at {ip}:{port} didn't respond in {timeout} seconds".format(
            ip=ip, port=port, timeout=timeout
        ),
        timeout=timeout,
    )


async def wait_for_http_server(url, timeout=10, ssl_context=None):
    """Wait for an HTTP Server to respond at url.

    Any non-5XX response code will do, even 404.
    """
    loop = ioloop.IOLoop.current()
    tic = loop.time()
    client = AsyncHTTPClient()
    if ssl_context:
        client.ssl_options = ssl_context

    async def is_reachable():
        try:
            r = await client.fetch(url, follow_redirects=False)
            return r
        except HTTPError as e:
            if e.code >= 500:
                # failed to respond properly, wait and try again
                if e.code != 599:
                    # we expect 599 for no connection,
                    # but 502 or other proxy error is conceivable
                    app_log.warning(
                        "Server at %s responded with error: %s", url, e.code
                    )
            else:
                app_log.debug("Server at %s responded with %s", url, e.code)
                return e.response
        except (OSError, socket.error) as e:
            if e.errno not in {
                errno.ECONNABORTED,
                errno.ECONNREFUSED,
                errno.ECONNRESET,
            }:
                app_log.warning("Failed to connect to %s (%s)", url, e)
        return False

    re = await exponential_backoff(
        is_reachable,
        "Server at {url} didn't respond in {timeout} seconds".format(
            url=url, timeout=timeout
        ),
        timeout=timeout,
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
    if self.current_user is None:
        raise web.HTTPError(403)


@auth_decorator
def admin_only(self):
    """Decorator for restricting access to admin users"""
    user = self.current_user
    if user is None or not user.admin:
        raise web.HTTPError(403)


@auth_decorator
def metrics_authentication(self):
    """Decorator for restricting access to metrics"""
    user = self.current_user
    if user is None and self.authenticate_prometheus:
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
    hashed = hash_token(
        token, salt=salt, rounds=int(srounds), algorithm=algorithm
    ).encode('utf8')
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
    stripped = [s.strip('/') for s in pieces]
    result = '/'.join(s for s in stripped if s)

    if initial:
        result = '/' + result
    if final:
        result = result + '/'
    if result == '//':
        result = '/'

    return result


def print_ps_info(file=sys.stderr):
    """Print process summary info from psutil

    warns if psutil is unavailable
    """
    try:
        import psutil
    except ImportError:
        # nothing to print
        warnings.warn(
            "psutil unavailable. Install psutil to get CPU and memory stats",
            stacklevel=2,
        )
        return
    p = psutil.Process()
    # format CPU percentage
    cpu = p.cpu_percent(0.1)
    if cpu >= 10:
        cpu_s = "%i" % cpu
    else:
        cpu_s = "%.1f" % cpu

    # format memory (only resident set)
    rss = p.memory_info().rss
    if rss >= 1e9:
        mem_s = '%.1fG' % (rss / 1e9)
    elif rss >= 1e7:
        mem_s = '%.0fM' % (rss / 1e6)
    elif rss >= 1e6:
        mem_s = '%.1fM' % (rss / 1e6)
    else:
        mem_s = '%.0fk' % (rss / 1e3)

    # left-justify and shrink-to-fit columns
    cpulen = max(len(cpu_s), 4)
    memlen = max(len(mem_s), 3)
    fd_s = str(p.num_fds())
    fdlen = max(len(fd_s), 3)
    threadlen = len('threads')

    print(
        "%s %s %s %s"
        % ('%CPU'.ljust(cpulen), 'MEM'.ljust(memlen), 'FDs'.ljust(fdlen), 'threads'),
        file=file,
    )

    print(
        "%s %s %s %s"
        % (
            cpu_s.ljust(cpulen),
            mem_s.ljust(memlen),
            fd_s.ljust(fdlen),
            str(p.num_threads()).ljust(7),
        ),
        file=file,
    )

    # trailing blank line
    print('', file=file)


def print_stacks(file=sys.stderr):
    """Print current status of the process

    For debugging purposes.
    Used as part of SIGINFO handler.

    - Shows active thread count
    - Shows current stack for all threads

    Parameters:

    file: file to write output to (default: stderr)

    """
    # local imports because these will not be used often,
    # no need to add them to startup
    import asyncio
    import traceback
    from .log import coroutine_frames

    print("Active threads: %i" % threading.active_count(), file=file)
    for thread in threading.enumerate():
        print("Thread %s:" % thread.name, end='', file=file)
        frame = sys._current_frames()[thread.ident]
        stack = traceback.extract_stack(frame)
        if thread is threading.current_thread():
            # truncate last two frames of the current thread
            # which are this function and its caller
            stack = stack[:-2]
        stack = coroutine_frames(stack)
        if stack:
            last_frame = stack[-1]
            if (
                last_frame[0].endswith('threading.py')
                and last_frame[-1] == 'waiter.acquire()'
            ) or (
                last_frame[0].endswith('thread.py')
                and last_frame[-1].endswith('work_queue.get(block=True)')
            ):
                # thread is waiting on a condition
                # call it idle rather than showing the uninteresting stack
                # most threadpools will be in this state
                print(' idle', file=file)
                continue

        print(''.join(['\n'] + traceback.format_list(stack)), file=file)

    # also show asyncio tasks, if any
    # this will increase over time as we transition from tornado
    # coroutines to native `async def`
    tasks = asyncio.Task.all_tasks()
    if tasks:
        print("AsyncIO tasks: %i" % len(tasks))
        for task in tasks:
            task.print_stack(file=file)


def maybe_future(obj):
    """Return an asyncio Future

    Use instead of gen.maybe_future

    For our compatibility, this must accept:

    - asyncio coroutine (gen.maybe_future doesn't work in tornado < 5)
    - tornado coroutine (asyncio.ensure_future doesn't work)
    - scalar (asyncio.ensure_future doesn't work)
    - concurrent.futures.Future (asyncio.ensure_future doesn't work)
    - tornado Future (works both ways)
    - asyncio Future (works both ways)
    """
    if inspect.isawaitable(obj):
        # already awaitable, use ensure_future
        return asyncio.ensure_future(obj)
    elif isinstance(obj, concurrent.futures.Future):
        return asyncio.wrap_future(obj)
    else:
        # could also check for tornado.concurrent.Future
        # but with tornado >= 5 tornado.Future is asyncio.Future
        f = asyncio.Future()
        f.set_result(obj)
        return f


@asynccontextmanager
@async_generator
async def not_aclosing(coro):
    """An empty context manager for Python < 3.5.2
    which lacks the `aclose` method on async iterators
    """
    await yield_(await coro)


if sys.version_info < (3, 5, 2):
    # Python 3.5.1 is missing the aclose method on async iterators,
    # so we can't close them
    aclosing = not_aclosing


@async_generator
async def iterate_until(deadline_future, generator):
    """An async generator that yields items from a generator
    until a deadline future resolves

    This could *almost* be implemented as a context manager
    like asyncio_timeout with a Future for the cutoff.

    However, we want one distinction: continue yielding items
    after the future is complete, as long as the are already finished.

    Usage::

        async for item in iterate_until(some_future, some_async_generator()):
            print(item)

    """
    async with aclosing(generator.__aiter__()) as aiter:
        while True:
            item_future = asyncio.ensure_future(aiter.__anext__())
            await asyncio.wait(
                [item_future, deadline_future], return_when=asyncio.FIRST_COMPLETED
            )
            if item_future.done():
                try:
                    await yield_(item_future.result())
                except (StopAsyncIteration, asyncio.CancelledError):
                    break
            elif deadline_future.done():
                # deadline is done *and* next item is not ready
                # cancel item future to avoid warnings about
                # unawaited tasks
                if not item_future.cancelled():
                    item_future.cancel()
                # resolve cancellation to avoid garbage collection issues
                try:
                    await item_future
                except asyncio.CancelledError:
                    pass
                break
            else:
                # neither is done, this shouldn't happen
                continue


def utcnow():
    """Return timezone-aware utcnow"""
    return datetime.now(timezone.utc)


def _parse_accept_header(accept):
    """
    Parse the Accept header *accept*

    Return a list with 3-tuples of
    [(str(media_type), dict(params), float(q_value)),] ordered by q values.
    If the accept header includes vendor-specific types like::
        application/vnd.yourcompany.yourproduct-v1.1+json
    It will actually convert the vendor and version into parameters and
    convert the content type into `application/json` so appropriate content
    negotiation decisions can be made.
    Default `q` for values that are not specified is 1.0

    From: https://gist.github.com/samuraisam/2714195
    """
    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0).strip()
        media_params = []
        # convert vendor-specific content type to application/json
        typ, subtyp = media_type.split('/')
        # check for a + in the sub-type
        if '+' in subtyp:
            # if it exists, determine if the subtype is a vendor-specific type
            vnd, sep, extra = subtyp.partition('+')
            if vnd.startswith('vnd'):
                # and then... if it ends in something like "-v1.1" parse the
                # version out
                if '-v' in vnd:
                    vnd, sep, rest = vnd.rpartition('-v')
                    if len(rest):
                        # add the version as a media param
                        try:
                            version = media_params.append(('version', float(rest)))
                        except ValueError:
                            version = 1.0  # could not be parsed
                # add the vendor code as a media param
                media_params.append(('vendor', vnd))
                # and re-write media_type to something like application/json so
                # it can be used usefully when looking up emitters
                media_type = '{}/{}'.format(typ, extra)

        q = 1.0
        for part in parts:
            (key, value) = part.lstrip().split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "q":
                q = float(value)
            else:
                media_params.append((key, value))
        result.append((media_type, dict(media_params), q))
    result.sort(key=itemgetter(2))
    return result


def get_accepted_mimetype(accept_header, choices=None):
    """Return the preferred mimetype from an Accept header

    If `choices` is given, return the first match,
    otherwise return the first accepted item

    Return `None` if choices is given and no match is found,
    or nothing is specified.
    """
    for (mime, params, q) in _parse_accept_header(accept_header):
        if choices:
            if mime in choices:
                return mime
            else:
                continue
        else:
            return mime
    return None
