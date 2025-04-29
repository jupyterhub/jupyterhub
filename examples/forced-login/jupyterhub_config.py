import json

from tornado import web
from tornado.httpclient import AsyncHTTPClient, HTTPClientError
from traitlets import Unicode

from jupyterhub.auth import Authenticator
from jupyterhub.utils import url_path_join


class ForcedLoginAuthenticator(Authenticator):
    """Authenticator to force login with a token provided by an external service

    The external service issues tokens, which are exchanged for a username.
    Visiting `/hub/login?login_token=...` logs in a user
    Each token can be used only once.
    """

    auto_login = True  # begin login without prompt (token is in url)
    allow_all = True  # external login app controls this
    token_provider_url = Unicode(
        config=True, help="""The URL of the token/username provider"""
    )

    async def authenticate(self, handler, data):
        token = handler.get_argument("login_token", None)
        if not token:
            raise web.HTTPError(
                400, f"Login with external provider at {self.token_provider_url}"
            )
        client = AsyncHTTPClient()
        try:
            response = await client.fetch(
                url_path_join(self.token_provider_url, "/login"),
                method="POST",
                headers={"Content-Type": "application/json"},
                body=json.dumps({"token": token}),
            )
        except HTTPClientError as e:
            self.log.info(
                "Error exchanging token for username: %s",
                e.response.body.decode("utf8", "replace"),
            )
            if e.code == 404:
                raise web.HTTPError(
                    403,
                    f"Invalid token. Login with external provider at {self.token_provider_url}",
                )
            else:
                raise
        # pass through the response
        return json.loads(response.body.decode())


c = get_config()  # noqa

# use our Authenticator
c.JupyterHub.authenticator_class = ForcedLoginAuthenticator
# tell it where the external launch app is
c.ForcedLoginAuthenticator.token_provider_url = "http://127.0.0.1:9000/"


# local testing config (fake spawner, localhost only)
c.JupyterHub.ip = "127.0.0.1"
c.JupyterHub.spawner_class = "simple"
