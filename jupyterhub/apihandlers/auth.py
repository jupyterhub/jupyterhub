"""Authorization handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from datetime import datetime
import json
from urllib.parse import (
    parse_qsl,
    quote,
    urlencode,
    urlparse,
    urlunparse,
)

from oauthlib import oauth2
from tornado import web

from .. import orm
from ..user import User
from ..utils import token_authenticated, compare_token
from .base import BaseHandler, APIHandler


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
        requester = user = self.get_current_user()
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
                    raise web.HTTPError(403, "Only admins can request tokens for other users.")
                if requester.admin and user is None:
                    raise web.HTTPError(400, "No such user '%s'" % data['username'])

        note = (data or {}).get('note')
        if not note:
            note = "Requested via deprecated api"
            if requester is not user:
                kind = 'user' if isinstance(user, User) else 'service'
                note += " by %s %s" % (kind, requester.name)

        api_token = user.new_api_token(note=note)
        self.write(json.dumps({
            'token': api_token,
            'warning': warn_msg,
            'user': self.user_model(user),
        }))


class CookieAPIHandler(APIHandler):
    @token_authenticated
    def get(self, cookie_name, cookie_value=None):
        cookie_name = quote(cookie_name, safe='')
        if cookie_value is None:
            self.log.warning("Cookie values in request body is deprecated, use `/cookie_name/cookie_value`")
            cookie_value = self.request.body
        else:
            cookie_value = cookie_value.encode('utf8')
        user = self._user_for_cookie(cookie_name, cookie_value)
        if user is None:
            raise web.HTTPError(404)
        self.write(json.dumps(self.user_model(user)))


class OAuthHandler(BaseHandler):
    def extract_oauth_params(self):
        """extract oauthlib params from a request

        Returns:

        (uri, http_method, body, headers)
        """
        return (
            self.make_absolute_redirect_uri(self.request.uri),
            self.request.method,
            self.request.body,
            self.request.headers,
        )

    def make_absolute_redirect_uri(self, uri):
        """Make absolute redirect URIs

        internal redirect uris, e.g. `/user/foo/oauth_handler`
        are allowed in jupyterhub, but oauthlib prohibits them.
        Add `$HOST` header to redirect_uri to make them acceptable.
        """
        redirect_uri = self.get_argument('redirect_uri')
        if not redirect_uri or not redirect_uri.startswith('/'):
            return uri
        # make absolute local redirects full URLs
        # to satisfy oauthlib's absolute URI requirement
        redirect_uri = self.request.protocol + "://" + self.request.headers['Host'] + redirect_uri
        parsed_url = urlparse(uri)
        query_list = parse_qsl(parsed_url.query, keep_blank_values=True)
        for idx, item in enumerate(query_list):
            if item[0] == 'redirect_uri':
                query_list[idx] = ('redirect_uri', redirect_uri)
                break

        return urlunparse(
            urlparse(uri)
            ._replace(query=urlencode(query_list))
        )


class OAuthAuthorizeHandler(OAuthHandler):
    """Implement OAuth provider handlers

    OAuth2Handler sets `self.provider` in initialize,
    but we are already passing the Provider object via settings.
    """

    @web.authenticated
    def get(self):
        # You need to define extract_params and make sure it does not
        # include file like objects waiting for input. In Django this
        # is request.META['wsgi.input'] and request.META['wsgi.errors']
        uri, http_method, body, headers = self.extract_oauth_params()

        try:
            scopes, credentials = self.oauth_provider.validate_authorization_request(
                uri, http_method, body, headers)

            if scopes == ['identify']:
                pass
            client_id = 'hmmm'
            # You probably want to render a template instead.
            self.write('<h1> Authorize access to %s </h1>' % client_id)
            self.write('<form method="POST" action="">')
            for scope in scopes or []:
                self.write('<input type="checkbox" name="scopes" ' +
                'value="%s"/> %s' % (scope, scope))
                self.write('<input type="submit" value="Authorize"/>')

        # Errors that should be shown to the user on the provider website
        except oauth2.FatalClientError as e:
            # TODO: human error page
            raise
            # return response_from_error(e)

        # Errors embedded in the redirect URI back to the client
        except oauth2.OAuth2Error as e:
            self.log.error("oauth error: %s" % e)
            self.redirect(e.in_uri(e.redirect_uri))

    @web.authenticated
    def post(self):
        uri, http_method, body, headers = self.extract_oauth_params()

        # The scopes the user actually authorized, i.e. checkboxes
        # that were selected.
        scopes = self.get_arguments('scopes')

        session_id = self.get_session_cookie()
        if session_id is None:
            session_id = self.set_session_cookie()

        user = self.get_current_user()


        # Extra credentials we need in the validator
        credentials = {
            'user': user,
            'handler': self,
            'session_id': session_id,
        }

        # The previously stored (in authorization GET view) credentials
        # credentials.update(request.session.get('oauth2_credentials', {}))

        try:
            headers, body, status = self.oauth_provider.create_authorization_response(
            uri, http_method, body, headers, scopes, credentials)
            self.set_status(status)
            for key, value in headers.items():
                self.set_header(key, value)
            if body:
                self.write(body)

        except oauth2.FatalClientError as e:
            # TODO: human error page
            raise


class OAuthTokenHandler(OAuthHandler):

    # get JSON error messages
    write_error = APIHandler.write_error

    def post(self):
        uri, http_method, body, headers = self.extract_oauth_params()
        credentials = {}

        headers, body, status = self.oauth_provider.create_token_response(
                uri, http_method, body, headers, credentials)

        self.set_status(status)
        for key, value in headers.items():
            self.set_header(key, value)
        if body:
            self.write(body)


default_handlers = [
    (r"/api/authorizations/cookie/([^/]+)(?:/([^/]+))?", CookieAPIHandler),
    (r"/api/authorizations/token/([^/]+)", TokenAPIHandler),
    (r"/api/authorizations/token", TokenAPIHandler),
    (r"/api/oauth2/authorize", OAuthAuthorizeHandler),
    (r"/api/oauth2/token", OAuthTokenHandler),
]
