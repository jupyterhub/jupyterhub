"""Authorization handlers"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import itertools
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
from .. import roles
from .. import scopes
from ..utils import token_authenticated
from .base import APIHandler
from .base import BaseHandler


class TokenAPIHandler(APIHandler):
    @token_authenticated
    def get(self, token):
        # FIXME: deprecate this API for oauth token resolution, in favor of using /api/user
        # TODO: require specific scope for this deprecated API, applied to service tokens only?
        self.log.warning(
            "/authorizations/token/:token endpoint is deprecated in JupyterHub 2.0. Use /api/user"
        )
        orm_token = orm.APIToken.find(self.db, token)
        if orm_token is None:
            raise web.HTTPError(404)

        owner = orm_token.user or orm_token.service
        if owner:
            # having a token means we should be able to read the owner's model
            # (this is the only thing this handler is for)
            self.expanded_scopes.update(scopes.identify_scopes(owner))
            self.parsed_scopes = scopes.parse_scopes(self.expanded_scopes)

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
        raise web.HTTPError(
            404,
            "Deprecated endpoint /hub/api/authorizations/token is removed in JupyterHub 2.0."
            " Use /hub/api/users/:user/tokens instead.",
        )


class CookieAPIHandler(APIHandler):
    @token_authenticated
    def get(self, cookie_name, cookie_value=None):
        self.log.warning(
            "/authorizations/cookie endpoint is deprecated in JupyterHub 2.0. Use /api/user with OAuth tokens."
        )

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

    def needs_oauth_confirm(self, user, oauth_client, roles):
        """Return whether the given oauth client needs to prompt for access for the given user

        Checks list for oauth clients that don't need confirmation

        Sources:

        - the user's own servers
        - Clients which already have authorization for the same roles
        - Explicit oauth_no_confirm_list configuration (e.g. admin-operated services)

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

        # Check existing authorization
        existing_tokens = self.db.query(orm.APIToken).filter_by(
            user_id=user.id,
            client_id=oauth_client.identifier,
        )
        authorized_roles = set()
        for token in existing_tokens:
            authorized_roles.update({role.name for role in token.roles})

        if authorized_roles:
            if set(roles).issubset(authorized_roles):
                self.log.debug(
                    f"User {user.name} has already authorized {oauth_client.identifier} for roles {roles}"
                )
                return False
            else:
                self.log.debug(
                    f"User {user.name} has authorized {oauth_client.identifier}"
                    f" for roles {authorized_roles}, confirming additonal roles {roles}"
                )
        # default: require confirmation
        return True

    def get_login_url(self):
        """
        Support automatically logging in when JupyterHub is used as auth provider
        """
        if self.authenticator.auto_login_oauth2_authorize:
            return self.authenticator.login_url(self.hub.base_url)
        return super().get_login_url()

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
            (
                role_names,
                credentials,
            ) = self.oauth_provider.validate_authorization_request(
                uri, http_method, body, headers
            )
            credentials = self.add_credentials(credentials)
            client = self.oauth_provider.fetch_by_client_id(credentials['client_id'])
            allowed = False

            # check for access to target resource
            if client.spawner:
                scope_filter = self.get_scope_filter("access:servers")
                allowed = scope_filter(client.spawner, kind='server')
            elif client.service:
                scope_filter = self.get_scope_filter("access:services")
                allowed = scope_filter(client.service, kind='service')
            else:
                # client is not associated with a service or spawner.
                # This shouldn't happen, but it might if this is a stale or forged request
                # from a service or spawner that's since been deleted
                self.log.error(
                    f"OAuth client {client} has no service or spawner, cannot resolve scopes."
                )
                raise web.HTTPError(500, "OAuth configuration error")

            if not allowed:
                self.log.error(
                    f"User {self.current_user} not allowed to access {client.description}"
                )
                raise web.HTTPError(
                    403, f"You do not have permission to access {client.description}"
                )
            if not self.needs_oauth_confirm(self.current_user, client, role_names):
                self.log.debug(
                    "Skipping oauth confirmation for %s accessing %s",
                    self.current_user,
                    client.description,
                )
                # this is the pre-1.0 behavior for all oauth
                self._complete_login(uri, headers, role_names, credentials)
                return

            # resolve roles to scopes for authorization page
            raw_scopes = set()
            if role_names:
                role_objects = (
                    self.db.query(orm.Role).filter(orm.Role.name.in_(role_names)).all()
                )
                raw_scopes = set(
                    itertools.chain(*(role.scopes for role in role_objects))
                )
            if not raw_scopes:
                scope_descriptions = [
                    {
                        "scope": None,
                        "description": scopes.scope_definitions['(no_scope)'][
                            'description'
                        ],
                        "filter": "",
                    }
                ]
            elif 'all' in raw_scopes:
                raw_scopes = ['all']
                scope_descriptions = [
                    {
                        "scope": "all",
                        "description": scopes.scope_definitions['all']['description'],
                        "filter": "",
                    }
                ]
            else:
                scope_descriptions = scopes.describe_raw_scopes(
                    raw_scopes,
                    username=self.current_user.name,
                )
            # Render oauth 'Authorize application...' page
            auth_state = await self.current_user.get_auth_state()
            self.write(
                await self.render_template(
                    "oauth.html",
                    auth_state=auth_state,
                    role_names=role_names,
                    scope_descriptions=scope_descriptions,
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
