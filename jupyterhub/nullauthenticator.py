# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from tornado import web

from .auth import Authenticator
from .handlers.base import BaseHandler


class NullLoginHandler(BaseHandler):
    def get(self):
        raise web.HTTPError(403, "Login is not supported")


class NullAuthenticator(Authenticator):
    """Null Authenticator for JupyterHub

    For cases where authentication should be disabled,
    e.g. only allowing access via API tokens.

    .. versionadded:: 2.0
    """

    # auto_login skips 'Login with...' page on Hub 0.8
    auto_login = True

    # for Hub 0.7, show 'login with...'
    login_service = 'null'

    def get_handlers(self, app):
        return [('/nologin', NullLoginHandler)]
