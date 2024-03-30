"""utilities for XSRF

Extends tornado's xsrf token checks with the following:

- only set xsrf cookie on navigation requests (cannot be fetched)

This utility file enables the consistent reuse of these functions
in both Hub and single-user code
"""

import base64
import hashlib
from http.cookies import SimpleCookie

from tornado import web
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


def _get_xsrf_token_cookie(handler):
    """
    Get the _valid_ XSRF token and id from Cookie

    Returns (xsrf_token, xsrf_id) found in Cookies header.

    multiple xsrf cookies may be set on multiple paths;

    RFC 6265 states that they should be in order of more specific path to less,
    but ALSO states that servers should never rely on order.

    Tornado (6.4) and stdlib (3.12) SimpleCookie explicitly use the _last_ value,
    which means the cookie with the _least_ specific prefix will be used if more than one is present.

    Because we sign values, we can get the first valid cookie and not worry about order too much.

    This is simplified from tornado's HTTPRequest.cookies property
    only looking for a single cookie.
    """

    if "Cookie" not in handler.request.headers:
        return (None, None)

    for chunk in handler.request.headers["Cookie"].split(";"):
        key = chunk.partition("=")[0].strip()
        if key != "_xsrf":
            # we are only looking for the _xsrf cookie
            # ignore everything else
            continue

        # use stdlib parsing to handle quotes, validation, etc.
        try:
            xsrf_token = SimpleCookie(chunk)[key].value.encode("ascii")
        except (ValueError, KeyError):
            continue

        xsrf_token_id = _get_signed_value_urlsafe(handler, "_xsrf", xsrf_token)

        if xsrf_token_id:
            # only return if we found a _valid_ xsrf cookie
            # otherwise, keep looking
            return (xsrf_token, xsrf_token_id)
    # no valid token found found
    return (None, None)


def _set_xsrf_cookie(handler, xsrf_id, *, cookie_path="", authenticated=None):
    """Set xsrf token cookie"""
    xsrf_token = _create_signed_value_urlsafe(handler, "_xsrf", xsrf_id)
    xsrf_cookie_kwargs = {}
    xsrf_cookie_kwargs.update(handler.settings.get('xsrf_cookie_kwargs', {}))
    xsrf_cookie_kwargs.setdefault("path", cookie_path)
    if authenticated is None:
        try:
            current_user = handler.current_user
        except Exception:
            authenticated = False
        else:
            authenticated = bool(current_user)
    if not authenticated:
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
    xsrf_token, xsrf_id_cookie = _get_xsrf_token_cookie(handler)
    cookie_token = xsrf_token

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
        if xsrf_id_cookie and not _set_cookie:
            # if we aren't setting a cookie here but we got one,
            # this means things probably aren't going to work
            app_log.warning(
                "Not accepting incorrect xsrf token id in cookie on %s",
                handler.request.path,
            )

    if _set_cookie:
        _set_xsrf_cookie(handler, xsrf_id, cookie_path=cookie_path)
    handler._xsrf_token = xsrf_token
    return xsrf_token


def _needs_check_xsrf(handler):
    """Does the given cookie-authenticated request need to check xsrf?"""

    if getattr(handler, "_token_authenticated", False):
        return False

    fetch_mode = handler.request.headers.get("Sec-Fetch-Mode", "unspecified")
    if fetch_mode in {"websocket", "no-cors"} or (
        fetch_mode in {"navigate", "unspecified"}
        and handler.request.method.lower() in {"get", "head", "options"}
    ):
        # no xsrf check needed for regular page views or no-cors
        # or websockets after allow_websocket_cookie_auth passes
        if fetch_mode == "unspecified":
            app_log.warning(
                f"Skipping XSRF check for insecure request {handler.request.method} {handler.request.path}"
            )
        return False
    else:
        return True


def check_xsrf_cookie(handler):
    """Check that xsrf cookie matches xsrf token in request"""
    # overrides tornado's implementation
    # because we changed what a correct value should be in xsrf_token
    if not _needs_check_xsrf(handler):
        # don't require XSRF for regular page views
        return

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
