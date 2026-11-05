"""
OpenID Connect (OIDC) handlers
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from urllib.parse import urlparse, urlunparse

from jwt.algorithms import RSAAlgorithm

from .. import scopes
from ..oauth.provider import GrantType
from ..utils import url_path_join
from .base import APIHandler


class OpenIDConfigurationHandler(APIHandler):
    """
    OpenID Connect configuration endpoint

    spec: https://openid.net/specs/openid-connect-discovery-1_0.html
    example: https://accounts.google.com/.well-known/openid-configuration
    """

    def get(self):
        ouath_provider = self.settings["oauth_provider"]
        public_url = self.settings["public_url"]
        if public_url:
            hub_url = url_path_join(urlunparse(public_url), "hub")
        else:
            self.log.warning("Guessing public URL for OIDC.")
            full_url = urlparse(self.request.full_url())
            hub_url = (
                f"{full_url.scheme}://{full_url.netloc}{self.hub.base_url}".rstrip("/")
            )
        oauth2 = url_path_join(hub_url, "api/oauth2")
        available_scopes = sorted(scopes.scope_definitions.keys())
        available_scopes.remove("(no_scope)")

        openid_config = {
            "issuer": ouath_provider.issuer,
            "authorization_endpoint": url_path_join(oauth2, "authorize"),
            "token_endpoint": url_path_join(oauth2, "token"),
            "userinfo_endpoint": url_path_join(hub_url, "api/user"),
            "jwks_uri": url_path_join(hub_url, ".well-known/jwks.json"),
            "response_types_supported": [
                "code",
            ],
            "response_modes_supported": [
                "query",
            ],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "scopes_supported": available_scopes,
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
            ],
            # fields
            "claims_supported": [
                "aud",
                "exp",
                "iat",
                "iss",
                "kind",
                "name",
                "sub",
            ],
            "code_challenge_methods_supported": ["S256"],
            "grant_types_supported": [
                "authorization_code",
                # "refresh_token",
                GrantType.TOKEN_EXCHANGE,
            ],
        }
        self.write(json.dumps(openid_config))


class JWKSHandler(APIHandler):
    def get(self):
        keys = self.settings["token_signing_keys"]
        jwks = []
        for kid, private_key in keys.items():
            jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
            jwk["use"] = "sig"
            jwk["alg"] = "RS256"
            jwk["kid"] = kid
            jwks.append(jwk)
        self.write(json.dumps({"keys": jwks}))


default_handlers = [
    (r"/.well-known/openid-configuration", OpenIDConfigurationHandler),
    (r"/.well-known/jwks.json", JWKSHandler),
]
