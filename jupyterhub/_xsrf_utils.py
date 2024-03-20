"""utilities for XSRF 

Extends tornado's xsrf token checks with the following:

- only set xsrf cookie on navigation requests (cannot be fetched)

This utility file enables the consistent reuse of these functions
in both Hub and single-user code
"""

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie

from tornado import web
from tornado.httputil import format_timestamp
from tornado.log import app_log


def _get_signed_value_urlsafe(handler, name, b64_value):
    """Like get_signed_value (used in get_secure_cookie), but for urlsafe values

    Decodes urlsafe_base64-encoded signed values

    Returns None if any decoding failed
    """
    if b64_value is None:
        return None

    if isinstance(b64_value, str):
        try:
            b64_value = b64_value.encode("ascii")
        except UnicodeEncodeError:
            app_log.warning("Invalid value %r", b64_value)
            return None
    # re-pad, since we stripped padding in _create_signed_value
    remainder = len(b64_value) % 4
    if remainder:
        b64_value = b64_value + (b'=' * (4 - remainder))
    try:
        value = base64.urlsafe_b64decode(b64_value)
    except ValueError:
        app_log.warning("Invalid base64 value %r", b64_value)
        return None

    return web.decode_signed_value(
        handler.application.settings["cookie_secret"],
        name,
        value,
        max_age_days=31,
        min_version=2,
    )


def _create_signed_value_urlsafe(handler, name, value):
    """Like tornado's create_signed_value (used in set_secure_cookie), but returns urlsafe bytes"""

    signed_value = handler.create_signed_value(name, value)
    return base64.urlsafe_b64encode(signed_value).rstrip(b"=")


def _clear_invalid_xsrf_cookie(handler, cookie_path):
    """
    Clear invalid XSRF cookie

    This may an old XSRF token, or one set on / by another application.
    Because we cannot trust browsers or tornado to give us the more specific cookie,
    try to clear _both_ on / and on our prefix,
    then reload the page.
    """

    expired = format_timestamp(datetime.now(timezone.utc) - timedelta(days=366))
    cookie = SimpleCookie()
    cookie["_xsrf"] = ""
    morsel = cookie["_xsrf"]
    morsel["expires"] = expired
    morsel["path"] = "/"
    # use Set-Cookie directly,
    # because tornado's set_cookie and clear_cookie use a single _dict_,
    # so we can't clear a cookie on multiple paths and then set it
    handler.add_header("Set-Cookie", morsel.OutputString(None))
    if cookie_path != "/":
        # clear it multiple times!
        morsel["path"] = cookie_path
        handler.add_header("Set-Cookie", morsel.OutputString(None))

    if (
        handler.request.method.lower() == "get"
        and handler.request.headers.get("Sec-Fetch-Mode", "navigate") == "navigate"
    ):
        # reload current page because any subsequent set_cookie
        # will cancel the clearing of the cookie
        # this only makes sense on GET requests
        handler.redirect(handler.request.uri)
        # halt any other processing of the request
        raise web.Finish()


def get_xsrf_token(handler, cookie_path=""):
    """Override tornado's xsrf token to add further restrictions

    - only set cookie for regular pages (not API requests)
    - include login info in xsrf token
    - verify signature
    """
    # original: https://github.com/tornadoweb/tornado/blob/v6.4.0/tornado/web.py#L1455
    if hasattr(handler, "_xsrf_token"):
        return handler._xsrf_token

    _set_cookie = False
    # the raw cookie is the token
    xsrf_token = xsrf_cookie = handler.get_cookie("_xsrf")
    if xsrf_token:
        try:
            xsrf_token = xsrf_token.encode("ascii")
        except UnicodeEncodeError:
            xsrf_token = None

    xsrf_id_cookie = _get_signed_value_urlsafe(handler, "_xsrf", xsrf_token)
    if xsrf_cookie and not xsrf_id_cookie:
        # we have a cookie, but it's invalid!
        # handle possibility of _xsrf being set multiple times,
        # e.g. on / and on /hub/
        # this will reload the page if it's a GET request
        app_log.warning(
            "Attempting to clear invalid _xsrf cookie %r", xsrf_cookie[:4] + "..."
        )
        _clear_invalid_xsrf_cookie(handler, cookie_path)

    # check the decoded, signed value for validity
    xsrf_id = handler._xsrf_token_id
    if xsrf_id_cookie != xsrf_id:
        # this will usually happen on the first page request after login,
        # which changes the inputs to the token id
        if xsrf_id_cookie:
            app_log.debug("xsrf id mismatch %r != %r", xsrf_id_cookie, xsrf_id)
        # generate new value
        xsrf_token = _create_signed_value_urlsafe(handler, "_xsrf", xsrf_id)
        # only set cookie on regular navigation pages
        # i.e. not API requests, etc.
        # insecure URLs (public hostname/ip, no https)
        # don't set Sec-Fetch-Mode.
        # consequence of assuming 'navigate': setting a cookie unnecessarily
        # consequence of assuming not 'navigate': xsrf never set, nothing works
        _set_cookie = (
            handler.request.headers.get("Sec-Fetch-Mode", "navigate") == "navigate"
        )

    if _set_cookie:
        xsrf_cookie_kwargs = {}
        xsrf_cookie_kwargs.update(handler.settings.get('xsrf_cookie_kwargs', {}))
        xsrf_cookie_kwargs.setdefault("path", cookie_path)
        if not handler.current_user:
            # limit anonymous xsrf cookies to one hour
            xsrf_cookie_kwargs.pop("expires", None)
            xsrf_cookie_kwargs.pop("expires_days", None)
            xsrf_cookie_kwargs["max_age"] = 3600
        app_log.info(
            "Setting new xsrf cookie for %r %r",
            xsrf_id,
            xsrf_cookie_kwargs,
        )
        handler.set_cookie("_xsrf", xsrf_token, **xsrf_cookie_kwargs)
    handler._xsrf_token = xsrf_token
    return xsrf_token


def check_xsrf_cookie(handler):
    """Check that xsrf cookie matches xsrf token in request"""
    # overrides tornado's implementation
    # because we changed what a correct value should be in xsrf_token

    token = (
        handler.get_argument("_xsrf", None)
        or handler.request.headers.get("X-Xsrftoken")
        or handler.request.headers.get("X-Csrftoken")
    )

    if not token:
        raise web.HTTPError(
            403, f"'_xsrf' argument missing from {handler.request.method}"
        )

    try:
        token = token.encode("utf8")
    except UnicodeEncodeError:
        raise web.HTTPError(403, "'_xsrf' argument invalid")

    if token != handler.xsrf_token:
        raise web.HTTPError(
            403, f"XSRF cookie does not match {handler.request.method.upper()} argument"
        )


def _anonymous_xsrf_id(handler):
    """Generate an appropriate xsrf token id for an anonymous request

    Currently uses hash of request ip and user-agent

    These are typically used only for the initial login page,
    so only need to be valid for a few seconds to a few minutes
    (enough to submit a login form with MFA).
    """
    hasher = hashlib.sha256()
    hasher.update(handler.request.remote_ip.encode("ascii"))
    hasher.update(
        handler.request.headers.get("User-Agent", "").encode("utf8", "replace")
    )
    return base64.urlsafe_b64encode(hasher.digest()).decode("ascii")
