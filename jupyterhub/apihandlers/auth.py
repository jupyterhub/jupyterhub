"""Authorization handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from datetime import datetime
from urllib.parse import parse_qsl
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import urlunparse

from oauthlib import oauth2
from tornado import web

from .. import orm
from ..user import User
from ..utils import compare_token
from ..utils import token_authenticated
from .base import APIHandler
from .base import BaseHandler


class TokenAPIHandler(APIHandler):
    @token_authenticated
    def get(self, token):
        orm_token = orm.APIToken.find(self.db, token)
        if orm_token is None:
            orm_token = orm.OAuthAccessToken.find(self.db, token)
        if orm_token is None:
            raise web.HTTPError(404)

        # record activity whenever we see a token
        now = orm_token.last_activity = datetime.utcnow()
        if orm_token.user:
            orm_token.user.last_activity = now
            model = self.user_model(self.users[orm_token.user])
        elif orm_token.service:
            model = self.service_model(orm_token.service)
        else:
            self.log.warning("%s has no user or service. Deleting..." % orm_token)
            self.db.delete(orm_token)
            self.db.commit()
            raise web.HTTPError(404)
        self.db.commit()
        self.write(json.dumps(model))

    async def post(self):
        warn_msg = (
            "Using deprecated token creation endpoint %s."
            " Use /hub/api/users/:user/tokens instead."
        ) % self.request.uri
        self.log.warning(warn_msg)
        requester = user = self.current_user
        if user is None:
            # allow requesting a token with username and password
            # for authenticators where that's possible
            data = self.get_json_body()
            try:
                requester = user = await self.login_user(data)
            except Exception as e:
                self.log.error("Failure trying to authenticate with form data: %s" % e)
                user = None
            if user is None:
                raise web.HTTPError(403)
        else:
            data = self.get_json_body()
            # admin users can request tokens for other users
            if data and data.get('username'):
                user = self.find_user(data['username'])
                if user is not requester and not requester.admin:
                    raise web.HTTPError(
                        403, "Only admins can request tokens for other users."
                    )
                if requester.admin and user is None:
                    raise web.HTTPError(400, "No such user '%s'" % data['username'])

        note = (data or {}).get('note')
        if not note:
            note = "Requested via deprecated api"
            if requester is not user:
                kind = 'user' if isinstance(user, User) else 'service'
                note += " by %s %s" % (kind, requester.name)

        api_token = user.new_api_token(note=note)
        self.write(
            json.dumps(
                {'token': api_token, 'warning': warn_msg, 'user': self.user_model(user)}
            )
        )


class CookieAPIHandler(APIHandler):
    @token_authenticated
    def get(self, cookie_name, cookie_value=None):
        cookie_name = quote(cookie_name, safe='')
        if cookie_value is None:
            self.log.warning(
                "Cookie values in request body is deprecated, use `/cookie_name/cookie_value`"
            )
            cookie_value = self.request.body
        else:
            cookie_value = cookie_value.encode('utf8')
        user = self._user_for_cookie(cookie_name, cookie_value)
        if user is None:
            raise web.HTTPError(404)
        self.write(json.dumps(self.user_model(user)))


class OAuthHandler:
    def extract_oauth_params(self):
        """extract oauthlib params from a request

        Returns:

        (uri, http_method, body, headers)
        """
        return (
            self.request.uri,
            self.request.method,
            self.request.body,
            self.request.headers,
        )

    def make_absolute_redirect_uri(self, uri):
        """Make absolute redirect URIs

        internal redirect uris, e.g. `/user/foo/oauth_handler`
        are allowed in jupyterhub, but oauthlib prohibits them.
        Add `$HOST` header to redirect_uri to make them acceptable.

        Currently unused in favor of monkeypatching
        oauthlib.is_absolute_uri to skip the check
        """
        redirect_uri = self.get_argument('redirect_uri')
        if not redirect_uri or not redirect_uri.startswith('/'):
            return uri
        # make absolute local redirects full URLs
        # to satisfy oauthlib's absolute URI requirement
        redirect_uri = (
            self.request.protocol + "://" + self.request.headers['Host'] + redirect_uri
        )
        parsed_url = urlparse(uri)
        query_list = parse_qsl(parsed_url.query, keep_blank_values=True)
        for idx, item in enumerate(query_list):
            if item[0] == 'redirect_uri':
                query_list[idx] = ('redirect_uri', redirect_uri)
                break

        return urlunparse(urlparse(uri)._replace(query=urlencode(query_list)))

    def add_credentials(self, credentials=None):
        """Add oauth credentials

        Adds user, session_id, client to oauth credentials
        """
        if credentials is None:
            credentials = {}
        else:
            credentials = credentials.copy()

        session_id = self.get_session_cookie()
        if session_id is None:
            session_id = self.set_session_cookie()

        user = self.current_user

        # Extra credentials we need in the validator
        credentials.update({'user': user, 'handler': self, 'session_id': session_id})
        return credentials

    def send_oauth_response(self, headers, body, status):
        """Send oauth response from provider return values

        Provider methods return headers, body, and status
        to be set on the response.

        This method applies these values to the Handler
        and sends the response.
        """
        self.set_status(status)
        for key, value in headers.items():
            self.set_header(key, value)
        if body:
            self.write(body)


class OAuthAuthorizeHandler(OAuthHandler, BaseHandler):
    """Implement OAuth authorization endpoint(s)"""

    def _complete_login(self, uri, headers, scopes, credentials):
        try:
            headers, body, status = self.oauth_provider.create_authorization_response(
                uri, 'POST', '', headers, scopes, credentials
            )

        except oauth2.FatalClientError as e:
            # TODO: human error page
            raise
        self.send_oauth_response(headers, body, status)

    def needs_oauth_confirm(self, user, oauth_client):
        """Return whether the given oauth client needs to prompt for access for the given user

        Checks list for oauth clients that don't need confirmation

        (i.e. the user's own server)

        .. versionadded: 1.1
        """
        # get the oauth client ids for the user's own server(s)
        own_oauth_client_ids = set(
            spawner.oauth_client_id for spawner in user.spawners.values()
        )
        if (
            # it's the user's own server
            oauth_client.identifier in own_oauth_client_ids
            # or it's in the global no-confirm list
            or oauth_client.identifier
            in self.settings.get('oauth_no_confirm_list', set())
        ):
            return False
        # default: require confirmation
        return True

    @web.authenticated
    async def get(self):
        """GET /oauth/authorization

        Render oauth confirmation page:
        "Server at ... would like permission to ...".

        Users accessing their own server or a blessed service
        will skip confirmation.
        """

        uri, http_method, body, headers = self.extract_oauth_params()
        try:
            scopes, credentials = self.oauth_provider.validate_authorization_request(
                uri, http_method, body, headers
            )
            credentials = self.add_credentials(credentials)
            client = self.oauth_provider.fetch_by_client_id(credentials['client_id'])
            if not self.needs_oauth_confirm(self.current_user, client):
                self.log.debug(
                    "Skipping oauth confirmation for %s accessing %s",
                    self.current_user,
                    client.description,
                )
                # this is the pre-1.0 behavior for all oauth
                self._complete_login(uri, headers, scopes, credentials)
                return

            # Render oauth 'Authorize application...' page
            auth_state = await self.current_user.get_auth_state()
            self.write(
                await self.render_template(
                    "oauth.html",
                    auth_state=auth_state,
                    scopes=scopes,
                    oauth_client=client,
                )
            )

        # Errors that should be shown to the user on the provider website
        except oauth2.FatalClientError as e:
            raise web.HTTPError(e.status_code, e.description)

        # Errors embedded in the redirect URI back to the client
        except oauth2.OAuth2Error as e:
            self.log.error("OAuth error: %s", e.description)
            self.redirect(e.in_uri(e.redirect_uri))

    @web.authenticated
    def post(self):
        uri, http_method, body, headers = self.extract_oauth_params()
        referer = self.request.headers.get('Referer', 'no referer')
        full_url = self.request.full_url()
        # trim protocol, which cannot be trusted with multiple layers of proxies anyway
        # Referer is set by browser, but full_url can be modified by proxy layers to appear as http
        # when it is actually https
        referer_proto, _, stripped_referer = referer.partition("://")
        referer_proto = referer_proto.lower()
        req_proto, _, stripped_full_url = full_url.partition("://")
        req_proto = req_proto.lower()
        if referer_proto != req_proto:
            self.log.warning("Protocol mismatch: %s != %s", referer, full_url)
            if req_proto == "https":
                # insecure origin to secure target is not allowed
                raise web.HTTPError(
                    403, "Not allowing authorization form submitted from insecure page"
                )
        if stripped_referer != stripped_full_url:
            # OAuth post must be made to the URL it came from
            self.log.error("Original OAuth POST from %s != %s", referer, full_url)
            self.log.error(
                "Stripped OAuth POST from %s != %s", stripped_referer, stripped_full_url
            )
            raise web.HTTPError(
                403, "Authorization form must be sent from authorization page"
            )

        # The scopes the user actually authorized, i.e. checkboxes
        # that were selected.
        scopes = self.get_arguments('scopes')
        # credentials we need in the validator
        credentials = self.add_credentials()

        try:
            headers, body, status = self.oauth_provider.create_authorization_response(
                uri, http_method, body, headers, scopes, credentials
            )
        except oauth2.FatalClientError as e:
            raise web.HTTPError(e.status_code, e.description)
        else:
            self.send_oauth_response(headers, body, status)


class OAuthTokenHandler(OAuthHandler, APIHandler):
    def post(self):
        uri, http_method, body, headers = self.extract_oauth_params()
        credentials = {}

        try:
            headers, body, status = self.oauth_provider.create_token_response(
                uri, http_method, body, headers, credentials
            )
        except oauth2.FatalClientError as e:
            raise web.HTTPError(e.status_code, e.description)
        else:
            self.send_oauth_response(headers, body, status)


default_handlers = [
    (r"/api/authorizations/cookie/([^/]+)(?:/([^/]+))?", CookieAPIHandler),
    (r"/api/authorizations/token/([^/]+)", TokenAPIHandler),
    (r"/api/authorizations/token", TokenAPIHandler),
    (r"/api/oauth2/authorize", OAuthAuthorizeHandler),
    (r"/api/oauth2/token", OAuthTokenHandler),
]
