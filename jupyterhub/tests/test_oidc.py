import asyncio

import jwt

from .utils import async_requests, public_url


async def test_oidc_configuration(app):
    hub_url = public_url(app, path="hub")
    url = public_url(app, path="hub/.well-known/openid-configuration")
    r = await async_requests.get(url)
    oidc_config = r.json()
    assert oidc_config["issuer"] == hub_url


async def test_jwks(app):
    url = public_url(app, path="hub/.well-known/jwks.json")
    r = await async_requests.get(url)
    jwks_json = r.json()
    # WHY is it a list and not a dict by kid?!
    assert set(jwks_json.keys()) == {"keys"}
    keys = jwks_json["keys"]
    assert isinstance(keys, list)
    assert len(keys) == 1
    jwk = keys[0]
    assert jwk["kid"] == "k1"


async def test_token_signing(app):
    jwks_client = jwt.PyJWKClient(public_url(app, path="hub/.well-known/jwks.json"))
    # jwks_client is sync
    await asyncio.get_running_loop().run_in_executor(None, jwks_client.fetch_data)
    keys = jwks_client.get_signing_keys()
    assert keys
    kid, key = next(iter(app.token_signing_keys_loaded.items()))
    payload = {"aud": "abc123"}
    token = jwt.encode(payload, key, headers={"kid": kid}, algorithm="RS256")
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    # resolve signing key with jwks client
    decoded = jwt.decode(token, signing_key, audience="abc123", algorithms=["RS256"])
