"""Utilities for hooking up oauth2 to JupyterHub's database

implements https://oauthlib.readthedocs.io/en/latest/oauth2/server.html
"""
from oauthlib import uri_validate
from oauthlib.oauth2 import RequestValidator
from oauthlib.oauth2 import WebApplicationServer
from oauthlib.oauth2.rfc6749.grant_types import authorization_code
from oauthlib.oauth2.rfc6749.grant_types import base
from tornado.escape import url_escape
from tornado.log import app_log

from .. import orm
from ..utils import compare_token
from ..utils import hash_token
from ..utils import url_path_join

# patch absolute-uri check
# because we want to allow relative uri oauth
# for internal services


def is_absolute_uri(uri):
    if uri.startswith('/'):
        return True
    return uri_validate.is_absolute_uri(uri)


authorization_code.is_absolute_uri = is_absolute_uri
base.is_absolute_uri = is_absolute_uri


class JupyterHubRequestValidator(RequestValidator):
    def __init__(self, db):
        self.db = db
        super().__init__()

    def authenticate_client(self, request, *args, **kwargs):
        """Authenticate client through means outside the OAuth 2 spec.
        Means of authentication is negotiated beforehand and may for example
        be `HTTP Basic Authentication Scheme`_ which utilizes the Authorization
        header.
        Headers may be accesses through request.headers and parameters found in
        both body and query can be obtained by direct attribute access, i.e.
        request.client_id for client_id in the URL query.
        :param request: oauthlib.common.Request
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant
            - Resource Owner Password Credentials Grant (may be disabled)
            - Client Credentials Grant
            - Refresh Token Grant
        .. _`HTTP Basic Authentication Scheme`: https://tools.ietf.org/html/rfc1945#section-11.1
        """
        app_log.debug("authenticate_client %s", request)
        client_id = request.client_id
        client_secret = request.client_secret
        oauth_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()
        )
        if oauth_client is None:
            return False
        if not compare_token(oauth_client.secret, client_secret):
            app_log.warning("Client secret mismatch for %s", client_id)
            return False

        request.client = oauth_client
        return True

    def authenticate_client_id(self, client_id, request, *args, **kwargs):
        """Ensure client_id belong to a non-confidential client.
        A non-confidential client is one that is not required to authenticate
        through other means, such as using HTTP Basic.
        Note, while not strictly necessary it can often be very convenient
        to set request.client to the client object associated with the
        given client_id.
        :param request: oauthlib.common.Request
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant
        """
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()
        )
        if orm_client is None:
            app_log.warning("No such oauth client %s", client_id)
            return False
        request.client = orm_client
        return True

    def confirm_redirect_uri(
        self, client_id, code, redirect_uri, client, *args, **kwargs
    ):
        """Ensure that the authorization process represented by this authorization
        code began with this 'redirect_uri'.
        If the client specifies a redirect_uri when obtaining code then that
        redirect URI must be bound to the code and verified equal in this
        method, according to RFC 6749 section 4.1.3.  Do not compare against
        the client's allowed redirect URIs, but against the URI used when the
        code was saved.
        :param client_id: Unicode client identifier
        :param code: Unicode authorization_code.
        :param redirect_uri: Unicode absolute URI
        :param client: Client object set by you, see authenticate_client.
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant (during token request)
        """
        # TODO: record redirect_uri used during oauth
        # if we ever support multiple destinations
        app_log.debug(
            "confirm_redirect_uri: client_id=%s, redirect_uri=%s",
            client_id,
            redirect_uri,
        )
        if redirect_uri == client.redirect_uri:
            return True
        else:
            app_log.warning("Redirect uri %s != %s", redirect_uri, client.redirect_uri)
            return False

    def get_default_redirect_uri(self, client_id, request, *args, **kwargs):
        """Get the default redirect URI for the client.
        :param client_id: Unicode client identifier
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: The default redirect URI for the client
        Method is used by:
            - Authorization Code Grant
            - Implicit Grant
        """
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()
        )
        if orm_client is None:
            raise KeyError(client_id)
        return orm_client.redirect_uri

    def get_default_scopes(self, client_id, request, *args, **kwargs):
        """Get the default scopes for the client.
        :param client_id: Unicode client identifier
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: List of default scopes
        Method is used by all core grant types:
            - Authorization Code Grant
            - Implicit Grant
            - Resource Owner Password Credentials Grant
            - Client Credentials grant
        """
        return ['identify']

    def get_original_scopes(self, refresh_token, request, *args, **kwargs):
        """Get the list of scopes associated with the refresh token.
        :param refresh_token: Unicode refresh token
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: List of scopes.
        Method is used by:
            - Refresh token grant
        """
        raise NotImplementedError()

    def is_within_original_scope(
        self, request_scopes, refresh_token, request, *args, **kwargs
    ):
        """Check if requested scopes are within a scope of the refresh token.
        When access tokens are refreshed the scope of the new token
        needs to be within the scope of the original token. This is
        ensured by checking that all requested scopes strings are on
        the list returned by the get_original_scopes. If this check
        fails, is_within_original_scope is called. The method can be
        used in situations where returning all valid scopes from the
        get_original_scopes is not practical.
        :param request_scopes: A list of scopes that were requested by client
        :param refresh_token: Unicode refresh_token
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is used by:
            - Refresh token grant
        """
        raise NotImplementedError()

    def invalidate_authorization_code(self, client_id, code, request, *args, **kwargs):
        """Invalidate an authorization code after use.
        :param client_id: Unicode client identifier
        :param code: The authorization code grant (request.code).
        :param request: The HTTP Request (oauthlib.common.Request)
        Method is used by:
            - Authorization Code Grant
        """
        app_log.debug("Deleting oauth code %s... for %s", code[:3], client_id)
        orm_code = self.db.query(orm.OAuthCode).filter_by(code=code).first()
        if orm_code is not None:
            self.db.delete(orm_code)
            self.db.commit()

    def revoke_token(self, token, token_type_hint, request, *args, **kwargs):
        """Revoke an access or refresh token.
        :param token: The token string.
        :param token_type_hint: access_token or refresh_token.
        :param request: The HTTP Request (oauthlib.common.Request)
        Method is used by:
            - Revocation Endpoint
        """
        app_log.debug("Revoking %s %s", token_type_hint, token[:3] + '...')
        raise NotImplementedError('Subclasses must implement this method.')

    def save_authorization_code(self, client_id, code, request, *args, **kwargs):
        """Persist the authorization_code.
        The code should at minimum be stored with:
            - the client_id (client_id)
            - the redirect URI used (request.redirect_uri)
            - a resource owner / user (request.user)
            - the authorized scopes (request.scopes)
            - the client state, if given (code.get('state'))
        The 'code' argument is actually a dictionary, containing at least a
        'code' key with the actual authorization code:
            {'code': 'sdf345jsdf0934f'}
        It may also have a 'state' key containing a nonce for the client, if it
        chose to send one.  That value should be saved and used in
        'validate_code'.
        It may also have a 'claims' parameter which, when present, will be a dict
        deserialized from JSON as described at
        http://openid.net/specs/openid-connect-core-1_0.html#ClaimsParameter
        This value should be saved in this method and used again in 'validate_code'.
        :param client_id: Unicode client identifier
        :param code: A dict of the authorization code grant and, optionally, state.
        :param request: The HTTP Request (oauthlib.common.Request)
        Method is used by:
            - Authorization Code Grant
        """
        log_code = code.get('code', 'undefined')[:3] + '...'
        app_log.debug(
            "Saving authorization code %s, %s, %s, %s",
            client_id,
            log_code,
            args,
            kwargs,
        )
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()
        )
        if orm_client is None:
            raise ValueError("No such client: %s" % client_id)

        orm_code = orm.OAuthCode(
            client=orm_client,
            code=code['code'],
            # oauth has 5 minutes to complete
            expires_at=int(orm.OAuthCode.now() + 300),
            # TODO: persist oauth scopes
            # scopes=request.scopes,
            user=request.user.orm_user,
            redirect_uri=orm_client.redirect_uri,
            session_id=request.session_id,
        )
        self.db.add(orm_code)
        self.db.commit()

    def get_authorization_code_scopes(self, client_id, code, redirect_uri, request):
        """ Extracts scopes from saved authorization code.
        The scopes returned by this method is used to route token requests
        based on scopes passed to Authorization Code requests.
        With that the token endpoint knows when to include OpenIDConnect
        id_token in token response only based on authorization code scopes.
        Only code param should be sufficient to retrieve grant code from
        any storage you are using, `client_id` and `redirect_uri` can gave a
        blank value `""` don't forget to check it before using those values
        in a select query if a database is used.
        :param client_id: Unicode client identifier
        :param code: Unicode authorization code grant
        :param redirect_uri: Unicode absolute URI
        :return: A list of scope
        Method is used by:
            - Authorization Token Grant Dispatcher
        """
        raise NotImplementedError("TODO")

    def save_token(self, token, request, *args, **kwargs):
        """Persist the token with a token type specific method.
        Currently, only save_bearer_token is supported.
        """
        return self.save_bearer_token(token, request, *args, **kwargs)

    def save_bearer_token(self, token, request, *args, **kwargs):
        """Persist the Bearer token.
        The Bearer token should at minimum be associated with:
            - a client and it's client_id, if available
            - a resource owner / user (request.user)
            - authorized scopes (request.scopes)
            - an expiration time
            - a refresh token, if issued
            - a claims document, if present in request.claims
        The Bearer token dict may hold a number of items::
            {
                'token_type': 'Bearer',
                'access_token': 'askfjh234as9sd8',
                'expires_in': 3600,
                'scope': 'string of space separated authorized scopes',
                'refresh_token': '23sdf876234',  # if issued
                'state': 'given_by_client',  # if supplied by client
            }
        Note that while "scope" is a string-separated list of authorized scopes,
        the original list is still available in request.scopes.
        The token dict is passed as a reference so any changes made to the dictionary
        will go back to the user.  If additional information must return to the client
        user, and it is only possible to get this information after writing the token
        to storage, it should be added to the token dictionary.  If the token
        dictionary must be modified but the changes should not go back to the user,
        a copy of the dictionary must be made before making the changes.
        Also note that if an Authorization Code grant request included a valid claims
        parameter (for OpenID Connect) then the request.claims property will contain
        the claims dict, which should be saved for later use when generating the
        id_token and/or UserInfo response content.
        :param token: A Bearer token dict
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: The default redirect URI for the client
        Method is used by all core grant types issuing Bearer tokens:
            - Authorization Code Grant
            - Implicit Grant
            - Resource Owner Password Credentials Grant (might not associate a client)
            - Client Credentials grant
        """
        log_token = {}
        log_token.update(token)
        scopes = token['scope'].split(' ')
        # TODO:
        if scopes != ['identify']:
            raise ValueError("Only 'identify' scope is supported")
        # redact sensitive keys in log
        for key in ('access_token', 'refresh_token', 'state'):
            if key in token:
                value = token[key]
                if isinstance(value, str):
                    log_token[key] = 'REDACTED'
        app_log.debug("Saving bearer token %s", log_token)
        if request.user is None:
            raise ValueError("No user for access token: %s" % request.user)
        client = (
            self.db.query(orm.OAuthClient)
            .filter_by(identifier=request.client.client_id)
            .first()
        )
        orm_access_token = orm.OAuthAccessToken(
            client=client,
            grant_type=orm.GrantType.authorization_code,
            expires_at=orm.OAuthAccessToken.now() + token['expires_in'],
            refresh_token=token['refresh_token'],
            # TODO: save scopes,
            # scopes=scopes,
            token=token['access_token'],
            session_id=request.session_id,
            user=request.user,
        )
        self.db.add(orm_access_token)
        self.db.commit()
        return client.redirect_uri

    def validate_bearer_token(self, token, scopes, request):
        """Ensure the Bearer token is valid and authorized access to scopes.
        :param token: A string of random characters.
        :param scopes: A list of scopes associated with the protected resource.
        :param request: The HTTP Request (oauthlib.common.Request)
        A key to OAuth 2 security and restricting impact of leaked tokens is
        the short expiration time of tokens, *always ensure the token has not
        expired!*.
        Two different approaches to scope validation:
            1) all(scopes). The token must be authorized access to all scopes
                            associated with the resource. For example, the
                            token has access to ``read-only`` and ``images``,
                            thus the client can view images but not upload new.
                            Allows for fine grained access control through
                            combining various scopes.
            2) any(scopes). The token must be authorized access to one of the
                            scopes associated with the resource. For example,
                            token has access to ``read-only-images``.
                            Allows for fine grained, although arguably less
                            convenient, access control.
        A powerful way to use scopes would mimic UNIX ACLs and see a scope
        as a group with certain privileges. For a restful API these might
        map to HTTP verbs instead of read, write and execute.
        Note, the request.user attribute can be set to the resource owner
        associated with this token. Similarly the request.client and
        request.scopes attribute can be set to associated client object
        and authorized scopes. If you then use a decorator such as the
        one provided for django these attributes will be made available
        in all protected views as keyword arguments.
        :param token: Unicode Bearer token
        :param scopes: List of scopes (defined by you)
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is indirectly used by all core Bearer token issuing grant types:
            - Authorization Code Grant
            - Implicit Grant
            - Resource Owner Password Credentials Grant
            - Client Credentials Grant
        """
        raise NotImplementedError('Subclasses must implement this method.')

    def validate_client_id(self, client_id, request, *args, **kwargs):
        """Ensure client_id belong to a valid and active client.
        Note, while not strictly necessary it can often be very convenient
        to set request.client to the client object associated with the
        given client_id.
        :param request: oauthlib.common.Request
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant
            - Implicit Grant
        """
        app_log.debug("Validating client id %s", client_id)
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()
        )
        if orm_client is None:
            return False
        request.client = orm_client
        return True

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        """Verify that the authorization_code is valid and assigned to the given
        client.
        Before returning true, set the following based on the information stored
        with the code in 'save_authorization_code':
            - request.user
            - request.state (if given)
            - request.scopes
            - request.claims (if given)
        OBS! The request.user attribute should be set to the resource owner
        associated with this authorization code. Similarly request.scopes
        must also be set.
        The request.claims property, if it was given, should assigned a dict.
        :param client_id: Unicode client identifier
        :param code: Unicode authorization code
        :param client: Client object set by you, see authenticate_client.
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant
        """
        orm_code = orm.OAuthCode.find(self.db, code=code)
        if orm_code is None:
            app_log.debug("No such code: %s", code)
            return False
        if orm_code.client_id != client_id:
            app_log.debug(
                "OAuth code client id mismatch: %s != %s", client_id, orm_code.client_id
            )
            return False
        request.user = orm_code.user
        request.session_id = orm_code.session_id
        # TODO: record state on oauth codes
        # TODO: specify scopes
        request.scopes = ['identify']
        return True

    def validate_grant_type(
        self, client_id, grant_type, client, request, *args, **kwargs
    ):
        """Ensure client is authorized to use the grant_type requested.
        :param client_id: Unicode client identifier
        :param grant_type: Unicode grant type, i.e. authorization_code, password.
        :param client: Client object set by you, see authenticate_client.
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant
            - Resource Owner Password Credentials Grant
            - Client Credentials Grant
            - Refresh Token Grant
        """
        return grant_type == 'authorization_code'

    def validate_redirect_uri(self, client_id, redirect_uri, request, *args, **kwargs):
        """Ensure client is authorized to redirect to the redirect_uri requested.
        All clients should register the absolute URIs of all URIs they intend
        to redirect to. The registration is outside of the scope of oauthlib.
        :param client_id: Unicode client identifier
        :param redirect_uri: Unicode absolute URI
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant
            - Implicit Grant
        """
        app_log.debug(
            "validate_redirect_uri: client_id=%s, redirect_uri=%s",
            client_id,
            redirect_uri,
        )
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()
        )
        if orm_client is None:
            app_log.warning("No such oauth client %s", client_id)
            return False
        if redirect_uri == orm_client.redirect_uri:
            return True
        else:
            app_log.warning(
                "Redirect uri %s != %s", redirect_uri, orm_client.redirect_uri
            )
            return False

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        """Ensure the Bearer token is valid and authorized access to scopes.
        OBS! The request.user attribute should be set to the resource owner
        associated with this refresh token.
        :param refresh_token: Unicode refresh token
        :param client: Client object set by you, see authenticate_client.
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant (indirectly by issuing refresh tokens)
            - Resource Owner Password Credentials Grant (also indirectly)
            - Refresh Token Grant
        """
        return False
        raise NotImplementedError('Subclasses must implement this method.')

    def validate_response_type(
        self, client_id, response_type, client, request, *args, **kwargs
    ):
        """Ensure client is authorized to use the response_type requested.
        :param client_id: Unicode client identifier
        :param response_type: Unicode response type, i.e. code, token.
        :param client: Client object set by you, see authenticate_client.
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is used by:
            - Authorization Code Grant
            - Implicit Grant
        """
        # TODO
        return True

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        """Ensure the client is authorized access to requested scopes.
        :param client_id: Unicode client identifier
        :param scopes: List of scopes (defined by you)
        :param client: Client object set by you, see authenticate_client.
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is used by all core grant types:
            - Authorization Code Grant
            - Implicit Grant
            - Resource Owner Password Credentials Grant
            - Client Credentials Grant
        """
        return True


class JupyterHubOAuthServer(WebApplicationServer):
    def __init__(self, db, validator, *args, **kwargs):
        self.db = db
        super().__init__(validator, *args, **kwargs)

    def add_client(self, client_id, client_secret, redirect_uri, description=''):
        """Add a client

        hash its client_secret before putting it in the database.
        """
        # clear existing clients with same ID
        for orm_client in self.db.query(orm.OAuthClient).filter_by(
            identifier=client_id
        ):
            self.db.delete(orm_client)
        self.db.commit()

        orm_client = orm.OAuthClient(
            identifier=client_id,
            secret=hash_token(client_secret),
            redirect_uri=redirect_uri,
            description=description,
        )
        self.db.add(orm_client)
        self.db.commit()

    def fetch_by_client_id(self, client_id):
        """Find a client by its id"""
        return self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()


def make_provider(session_factory, url_prefix, login_url):
    """Make an OAuth provider"""
    db = session_factory()
    validator = JupyterHubRequestValidator(db)
    server = JupyterHubOAuthServer(db, validator)
    return server
