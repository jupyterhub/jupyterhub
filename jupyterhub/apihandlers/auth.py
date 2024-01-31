"""Authorization handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from datetime import datetime
from unittest import mock
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from oauthlib import oauth2
from tornado import web

from .. import orm, roles, scopes
from ..utils import get_browser_protocol, token_authenticated
from .base import APIHandler, BaseHandler


class TokenAPIHandler(APIHandler):
    def check_xsrf_cookie(self):
        # no xsrf check needed here
        # post is just a 404
        return

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
            self.expanded_scopes |= scopes.identify_scopes(owner)
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
            get_browser_protocol(self.request)
            + "://"
            + self.request.host
            + redirect_uri
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

    def needs_oauth_confirm(self, user, oauth_client, requested_scopes):
        """Return whether the given oauth client needs to prompt for access for the given user

        Checks list for oauth clients that don't need confirmation

        Sources:

        - the user's own servers
        - Clients which already have authorization for the same roles
        - Explicit oauth_no_confirm_list configuration (e.g. admin-operated services)

        .. versionadded: 1.1
        """
        # get the oauth client ids for the user's own server(s)
        own_oauth_client_ids = {
            spawner.oauth_client_id for spawner in user.spawners.values()
        }
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
        authorized_scopes = set()
        for token in existing_tokens:
            authorized_scopes.update(token.scopes)

        if authorized_scopes:
            if set(requested_scopes).issubset(authorized_scopes):
                self.log.debug(
                    f"User {user.name} has already authorized {oauth_client.identifier} for scopes {requested_scopes}"
                )
                return False
            else:
                self.log.debug(
                    f"User {user.name} has authorized {oauth_client.identifier}"
                    f" for scopes {authorized_scopes}, confirming additional scopes {requested_scopes}"
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
            with mock.patch.object(
                self.oauth_provider.request_validator,
                "_current_user",
                self.current_user,
                create=True,
            ):
                (
                    requested_scopes,
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

            # subset 'raw scopes' to those held by authenticating user
            requested_scopes = set(requested_scopes)
            user = self.current_user
            # raw, _not_ expanded scopes
            user_scopes = roles.roles_to_scopes(roles.get_roles_for(user.orm_user))
            # these are some scopes the user may not have
            # in 'raw' form, but definitely have at this point
            # make sure they are here, because we are computing the
            # 'raw' scope intersection,
            # rather than the expanded_scope intersection

            required_scopes = {*scopes.identify_scopes(), *scopes.access_scopes(client)}
            user_scopes |= {"inherit", *required_scopes}

            allowed_scopes, disallowed_scopes = scopes._resolve_requested_scopes(
                requested_scopes,
                user_scopes,
                user=user.orm_user,
                client=client,
                db=self.db,
            )

            if disallowed_scopes:
                self.log.warning(
                    f"Service {client.description} requested scopes {','.join(requested_scopes)}"
                    f" for user {self.current_user.name},"
                    f" granting only {','.join(allowed_scopes) or '[]'}."
                )

            if not self.needs_oauth_confirm(self.current_user, client, allowed_scopes):
                self.log.debug(
                    "Skipping oauth confirmation for %s accessing %s",
                    self.current_user,
                    client.description,
                )
                # this is the pre-1.0 behavior for all oauth
                self._complete_login(uri, headers, allowed_scopes, credentials)
                return

            # discard 'required' scopes from description
            # no need to describe the ability to access itself
            scopes_to_describe = allowed_scopes.difference(required_scopes)

            if not scopes_to_describe:
                # TODO: describe all scopes?
                # Not right now, because the no-scope default 'identify' text
                # is clearer than what we produce for those scopes individually
                scope_descriptions = [
                    {
                        "scope": None,
                        "description": scopes.scope_definitions['(no_scope)'][
                            'description'
                        ],
                        "filter": "",
                    }
                ]
            elif 'inherit' in scopes_to_describe:
                allowed_scopes = scopes_to_describe = ['inherit']
                scope_descriptions = [
                    {
                        "scope": "inherit",
                        "description": scopes.scope_definitions['inherit'][
                            'description'
                        ],
                        "filter": "",
                    }
                ]
            else:
                scope_descriptions = scopes.describe_raw_scopes(
                    scopes_to_describe,
                    username=self.current_user.name,
                )
            # Render oauth 'Authorize application...' page
            auth_state = await self.current_user.get_auth_state()
            self.write(
                await self.render_template(
                    "oauth.html",
                    auth_state=auth_state,
                    allowed_scopes=allowed_scopes,
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
        # The scopes the user actually authorized, i.e. checkboxes
        # that were selected.
        scopes = self.get_arguments('scopes')
        if scopes == []:
            # avoid triggering default scopes (provider selects default scopes when scopes is falsy)
            # when an explicit empty list is authorized
            scopes = ["identify"]
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
