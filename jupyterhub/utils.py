"""Miscellaneous utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import concurrent.futures
import errno
import functools
import hashlib
import inspect
import os
import random
import re
import secrets
import socket
import ssl
import string
import sys
import threading
import time
import uuid
import warnings
from binascii import b2a_hex
from datetime import datetime, timezone
from functools import lru_cache
from hmac import compare_digest
from operator import itemgetter
from urllib.parse import quote

if sys.version_info >= (3, 10):
    from contextlib import aclosing
else:
    from async_generator import aclosing

import idna
from sqlalchemy.exc import SQLAlchemyError
from tornado import gen, ioloop, web
from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.log import app_log


def _bool_env(key, default=False):
    """Cast an environment variable to bool

    If unset or empty, return `default`
    `0` is False; all other values are True.
    """
    value = os.environ.get(key, "")
    if value == "":
        return default
    if value.lower() in {"0", "false"}:
        return False
    else:
        return True


# Deprecated aliases: no longer needed now that we require 3.7
def asyncio_all_tasks(loop=None):
    warnings.warn(
        "jupyterhub.utils.asyncio_all_tasks is deprecated in JupyterHub 2.4."
        " Use asyncio.all_tasks().",
        DeprecationWarning,
        stacklevel=2,
    )
    return asyncio.all_tasks(loop=loop)


def asyncio_current_task(loop=None):
    warnings.warn(
        "jupyterhub.utils.asyncio_current_task is deprecated in JupyterHub 2.4."
        " Use asyncio.current_task().",
        DeprecationWarning,
        stacklevel=2,
    )
    return asyncio.current_task(loop=loop)


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
    except OSError as e:
        if e.errno not in {errno.ECONNREFUSED, errno.ETIMEDOUT}:
            app_log.error("Unexpected error connecting to %s:%i %s", ip, port, e)
        else:
            app_log.debug("Server at %s:%i not ready: %s", ip, port, e)
        return False
    else:
        return True


def make_ssl_context(
    keyfile,
    certfile,
    cafile=None,
    verify=None,
    check_hostname=None,
    purpose=ssl.Purpose.SERVER_AUTH,
):
    """Setup context for starting an https server or making requests over ssl.

    Used for verifying internal ssl connections.
    Certificates are always verified in both directions.
    Hostnames are checked for client sockets.

    Client sockets are created with `purpose=ssl.Purpose.SERVER_AUTH` (default),
    Server sockets are created with `purpose=ssl.Purpose.CLIENT_AUTH`.
    """
    if not keyfile or not certfile:
        return None
    if verify is not None:
        purpose = ssl.Purpose.SERVER_AUTH if verify else ssl.Purpose.CLIENT_AUTH
        warnings.warn(
            f"make_ssl_context(verify={verify}) is deprecated in jupyterhub 2.4."
            f" Use make_ssl_context(purpose={purpose!s}).",
            DeprecationWarning,
            stacklevel=2,
        )
    if check_hostname is not None:
        purpose = ssl.Purpose.SERVER_AUTH if check_hostname else ssl.Purpose.CLIENT_AUTH
        warnings.warn(
            f"make_ssl_context(check_hostname={check_hostname}) is deprecated in jupyterhub 2.4."
            f" Use make_ssl_context(purpose={purpose!s}).",
            DeprecationWarning,
            stacklevel=2,
        )

    ssl_context = ssl.create_default_context(purpose, cafile=cafile)
    # always verify
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    if purpose == ssl.Purpose.SERVER_AUTH:
        # SERVER_AUTH is authenticating servers (i.e. for a client)
        ssl_context.check_hostname = True
    ssl_context.load_default_certs()

    ssl_context.load_cert_chain(certfile, keyfile)
    ssl_context.check_hostname = check_hostname
    return ssl_context


# AnyTimeoutError catches TimeoutErrors coming from asyncio, tornado, stdlib
AnyTimeoutError = (gen.TimeoutError, asyncio.TimeoutError, TimeoutError)


async def exponential_backoff(
    pass_func,
    fail_message,
    start_wait=0.2,
    scale_factor=2,
    max_wait=5,
    timeout=10,
    timeout_tolerance=0.1,
    *args,
    **kwargs,
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
        limit = min(max_wait, start_wait * scale)
        if limit < max_wait:
            scale *= scale_factor
        dt = min(remaining, random.uniform(0, limit))
        await asyncio.sleep(dt)
    raise asyncio.TimeoutError(fail_message)


async def wait_for_server(ip, port, timeout=10):
    """Wait for any server to show up at ip:port."""
    if ip in {'', '0.0.0.0', '::'}:
        ip = '127.0.0.1'
    app_log.debug("Waiting %ss for server at %s:%s", timeout, ip, port)
    tic = time.perf_counter()
    await exponential_backoff(
        lambda: can_connect(ip, port),
        f"Server at {ip}:{port} didn't respond in {timeout} seconds",
        timeout=timeout,
    )
    toc = time.perf_counter()
    app_log.debug("Server at %s:%s responded in %.2fs", ip, port, toc - tic)


async def wait_for_http_server(url, timeout=10, ssl_context=None):
    """Wait for an HTTP Server to respond at url.

    Any non-5XX response code will do, even 404.
    """
    client = AsyncHTTPClient()
    if ssl_context:
        client.ssl_options = ssl_context

    app_log.debug("Waiting %ss for server at %s", timeout, url)
    tic = time.perf_counter()

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
        except OSError as e:
            if e.errno not in {
                errno.ECONNABORTED,
                errno.ECONNREFUSED,
                errno.ECONNRESET,
            }:
                app_log.warning("Failed to connect to %s (%s)", url, e)
        except Exception as e:
            app_log.warning("Error while waiting for server %s (%s)", url, e)
        return False

    re = await exponential_backoff(
        is_reachable,
        f"Server at {url} didn't respond in {timeout} seconds",
        timeout=timeout,
    )
    toc = time.perf_counter()
    app_log.debug("Server at %s responded in %.2fs", url, toc - tic)
    return re


# Decorators for authenticated Handlers
def auth_decorator(check_auth):
    """Make an authentication decorator.

    I heard you like decorators, so I put a decorator
    in your decorator, so you can decorate while you decorate.
    """

    def decorator(method):
        def decorated(self, *args, **kwargs):
            check_auth(self, **kwargs)
            return method(self, *args, **kwargs)

        # Perhaps replace with functools.wrap
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


def admin_only(f):
    """Deprecated!"""
    # write it this way to trigger deprecation warning at decoration time,
    # not on the method call
    warnings.warn(
        """@jupyterhub.utils.admin_only is deprecated in JupyterHub 2.0.

        Use the new `@jupyterhub.scopes.needs_scope` decorator to resolve permissions,
        or check against `self.current_user.parsed_scopes`.
        """,
        DeprecationWarning,
        stacklevel=2,
    )

    # the original decorator
    @auth_decorator
    def admin_only(self):
        """Decorator for restricting access to admin users"""
        user = self.current_user
        if user is None or not user.admin:
            raise web.HTTPError(403)

    return admin_only(f)


@auth_decorator
def metrics_authentication(self):
    """Decorator for restricting access to metrics"""
    if not self.authenticate_prometheus:
        return
    scope = 'read:metrics'
    if scope not in self.parsed_scopes:
        raise web.HTTPError(403, f"Access to metrics requires scope '{scope}'")


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
        salt = b2a_hex(secrets.token_bytes(salt))
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

    return f"{algorithm}:{rounds}:{salt}:{digest}"


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


def url_escape_path(value):
    """Escape a value to be used in URLs, cookies, etc."""
    return quote(value, safe='@~')


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
        cpu_s = f"{cpu:.1f}"

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
        "{} {} {} {}".format(
            '%CPU'.ljust(cpulen), 'MEM'.ljust(memlen), 'FDs'.ljust(fdlen), 'threads'
        ),
        file=file,
    )

    print(
        f"{cpu_s.ljust(cpulen)} {mem_s.ljust(memlen)} {fd_s.ljust(fdlen)} {str(p.num_threads()).ljust(7)}",
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
    import traceback

    from .log import coroutine_frames

    print("Active threads: %i" % threading.active_count(), file=file)
    for thread in threading.enumerate():
        print(f"Thread {thread.name}:", end='', file=file)
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
    tasks = asyncio_all_tasks()
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
        # but with tornado >= 5.1 tornado.Future is asyncio.Future
        f = asyncio.Future()
        f.set_result(obj)
        return f


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
                    yield item_future.result()
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


def utcnow(*, with_tz=True):
    """Return utcnow

    with_tz (default): returns tz-aware datetime in UTC

    if with_tz=False, returns UTC timestamp without tzinfo
    (used for most internal timestamp storage because databases often don't preserve tz info)
    """
    now = datetime.now(timezone.utc)
    if not with_tz:
        now = now.replace(tzinfo=None)
    return now


def _parse_accept_header(accept):
    """
    Parse the Accept header

    Return a list with 2-tuples of
    [(str(media_type), float(q_value)),] ordered by q values (descending).

    Default `q` for values that are not specified is 1.0
    """
    result = []
    if not accept:
        return result
    for media_range in accept.split(","):
        media_type, *parts = media_range.split(";")
        media_type = media_type.strip()
        if not media_type:
            continue

        q = 1.0
        for part in parts:
            (key, _, value) = part.partition("=")
            key = key.strip()
            if key == "q":
                try:
                    q = float(value)
                except ValueError:
                    pass
                break
        result.append((media_type, q))
    result.sort(key=itemgetter(1), reverse=True)
    return result


def get_accepted_mimetype(accept_header, choices=None):
    """Return the preferred mimetype from an Accept header

    If `choices` is given, return the first match,
    otherwise return the first accepted item

    Return `None` if choices is given and no match is found,
    or nothing is specified.
    """
    for mime, q in _parse_accept_header(accept_header):
        if choices:
            if mime in choices:
                return mime
            else:
                continue
        else:
            return mime
    return None


def catch_db_error(f):
    """Catch and rollback database errors"""

    @functools.wraps(f)
    async def catching(self, *args, **kwargs):
        try:
            r = f(self, *args, **kwargs)
            if inspect.isawaitable(r):
                r = await r
        except SQLAlchemyError:
            self.log.exception("Rolling back session due to database error")
            self.db.rollback()
        else:
            return r

    return catching


def get_browser_protocol(request):
    """Get the _protocol_ seen by the browser

    Like tornado's _apply_xheaders,
    but in the case of multiple proxy hops,
    use the outermost value (what the browser likely sees)
    instead of the innermost value,
    which is the most trustworthy.

    We care about what the browser sees,
    not where the request actually came from,
    so trusting possible spoofs is the right thing to do.
    """
    headers = request.headers
    # first choice: Forwarded header
    forwarded_header = headers.get("Forwarded")
    if forwarded_header:
        first_forwarded = forwarded_header.split(",", 1)[0].strip()
        fields = {}
        forwarded_dict = {}
        for field in first_forwarded.split(";"):
            key, _, value = field.partition("=")
            fields[key.strip().lower()] = value.strip()
        if "proto" in fields and fields["proto"].lower() in {"http", "https"}:
            return fields["proto"].lower()
        else:
            app_log.warning(
                f"Forwarded header present without protocol: {forwarded_header}"
            )

    # second choice: X-Scheme or X-Forwarded-Proto
    proto_header = headers.get("X-Scheme", headers.get("X-Forwarded-Proto", None))
    if proto_header:
        proto_header = proto_header.split(",")[0].strip().lower()
        if proto_header in {"http", "https"}:
            return proto_header

    # no forwarded headers
    return request.protocol


# set of chars that are safe in dns labels
# (allow '.' because we don't mind multiple levels of subdomains)
_dns_safe = set(string.ascii_letters + string.digits + '-.')
# don't escape % because it's the escape char and we handle it separately
_dns_needs_replace = _dns_safe | {"%"}


@lru_cache
def _dns_quote(name):
    """Escape a name for use in a dns label

    this is _NOT_ fully domain-safe, but works often enough for realistic usernames.
    Fully safe would be full IDNA encoding,
    PLUS escaping non-IDNA-legal ascii,
    PLUS some encoding of boundary conditions
    """
    # escape name for subdomain label
    label = quote(name, safe="").lower()
    # some characters are not handled by quote,
    # because they are legal in URLs but not domains,
    # specifically _ and ~ (starting in 3.7).
    # Escape these in the same way (%{hex_codepoint}).
    unique_chars = set(label)
    for c in unique_chars:
        if c not in _dns_needs_replace:
            label = label.replace(c, f"%{ord(c):x}")

    # underscore is our escape char -
    # it's not officially legal in hostnames,
    # but is valid in _domain_ names (?),
    # and seems to always work in practice.
    label = label.replace("%", "_")
    return label


def subdomain_hook_legacy(name, domain, kind):
    """Legacy (default) hook for subdomains

    Users are at '$user.$host' where $user is _mostly_ DNS-safe.
    Services are all simultaneously on 'services.$host`.
    """
    if kind == "user":
        # backward-compatibility
        return f"{_dns_quote(name)}.{domain}"
    elif kind == "service":
        return f"services.{domain}"
    else:
        raise ValueError(f"kind must be 'service' or 'user', not {kind!r}")


# strict dns-safe characters (excludes '-')
_strict_dns_safe = set(string.ascii_lowercase) | set(string.digits)


def _trim_and_hash(name):
    """Always-safe fallback for a DNS label

    Produces a valid and unique DNS label for any string

    - prefix with 'u-' to avoid collisions and first-character rules
    - Selects the first N characters that are safe ('x' if none are safe)
    - suffix with truncated hash of true name
    - length is guaranteed to be < 32 characters
      leaving room for additional components to build a DNS label.
      Will currently be between 12-19 characters:
        4 (prefix, delimiters) + 7 (hash) + 1-8 (name stub)
    """
    name_hash = hashlib.sha256(name.encode('utf8')).hexdigest()[:7]

    safe_chars = [c for c in name.lower() if c in _strict_dns_safe]
    name_stub = ''.join(safe_chars[:8])
    # We MUST NOT put the `--` in the 3rd and 4th position (RFC 5891)
    # which is reserved for IDNs
    # It would be if name_stub were empty, so put 'x' here
    # (value doesn't matter, as uniqueness is in the hash - the stub is more of a hint, anyway)
    if not name_stub:
        name_stub = "x"
    return f"u-{name_stub}--{name_hash}"


# A host name (label) can start or end with a letter or a number
# this pattern doesn't need to handle the boundary conditions,
# which are handled more simply with starts/endswith
_dns_re = re.compile(r'^[a-z0-9-]{1,63}$', flags=re.IGNORECASE)


def _is_dns_safe(label, max_length=63):
    # A host name (label) MUST NOT consist of all numeric values
    if label.isnumeric():
        return False
    # A host name (label) can be up to 63 characters
    if not 0 < len(label) <= max_length:
        return False
    # A host name (label) MUST NOT start or end with a '-' (dash)
    if label.startswith('-') or label.endswith('-'):
        return False
    return bool(_dns_re.match(label))


def _strict_dns_safe_encode(name, max_length=63):
    """Will encode a username to a guaranteed-safe DNS label

    - if it contains '--' at all, jump to the end and take the hash route to avoid collisions with escaped
    - if safe, use it
    - if not, use IDNA encoding
    - if a safe encoding cannot be produced, use stripped safe characters + '--{hash}`
    - allow specifying a max_length, to give room for additional components,
      if used as only a _part_ of a DNS label.
    """
    # short-circuit: avoid accepting already-encoded results
    # which all include '--'
    if '--' in name:
        return _trim_and_hash(name)

    # if name is already safe (and can't collide with an escaped result) use it
    if _is_dns_safe(name, max_length=max_length):
        return name

    # next: use IDNA encoding, if applicable
    try:
        idna_name = idna.encode(name).decode("ascii")
    except ValueError:
        idna_name = None

    if idna_name and idna_name != name and _is_dns_safe(idna_name):
        return idna_name

    # fallback, always works: trim to safe characters and hash
    return _trim_and_hash(name)


def subdomain_hook_idna(name, domain, kind):
    """New, reliable subdomain hook

    More reliable than previous, should always produce valid domains

    - uses IDNA encoding for simple unicode names
    - separate domain for each service
    - uses stripped name and hash, where above schemes fail to produce a valid domain
    """
    safe_name = _strict_dns_safe_encode(name)
    if kind == 'user':
        # 'user' namespace is special-cased as the default
        # for aesthetics and backward-compatibility for names that don't need escaping
        suffix = ""
    else:
        suffix = f"--{kind}"
    return f"{safe_name}{suffix}.{domain}"


# From https://github.com/jupyter-server/jupyter_server/blob/fc0ac3236fdd92778ea765db6e8982212c8389ee/jupyter_server/config_manager.py#L14
def recursive_update(target, new):
    """
    Recursively update one dictionary in-place using another.

    None values will delete their keys.
    """
    for k, v in new.items():
        if isinstance(v, dict):
            if k not in target:
                target[k] = {}
            recursive_update(target[k], v)

        elif v is None:
            target.pop(k, None)

        else:
            target[k] = v
