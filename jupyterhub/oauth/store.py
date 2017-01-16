"""Utilities for hooking up oauth2 to JupyterHub's database

implements https://python-oauth2.readthedocs.io/en/latest/store.html
"""

import threading

from oauth2.datatype import Client, AccessToken, AuthorizationCode
from oauth2.error import AccessTokenNotFound, AuthCodeNotFound, ClientNotFoundError, UserNotAuthenticated
from oauth2.grant import AuthorizationCodeGrant
from oauth2.web import AuthorizationCodeGrantSiteAdapter
import oauth2.store
from oauth2 import Provider
from oauth2.tokengenerator import Uuid4 as UUID4

from sqlalchemy.orm import scoped_session

from . import orm
from ..utils import url_path_join


class JupyterHubSiteAdapter(AuthorizationCodeGrantSiteAdapter):
    """
    This adapter renders a confirmation page so the user can confirm the auth
    request.
    """
    def __init__(self, login_url):
        self.login_url = login_url

    def render_auth_page(self, request, response, environ, scopes, client):
        response.status_code = 302
        response.headers['Location'] = self.login_url
        return response

    def authenticate(self, request, environ, scopes, client):
        print(request, environ, scopes, client)
        handler = request.handler
        user = handler.get_current_user()
        if user:
            return {}, user.id
        else:
            raise UserNotAuthenticated()

    def user_has_denied_access(self, request):
        # user can't deny access
        return False
    

class HubDBMixin(object):
    """Mixin for connecting to the hub database"""
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._local = threading.local()

    @property
    def db(self):
        if not hasattr(self._local, 'db'):
            self._local.db = scoped_session(self.session_factory)()
        return self._local.db


class AccessTokenStore(HubDBMixin, oauth2.store.AccessTokenStore):
    """OAuth2 AccessTokenStore, storing data in the Hub database"""
    
    def _access_token_from_orm(self, orm_token):
        """Transform an ORM AccessToken record into an oauth2 AccessToken instance"""
        return AccessToken(
            client_id=orm_token.client_id,
            token=orm_token.token,
            grant_type=orm_token.grant_type,
            expires_at=orm_token.expires_at,
            refresh_token=orm_token.refresh_token,
            refresh_expires_at=orm_token.refresh_expires_at,
            user_id=orm_token.user_id,
        )

    def save_token(self, access_token):
        """
        Stores an access token in the database.

        :param access_token: An instance of :class:`oauth2.datatype.AccessToken`.

        """
        print('save token', access_token, access_token.data)
        orm_token = orm.OAuthAccessToken(
            client_id=access_token.client_id,
            token=access_token.token,
            grant_type=orm_token.grant_type,
            expires_at=access_token.expires_at,
            refresh_token=access_token.refresh_token,
            refresh_expires_at=access_token.refresh_expires_at,
            user_id=access_token.user_id,
        )
        self.db.add(orm_token)
        self.db.commit()

    def fetch_existing_token_of_user(self, client_id, grant_type, user_id):
        """
        Fetches an access token identified by its client id, type of grant and
        user id.

        This method must be implemented to make use of unique access tokens.

        :param client_id: Identifier of the client a token belongs to.
        :param grant_type: The type of the grant that created the token
        :param user_id: Identifier of the user a token belongs to.
        :return: An instance of :class:`oauth2.datatype.AccessToken`.
        :raises: :class:`oauth2.error.AccessTokenNotFound` if no data could be
                 retrieved.
        """
        orm_token = self.db\
            .query(orm.OAuthAccessToken)\
            .filter(orm.OAuthAccessToken.client_id==client_id)\
            .filter(orm.OAuthAccessToken.user_id==user_id)\
            .first()
        if orm_token is None:
            raise AccessTokenNotFound()
        return self._access_token_from_orm(orm_token)


    def fetch_by_refresh_token(self, refresh_token):
        """
        Fetches an access token from the store using its refresh token to
        identify it.

        :param refresh_token: A string containing the refresh token.
        :return: An instance of :class:`oauth2.datatype.AccessToken`.
        :raises: :class:`oauth2.error.AccessTokenNotFound` if no data could be retrieved for
                 given refresh_token.
        """
        orm_token = self.db\
            .query(orm.OAuthAccessToken)\
            .filter(orm.OAuthAccessToken.refresh_token==refresh_token)\
            .first()
        if orm_token is None:
            raise AccessTokenNotFound()
        return self._access_token_from_orm(orm_token)
        raise NotImplementedError


    def delete_refresh_token(self, refresh_token):
        """
        Deletes an access token from the store using its refresh token to identify it.
        This invalidates both the access token and the refresh token.

        :param refresh_token: A string containing the refresh token.
        :return: None.
        :raises: :class:`oauth2.error.AccessTokenNotFound` if no data could be retrieved for
                 given refresh_token.
        """
        orm_token = self.db\
            .query(orm.OAuthAccessToken)\
            .filter(orm.OAuthAccessToken.refresh_token==refresh_token)\
            .first()
        if orm_token is None:
            raise AccessTokenNotFound()
        self.db.delete(orm_token)
        self.db.commit()


class AuthCodeStore(HubDBMixin, oauth2.store.AuthCodeStore):
    """
    OAuth2 AuthCodeStore, storing data in the Hub database
    """
    def fetch_by_code(self, code):
        """
        Returns an AuthorizationCode fetched from a storage.

        :param code: The authorization code.
        :return: An instance of :class:`oauth2.datatype.AuthorizationCode`.
        :raises: :class:`oauth2.error.AuthCodeNotFound` if no data could be retrieved for
                 given code.

        """
        orm_code = self.db\
            .query(orm.OAuthCode)\
            .filter(orm.OAuthCode.code == code)\
            .first()
        print("fetch code", code, orm_code)
        if orm_code is None:
            raise AuthCodeNotFound()
        else:
            return AuthorizationCode(
                client_id=orm_code.client_id,
                code=code,
                expires_at=orm_code.expires_at,
                redirect_uri=orm_code.redirect_uri,
                scopes=[],
                user_id=orm_code.user_id,
            )


    def save_code(self, authorization_code):
        """
        Stores the data belonging to an authorization code token.

        :param authorization_code: An instance of
                                   :class:`oauth2.datatype.AuthorizationCode`.
        """
        print("save code", authorization_code)
        orm_code = orm.OAuthCode(
            client_id=authorization_code.client_id,
            code=authorization_code.code,
            expires_at=authorization_code.expires_at,
            user_id=authorization_code.user_id,
            redirect_uri=authorization_code.redirect_uri,
        )
        self.db.add(orm_code)
        self.db.commit()


    def delete_code(self, code):
        """
        Deletes an authorization code after it's use per section 4.1.2.

        http://tools.ietf.org/html/rfc6749#section-4.1.2

        :param code: The authorization code.
        """
        print("delete code", code)
        orm_code = self.db.query(orm.OAuthCode).filter(orm.OAuthCode.code == code).first()
        if orm_code is not None:
            self.db.delete(orm_code)
            self.db.commit()


class ClientStore(HubDBMixin, oauth2.store.ClientStore):
    """
    OAuth2 ClientStore, storing data in the Hub database
    """
    def fetch_by_client_id(self, client_id):
        """
        Retrieve a client by its identifier.

        :param client_id: Identifier of a client app.
        :return: An instance of :class:`oauth2.datatype.Client`.
        :raises: :class:`oauth2.error.ClientNotFoundError` if no data could be retrieved for
                 given client_id.
        """
        orm_client = self.db\
            .query(orm.OAuthCode)\
            .filter(orm.OAuthClient.identifier == client_id)\
            .first()
        print("fetch client", client_id, orm_client)
        if orm_client is None:
            raise ClientNotFoundError()
        return Client(identifier=client_id, redirect_uris=[orm_client.redirect_uri], secret=orm_client.secret)
    
    def add_client(self, client_id, client_secret, redirect_uri):
        """Add a client"""
        orm_client = orm.OAuthClient(
            identifier=client_id,
            secret=client_secret,
            redirect_uri=redirect_uri,
        )
        self.db.add(orm_client)
        print("add client", client_id, orm_client)
        self.db.commit()


def make_provider(session_factory, url_prefix, login_url):
    """Make an OAuth provider"""
    token_store = AccessTokenStore(session_factory)
    code_store = AuthCodeStore(session_factory)
    client_store = ClientStore(session_factory)
    
    provider = Provider(
        access_token_store=token_store,
        auth_code_store=code_store,
        client_store=client_store,
        token_generator=UUID4(),
    )
    provider.token_path = url_path_join(url_prefix, 'token')
    provider.authorize_path = url_path_join(url_prefix, 'authorize')
    provider.add_grant(AuthorizationCodeGrant(site_adapter=JupyterHubSiteAdapter(login_url=login_url)))
    return provider

