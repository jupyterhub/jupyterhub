"""Utilities for hooking up oauth2 to JupyterHub's database

implements https://oauthlib.readthedocs.io/en/latest/oauth2/server.html
"""

from oauthlib import uri_validate
from oauthlib.oauth2 import RequestValidator, WebApplicationServer
from oauthlib.oauth2.rfc6749.grant_types import authorization_code, base
from tornado.log import app_log

from .. import orm
from ..roles import roles_to_scopes
from ..scopes import (
    _check_scopes_exist,
    _resolve_requested_scopes,
    access_scopes,
    identify_scopes,
)
from ..utils import compare_token, hash_token

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
        if not client_secret or not oauth_client.secret:
            # disallow authentication with no secret
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
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()
        )
        if orm_client is None:
            raise ValueError(f"No such client: {client_id}")
        scopes = set(orm_client.allowed_scopes)
        if 'inherit' not in scopes:
            # add identify-user scope
            # and access-service scope
            scopes |= identify_scopes() | access_scopes(orm_client)
        return scopes

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
            raise ValueError(f"No such client: {client_id}")

        orm_code = orm.OAuthCode(
            code=code['code'],
            code_challenge=request.code_challenge,
            code_challenge_method=request.code_challenge_method,
            # oauth has 5 minutes to complete
            expires_at=int(orm.OAuthCode.now() + 300),
            scopes=list(request.scopes),
            redirect_uri=orm_client.redirect_uri,
            session_id=request.session_id,
        )
        self.db.add(orm_code)
        orm_code.client = orm_client
        orm_code.user = request.user.orm_user
        self.db.commit()

    def get_authorization_code_scopes(self, client_id, code, redirect_uri, request):
        """Extracts scopes from saved authorization code.
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
        # redact sensitive keys in log
        for key in ('access_token', 'refresh_token', 'state'):
            if key in token:
                value = token[key]
                if isinstance(value, str):
                    log_token[key] = 'REDACTED'
        app_log.debug("Saving bearer token %s", log_token)

        if request.user is None:
            raise ValueError(f"No user for access token: {request.user}")
        client = (
            self.db.query(orm.OAuthClient)
            .filter_by(identifier=request.client.client_id)
            .first()
        )
        # FIXME: support refresh tokens
        # These should be in a new table
        token.pop("refresh_token", None)

        # APIToken.new commits the token to the db
        orm.APIToken.new(
            oauth_client=client,
            expires_in=token['expires_in'],
            scopes=request.scopes,
            token=token['access_token'],
            session_id=request.session_id,
            user=request.user,
        )
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
        if not orm_client.secret:
            app_log.warning("OAuth client %s present without secret", client_id)
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
        request.scopes = orm_code.scopes
        # attach PKCE attributes
        request.code_challenge = orm_code.code_challenge
        request.code_challenge_method = orm_code.code_challenge_method
        return True

    def is_pkce_required(self, client_id, request):
        """Determine if current request requires PKCE. Default, False.
        This is called for both "authorization" and "token" requests.

        Override this method by ``return True`` to enable PKCE for everyone.
        You might want to enable it only for public clients.
        Note that PKCE can also be used in addition of a client authentication.

        OAuth 2.0 public clients utilizing the Authorization Code Grant are
        susceptible to the authorization code interception attack.  This
        specification describes the attack as well as a technique to mitigate
        against the threat through the use of Proof Key for Code Exchange
        (PKCE, pronounced "pixy"). See `RFC7636`_.

        :param client_id: Client identifier.
        :param request: OAuthlib request.
        :type request: oauthlib.common.Request
        :rtype: True or False

        Method is used by:
            - Authorization Code Grant

        .. _`RFC7636`: https://tools.ietf.org/html/rfc7636
        """
        # TODO: add config to enforce PKCE
        return False

    def get_code_challenge(self, code, request):
        """Is called for every "token" requests.

        When the server issues the authorization code in the authorization
        response, it MUST associate the ``code_challenge`` and
        ``code_challenge_method`` values with the authorization code so it can
        be verified later.

        Typically, the ``code_challenge`` and ``code_challenge_method`` values
        are stored in encrypted form in the ``code`` itself but could
        alternatively be stored on the server associated with the code.  The
        server MUST NOT include the ``code_challenge`` value in client requests
        in a form that other entities can extract.

        Return the ``code_challenge`` associated to the code.
        If ``None`` is returned, code is considered to not be associated to any
        challenges.

        :param code: Authorization code.
        :param request: OAuthlib request.
        :type request: oauthlib.common.Request
        :rtype: code_challenge string

        Method is used by:
            - Authorization Code Grant - when PKCE is active

        """
        # attached in validate_code
        return request.code_challenge

    def get_code_challenge_method(self, code, request):
        """Is called during the "token" request processing, when a
        ``code_verifier`` and a ``code_challenge`` has been provided.

        See ``.get_code_challenge``.

        Must return ``plain`` or ``S256``. You can return a custom value if you have
        implemented your own ``AuthorizationCodeGrant`` class.

        :param code: Authorization code.
        :param request: OAuthlib request.
        :type request: oauthlib.common.Request
        :rtype: code_challenge_method string

        Method is used by:
            - Authorization Code Grant - when PKCE is active

        """
        # persisted in validate_code
        return request.code_challenge_method

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
        :param scopes: List of 'raw' scopes (defined by you)
        :param client: Client object set by you, see authenticate_client.
        :param request: The HTTP Request (oauthlib.common.Request)
        :rtype: True or False
        Method is used by all core grant types:
            - Authorization Code Grant
            - Implicit Grant
            - Resource Owner Password Credentials Grant
            - Client Credentials Grant
        """
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).one_or_none()
        )
        if orm_client is None:
            app_log.warning("No such oauth client %s", client_id)
            return False

        requested_scopes = set(scopes)
        # explicitly allow 'identify', which was the only allowed scope previously
        # requesting 'identify' gets no actual permissions other than self-identification
        if "identify" in requested_scopes:
            app_log.warning(
                f"Ignoring deprecated 'identify' scope, requested by {client_id}"
            )
            requested_scopes.discard("identify")

        # TODO: handle roles->scopes transition
        # In 2.x, `?scopes=` only accepted _role_ names,
        # but in 3.0 we accept and prefer scopes.
        # For backward-compatibility, we still accept both.
        # Should roles be deprecated here, or kept as a convenience?
        try:
            _check_scopes_exist(requested_scopes)
        except KeyError as e:
            # scopes don't exist, maybe they are role names
            requested_roles = list(
                self.db.query(orm.Role).filter(orm.Role.name.in_(requested_scopes))
            )
            if len(requested_roles) != len(requested_scopes):
                # did not find roles
                app_log.warning(f"No such scopes: {requested_scopes}")
                return False
            app_log.info(
                f"OAuth client {client_id} requesting roles: {requested_scopes}"
            )
            requested_scopes = roles_to_scopes(requested_roles)

        client_allowed_scopes = set(orm_client.allowed_scopes)

        # scope resolution only works if we have a user defined
        user = request.user or getattr(self, "_current_user")

        # always grant reading the token-owner's name
        # and accessing the service itself
        required_scopes = {*identify_scopes(), *access_scopes(orm_client)}
        requested_scopes.update(required_scopes)
        client_allowed_scopes.update(required_scopes)

        allowed_scopes, disallowed_scopes = _resolve_requested_scopes(
            requested_scopes,
            client_allowed_scopes,
            user=user.orm_user,
            client=orm_client,
            db=self.db,
        )

        if disallowed_scopes:
            app_log.error(
                f"Scope(s) not allowed for {client_id}: {', '.join(disallowed_scopes)}"
            )
            return False

        # store resolved scopes on request
        app_log.debug(
            f"Allowing request for scope(s) for {client_id}:  {','.join(requested_scopes) or '[]'}"
        )
        request.scopes = requested_scopes
        return True


class JupyterHubOAuthServer(WebApplicationServer):
    def __init__(self, db, validator, *args, **kwargs):
        self.db = db
        super().__init__(validator, *args, **kwargs)

    def add_client(
        self,
        client_id,
        client_secret,
        redirect_uri,
        allowed_scopes=None,
        description='',
    ):
        """Add a client

        hash its client_secret before putting it in the database.
        """
        # Update client if it already exists, else create it
        # Sqlalchemy doesn't have a good db agnostic UPSERT,
        # so we do this manually. It's protected inside a
        # transaction, so should fail if there are multiple
        # rows with the same identifier.
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).one_or_none()
        )
        if orm_client is None:
            orm_client = orm.OAuthClient(
                identifier=client_id,
            )
            self.db.add(orm_client)
            app_log.info(f'Creating oauth client {client_id}')
        else:
            app_log.info(f'Updating oauth client {client_id}')
        if allowed_scopes == None:
            allowed_scopes = []
        orm_client.secret = hash_token(client_secret) if client_secret else ""
        orm_client.redirect_uri = redirect_uri
        orm_client.description = description or client_id
        orm_client.allowed_scopes = list(allowed_scopes)
        self.db.commit()
        return orm_client

    def remove_client(self, client_id):
        """Remove a client by its id if it is existed."""
        orm_client = (
            self.db.query(orm.OAuthClient).filter_by(identifier=client_id).one_or_none()
        )
        if orm_client is not None:
            self.db.delete(orm_client)
            self.db.commit()
            app_log.info("Removed client %s", client_id)
        else:
            app_log.warning("No such client %s", client_id)

    def fetch_by_client_id(self, client_id):
        """Find a client by its id"""
        client = self.db.query(orm.OAuthClient).filter_by(identifier=client_id).first()
        if client and client.secret:
            return client


def make_provider(session_factory, url_prefix, login_url, **oauth_server_kwargs):
    """Make an OAuth provider"""
    db = session_factory()
    validator = JupyterHubRequestValidator(db)
    server = JupyterHubOAuthServer(db, validator, **oauth_server_kwargs)
    return server
