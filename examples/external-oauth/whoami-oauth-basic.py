"""Basic implementation of OAuth without any inheritance

Implements OAuth handshake manually
so all URLs and requests necessary for OAuth with JupyterHub should be in one place
"""

import json
import os
import secrets
from urllib.parse import urlencode, urlparse

from oauthlib.oauth2 import Client
from tornado import log, web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import url_concat
from tornado.ioloop import IOLoop

# dict by state id
state_dict = {}

oauth = Client("client_id_unused")
PKCE_CHALLENGE_METHOD = "S256"


class JupyterHubLoginHandler(web.RequestHandler):
    """Login Handler

    this handler both begins and ends the OAuth process
    """

    async def token_for_code(self, code, code_verifier):
        """Complete OAuth by requesting an access token for an oauth code"""
        params = dict(
            client_id=self.settings['client_id'],
            client_secret=self.settings['api_token'],
            grant_type='authorization_code',
            code=code,
            code_verifier=code_verifier,
            redirect_uri=self.settings['redirect_uri'],
        )
        req = HTTPRequest(
            self.settings['token_url'],
            method='POST',
            body=urlencode(params).encode('utf8'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        response = await AsyncHTTPClient().fetch(req)
        data = json.loads(response.body.decode('utf8', 'replace'))
        return data['access_token']

    async def get(self):
        code = self.get_argument('code', None)
        if code:
            # code is set, we are the oauth callback
            # complete oauth

            # get PKCE code_verifier
            state_id = self.get_argument("state", None)
            state = state_dict.pop(state_id, None)
            if not state:
                raise web.HTTPError(400, "Invalid oauth state")

            # get pkce code verifier
            code_verifier = state["code_verifier"]

            token = await self.token_for_code(code, code_verifier)
            # login successful, set cookie and redirect back to home
            self.set_secure_cookie('whoami-oauth-token', token)
            self.redirect('/')
        else:
            # we are the login handler,
            # begin oauth process which will come back later with an
            # authorization_code
            # create pkce arguments
            state_id = secrets.token_urlsafe(16)
            code_verifier = oauth.create_code_verifier(64)
            state_dict[state_id] = {
                "code_verifier": code_verifier,
            }
            code_challenge = oauth.create_code_challenge(
                code_verifier, PKCE_CHALLENGE_METHOD
            )
            self.redirect(
                url_concat(
                    self.settings['authorize_url'],
                    dict(
                        redirect_uri=self.settings['redirect_uri'],
                        client_id=self.settings['client_id'],
                        response_type='code',
                        code_challenge=code_challenge,
                        code_challenge_method=PKCE_CHALLENGE_METHOD,
                        state=state_id,
                    ),
                )
            )


class WhoAmIHandler(web.RequestHandler):
    """Serve the JSON model for the authenticated user"""

    def get_current_user(self):
        """The login handler stored a JupyterHub API token in a cookie

        @web.authenticated calls this method.
        If a Falsy value is returned, the request is redirected to `login_url`.
        If a Truthy value is returned, the request is allowed to proceed.
        """
        token = self.get_secure_cookie('whoami-oauth-token')

        if token:
            # secure cookies are bytes, decode to str
            return token.decode('ascii', 'replace')

    async def user_for_token(self, token):
        """Retrieve the user for a given token, via /hub/api/user"""

        req = HTTPRequest(
            self.settings['user_url'], headers={'Authorization': f'token {token}'}
        )
        response = await AsyncHTTPClient().fetch(req)
        return json.loads(response.body.decode('utf8', 'replace'))

    @web.authenticated
    async def get(self):
        user_token = self.get_current_user()
        user_model = await self.user_for_token(user_token)
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(user_model, indent=1, sort_keys=True))


def main():
    log.enable_pretty_logging()

    # construct OAuth URLs from jupyterhub base URL
    hub_api = os.environ['JUPYTERHUB_URL'].rstrip('/') + '/hub/api'
    authorize_url = hub_api + '/oauth2/authorize'
    token_url = hub_api + '/oauth2/token'
    user_url = hub_api + '/user'

    app = web.Application(
        [('/oauth_callback', JupyterHubLoginHandler), ('/', WhoAmIHandler)],
        login_url='/oauth_callback',
        cookie_secret=os.urandom(32),
        api_token=os.environ['JUPYTERHUB_API_TOKEN'],
        client_id=os.environ['JUPYTERHUB_CLIENT_ID'],
        redirect_uri=os.environ['JUPYTERHUB_SERVICE_URL'].rstrip('/')
        + '/oauth_callback',
        authorize_url=authorize_url,
        token_url=token_url,
        user_url=user_url,
    )

    url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
    log.app_log.info(
        "Running basic whoami service on %s", os.environ['JUPYTERHUB_SERVICE_URL']
    )
    app.listen(url.port, url.hostname)
    IOLoop.current().start()


if __name__ == '__main__':
    main()
