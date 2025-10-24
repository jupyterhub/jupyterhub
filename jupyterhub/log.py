"""logging utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import logging
import traceback
from functools import partial
from http.cookies import SimpleCookie
from urllib.parse import urlparse, urlunparse

from tornado.log import LogFormatter, access_log
from tornado.web import HTTPError, StaticFileHandler

from .handlers.pages import HealthCheckHandler
from .metrics import prometheus_log_method


def coroutine_frames(all_frames):
    """Extract coroutine boilerplate frames from a frame list

    for better stack/traceback printing of coroutines
    """
    useful_frames = []
    for frame in all_frames:
        if frame[0] == '<string>' and frame[2] == 'raise_exc_info':
            continue
        # start out conservative with filename + function matching
        # maybe just filename matching would be sufficient
        elif frame[0].endswith('tornado/gen.py') and frame[2] in {
            'run',
            'wrapper',
            '__init__',
        }:
            continue
        elif frame[0].endswith('tornado/concurrent.py') and frame[2] == 'result':
            continue
        useful_frames.append(frame)
    return useful_frames


def coroutine_traceback(typ, value, tb):
    """Scrub coroutine frames from a traceback

    Coroutine tracebacks have a bunch of identical uninformative frames at each yield point.
    This removes those extra frames, so tracebacks should be easier to read.
    This might be a horrible idea.

    Returns a list of strings (like traceback.format_tb)
    """
    all_frames = traceback.extract_tb(tb)
    useful_frames = coroutine_frames(all_frames)

    tb_list = ['Traceback (most recent call last):\n']
    tb_list.extend(traceback.format_list(useful_frames))
    tb_list.extend(traceback.format_exception_only(typ, value))
    return tb_list


class CoroutineLogFormatter(LogFormatter):
    """Log formatter that scrubs coroutine frames"""

    def formatException(self, exc_info):
        return ''.join(coroutine_traceback(*exc_info))


# url params to be scrubbed if seen
# any url param that *contains* one of these
# will be scrubbed from logs
SCRUB_PARAM_KEYS = ('token', 'auth', 'key', 'code', 'state', '_xsrf')


def _scrub_uri(uri):
    """scrub auth info from uri"""
    if '/api/authorizations/cookie/' in uri or '/api/authorizations/token/' in uri:
        uri = uri.rsplit('/', 1)[0] + '/[secret]'
    parsed = urlparse(uri)
    if parsed.query:
        # check for potentially sensitive url params
        # use manual list + split rather than parsing
        # to minimally perturb original
        parts = parsed.query.split('&')
        changed = False
        for i, s in enumerate(parts):
            if '=' in s:
                key, value = s.split('=', 1)
                for substring in SCRUB_PARAM_KEYS:
                    if substring in key:
                        parts[i] = key + '=[secret]'
                        changed = True
        if changed:
            parsed = parsed._replace(query='&'.join(parts))
            return urlunparse(parsed)
    return uri


def _scrub_headers(headers):
    """scrub auth info from headers"""
    headers = dict(headers)
    if 'Authorization' in headers:
        auth = headers['Authorization']
        if ' ' in auth:
            auth_type = auth.split(' ', 1)[0]
        else:
            # no space, hide the whole thing in case there was a mistake
            auth_type = ''
        headers['Authorization'] = f'{auth_type} [secret]'
    if 'Cookie' in headers:
        try:
            c = SimpleCookie(headers['Cookie'])
        except Exception as e:
            # it's possible for browsers to send invalid cookies
            headers['Cookie'] = f"Invalid Cookie: {e}"
        else:
            redacted = []
            for name in c.keys():
                redacted.append(f"{name}=[secret]")
            headers['Cookie'] = '; '.join(redacted)
    return headers


# log_request adapted from IPython (BSD)


def log_request(handler):
    """log a bit more information about each request than tornado's default

    - move static file get success to debug-level (reduces noise)
    - get proxied IP instead of proxy IP
    - log referer for redirect and failed requests
    - log user-agent for failed requests
    - record per-request metrics in prometheus
    """
    status = handler.get_status()
    request = handler.request
    if status == 304 or (
        status < 300 and isinstance(handler, StaticFileHandler | HealthCheckHandler)
    ):
        # static-file success and 304 Found are debug-level
        log_level = logging.DEBUG
    elif status < 400:
        log_level = logging.INFO
    elif status < 500:
        log_level = logging.WARNING
    else:
        log_level = logging.ERROR

    uri = _scrub_uri(request.uri)
    headers = _scrub_headers(request.headers)

    request_time = 1000.0 * handler.request.request_time()

    # always log slow responses (longer than 1s) at least info-level
    if request_time >= 1000 and log_level < logging.INFO:
        log_level = logging.INFO

    log_method = partial(access_log.log, log_level)

    try:
        user = handler.current_user
    except (HTTPError, RuntimeError):
        username = ''
    else:
        if user is None:
            username = ''
        elif isinstance(user, str):
            username = user
        elif isinstance(user, dict):
            username = user['name']
        else:
            username = user.name

    ns = dict(
        status=status,
        method=request.method,
        ip=request.remote_ip,
        uri=uri,
        request_time=request_time,
        user=username,
        location='',
    )
    msg = "{status} {method} {uri}{location} ({user}@{ip}) {request_time:.2f}ms"
    if status >= 500 and status not in {502, 503}:
        log_method(json.dumps(headers, indent=2))
    elif status in {301, 302}:
        # log redirect targets
        # FIXME: _headers is private, but there doesn't appear to be a public way
        # to get headers from tornado
        location = handler._headers.get('Location')
        if location:
            ns['location'] = f' -> {_scrub_uri(location)}'
    log_method(msg.format(**ns))
    prometheus_log_method(handler)
