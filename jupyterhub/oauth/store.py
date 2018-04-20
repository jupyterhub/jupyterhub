"""Utilities for hooking up oauth2 to JupyterHub's database

implements https://python-oauth2.readthedocs.io/en/latest/store.html
"""

import threading

from oauth2.datatype import Client, AuthorizationCode
from oauth2.error import AuthCodeNotFound, ClientNotFoundError, UserNotAuthenticated
from oauth2.grant import AuthorizationCodeGrant
from oauth2.web import AuthorizationCodeGrantSiteAdapter
import oauth2.store
from oauth2 import Provider
from oauth2.tokengenerator import Uuid4 as UUID4

from sqlalchemy.orm import scoped_session
from tornado.escape import url_escape

from .. import orm
from ..utils import url_path_join, hash_token, compare_token


class JupyterHubSiteAdapter(AuthorizationCodeGrantSiteAdapter):
    """
    This adapter renders a confirmation page so the user can confirm the auth
    request.
    """
    def __init__(self, login_url):
        self.login_url = login_url

    def render_auth_page(self, request, response, environ, scopes, client):
        """Auth page is a redirect to login page"""
        response.status_code = 302
        response.headers['Location'] = self.login_url + '?next={}'.format(
            url_escape(request.handler.request.path + '?' + request.handler.request.query)
        )
        return response

    def authenticate(self, request, environ, scopes, client):
        handler = request.handler
        user = handler.get_current_user()
        # ensure session_id is set
        session_id = handler.get_session_cookie()
        if session_id is None:
            session_id = handler.set_session_cookie()
        if user:
            return {'session_id': session_id}, user.id
        else:
            raise UserNotAuthenticated()

    def user_has_denied_access(self, request):
        # user can't deny access
        return False


class HubDBMixin(object):
    """Mixin for connecting to the hub database"""
    def __init__(self, session_factory):
        self.db = session_factory()


class AccessTokenStore(HubDBMixin, oauth2.store.AccessTokenStore):
    """OAuth2 AccessTokenStore, storing data in the Hub database"""

    def save_token(self, access_token):
        """
        Stores an access token in the database.

        :param access_token: An instance of :class:`oauth2.datatype.AccessToken`.

        """

        user = self.db.query(orm.User).filter_by(id=access_token.user_id).first()
        if user is None:
            raise ValueError("No user for access token: %s" % access_token.user_id)
        client = self.db.query(orm.OAuthClient).filter_by(identifier=access_token.client_id).first()
        orm_access_token = orm.OAuthAccessToken(
            client=client,
            grant_type=access_token.grant_type,
            expires_at=access_token.expires_at,
            refresh_token=access_token.refresh_token,
            refresh_expires_at=access_token.refresh_expires_at,
            token=access_token.token,
            session_id=access_token.data['session_id'],
            user=user,
        )
        self.db.add(orm_access_token)
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
        orm_code = (
            self.db
            .query(orm.OAuthCode)
            .filter_by(code=code)
            .first()
        )
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
                data={'session_id': orm_code.session_id},
            )

    def save_code(self, authorization_code):
        """
        Stores the data belonging to an authorization code token.

        :param authorization_code: An instance of
                                   :class:`oauth2.datatype.AuthorizationCode`.
        """
        orm_client = (
            self.db
            .query(orm.OAuthClient)
            .filter_by(identifier=authorization_code.client_id)
            .first()
        )
        if orm_client is None:
            raise ValueError("No such client: %s" % authorization_code.client_id)

        orm_user = (
            self.db
            .query(orm.User)
            .filter_by(id=authorization_code.user_id)
            .first()
        )
        if orm_user is None:
            raise ValueError("No such user: %s" % authorization_code.user_id)

        orm_code = orm.OAuthCode(
            client=orm_client,
            code=authorization_code.code,
            expires_at=authorization_code.expires_at,
            user=orm_user,
            redirect_uri=authorization_code.redirect_uri,
            session_id=authorization_code.data.get('session_id', ''),
        )
        self.db.add(orm_code)
        self.db.commit()


    def delete_code(self, code):
        """
        Deletes an authorization code after its use per section 4.1.2.

        http://tools.ietf.org/html/rfc6749#section-4.1.2

        :param code: The authorization code.
        """
        orm_code = self.db.query(orm.OAuthCode).filter_by(code=code).first()
        if orm_code is not None:
            self.db.delete(orm_code)
            self.db.commit()


class HashComparable:
    """An object for storing hashed tokens

    Overrides `==` so that it compares as equal to its unhashed original

    Needed for storing hashed client_secrets
    because python-oauth2 uses::

        secret == client.client_secret

    and we don't want to store unhashed secrets in the database.
    """
    def __init__(self, hashed_token):
        self.hashed_token = hashed_token

    def __repr__(self):
        return "<{} '{}'>".format(self.__class__.__name__, self.hashed_token)

    def __eq__(self, other):
        return compare_token(self.hashed_token, other)


class ClientStore(HubDBMixin, oauth2.store.ClientStore):
    """OAuth2 ClientStore, storing data in the Hub database"""

    def fetch_by_client_id(self, client_id):
        """Retrieve a client by its identifier.

        :param client_id: Identifier of a client app.
        :return: An instance of :class:`oauth2.datatype.Client`.
        :raises: :class:`oauth2.error.ClientNotFoundError` if no data could be retrieved for
                 given client_id.
        """
        orm_client = (
            self.db
            .query(orm.OAuthClient)
            .filter_by(identifier=client_id)
            .first()
        )
        if orm_client is None:
            raise ClientNotFoundError()
        return Client(identifier=client_id,
                      redirect_uris=[orm_client.redirect_uri],
                      secret=HashComparable(orm_client.secret),
                      )

    def add_client(self, client_id, client_secret, redirect_uri, description=''):
        """Add a client

        hash its client_secret before putting it in the database.
        """
        # clear existing clients with same ID
        for orm_client in (
            self.db
            .query(orm.OAuthClient)\
            .filter_by(identifier=client_id)
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
    site_adapter = JupyterHubSiteAdapter(login_url=login_url)
    provider.add_grant(AuthorizationCodeGrant(site_adapter=site_adapter))
    return provider

