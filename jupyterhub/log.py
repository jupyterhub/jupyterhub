"""logging utilities"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json
import traceback

from tornado.log import LogFormatter, access_log
from tornado.web import StaticFileHandler


def coroutine_traceback(typ, value, tb):
    """Scrub coroutine frames from a traceback

    Coroutine tracebacks have a bunch of identical uninformative frames at each yield point.
    This removes those extra frames, so tracebacks should be easier to read.
    This might be a horrible idea.

    Returns a list of strings (like traceback.format_tb)
    """
    all_frames = traceback.extract_tb(tb)
    useful_frames = []
    for frame in all_frames:
        if frame[0] == '<string>' and frame[2] == 'raise_exc_info':
            continue
        # start out conservative with filename + function matching
        # maybe just filename matching would be sufficient
        elif frame[0].endswith('tornado/gen.py') and frame[2] in {'run', 'wrapper'}:
            continue
        elif frame[0].endswith('tornado/concurrent.py') and frame[2] == 'result':
            continue
        useful_frames.append(frame)
    tb_list = ['Traceback (most recent call last):\n']
    tb_list.extend(traceback.format_list(useful_frames))
    tb_list.extend(traceback.format_exception_only(typ, value))
    return tb_list


class CoroutineLogFormatter(LogFormatter):
    """Log formatter that scrubs coroutine frames"""
    def formatException(self, exc_info):
        return ''.join(coroutine_traceback(*exc_info))


def _scrub_uri(uri):
    """scrub auth info from uri"""
    if '/api/authorizations/cookie/' in uri or '/api/authorizations/token/' in uri:
        uri = uri.rsplit('/', 1)[0] + '/[secret]'
    return uri


def _scrub_headers(headers):
    """scrub auth info from headers"""
    headers = dict(headers)
    if 'Authorization' in headers:
        auth = headers['Authorization']
        if auth.startswith('token '):
            headers['Authorization'] = 'token [secret]'
    return headers


# log_request adapted from IPython (BSD)

def log_request(handler):
    """log a bit more information about each request than tornado's default

    - move static file get success to debug-level (reduces noise)
    - get proxied IP instead of proxy IP
    - log referer for redirect and failed requests
    - log user-agent for failed requests
    """
    status = handler.get_status()
    request = handler.request
    if status == 304 or (status < 300 and isinstance(handler, StaticFileHandler)):
        # static-file success and 304 Found are debug-level
        log_method = access_log.debug
    elif status < 400:
        log_method = access_log.info
    elif status < 500:
        log_method = access_log.warning
    else:
        log_method = access_log.error

    uri = _scrub_uri(request.uri)
    headers = _scrub_headers(request.headers)

    request_time = 1000.0 * handler.request.request_time()
    user = handler.get_current_user()
    ns = dict(
        status=status,
        method=request.method,
        ip=request.remote_ip,
        uri=uri,
        request_time=request_time,
        user=user.name if user else ''
    )
    msg = "{status} {method} {uri} ({user}@{ip}) {request_time:.2f}ms"
    if status >= 500 and status != 502:
        log_method(json.dumps(headers, indent=2))
    log_method(msg.format(**ns))
