import asyncio
from contextlib import nullcontext

import jwt
import pytest
from tornado import web

from ..apihandlers.auth import _lookup_resource
from ..utils import is_jwt
from .conftest import _mockservice
from .utils import api_request, async_requests, public_url


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


async def test_oidc_id_token(app):
    provider = app.oauth_provider
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


async def token_exchange(app, subject_token, check=True, scopes=None, **params):
    """Make a token-exchange request"""
    request = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": subject_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
    }
    request.update(params)
    if scopes:
        request["scope"] = " ".join(scopes)
    r = await api_request(
        app,
        "oauth2/token",
        method="post",
        data=request,
    )
    if check and not r.ok:
        pytest.fail(r.text)
    jwt_claims = token = None
    if r.ok:
        response = r.json()
        token = response["access_token"]
        assert is_jwt(token)
        jwt_claims = jwt.decode(
            token, audience=request.get("audience"), options={'verify_signature': False}
        )
    return r, token, jwt_claims


@pytest.mark.parametrize(
    "token_scopes, request_scopes, expect_scopes",
    [
        (
            ["list:users"],
            ["list:users"],
            ["list:users", "read:users:name"],
        ),
        (
            ["list:users"],
            ["read:groups"],
            "error",
        ),
        # strip access scopes
        (
            ["access:services"],
            ["access:services"],
            "error",
        ),
        (
            ["read:users:name", "access:services"],
            None,
            [],
        ),
        (
            ["read:users:name", "access:services"],
            ["read:users:name"],
            ["read:users:name"],
        ),
        (
            ["inherit"],
            ["read:users:name"],
            ["read:users:name"],
        ),
        (
            ["list:users"],
            ["inherit"],
            ["list:users", "read:users:name"],
        ),
    ],
)
async def test_token_exchange_scopes(
    app,
    admin_user,
    create_user_with_scopes,
    token_scopes,
    request_scopes,
    expect_scopes,
):
    user = admin_user
    token = user.new_api_token(scopes=token_scopes)
    from jupyterhub import orm

    orm_token = orm.APIToken.find(app.db, token=token)
    r, token, jwt_claims = await token_exchange(
        app, token, audience="jupyterhub", scopes=request_scopes, check=False
    )
    if expect_scopes == "error":
        assert r.status_code == 403
        return
    assert sorted(jwt_claims["scopes"]) == sorted(expect_scopes)
    # now make another request with this token
    r = await api_request(app, "user", headers={"Authorization": f"Bearer {token}"})
    assert r.ok
    response = r.json()
    assert response["name"] == user.name
    assert sorted(response["scopes"]) == sorted(expect_scopes)


async def test_token_exchange_hub(app, create_user_with_scopes, admin_user):
    user = create_user_with_scopes("list:users", "list:groups", "read:users")
    token = user.new_api_token(scopes=["list:users", "read:users"])
    _, token, jwt_claims = await token_exchange(
        app, token, audience="jupyterhub", scopes=["read:users:name"]
    )
    assert jwt_claims["scopes"] == ["read:users:name"]
    # now make another request with this token
    r = await api_request(app, "user", headers={"Authorization": f"Bearer {token}"})
    assert r.ok
    response = r.json()
    assert response["name"] == user.name
    assert response["scopes"] == ["read:users:name"]
    # make sure endpoints are appropriately protected
    r = await api_request(
        app, "users", admin_user.name, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.ok
    assert r.json() == {
        "admin": True,
        "kind": "user",
        "name": admin_user.name,
        "user_info": None,
    }
    r = await api_request(app, "users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    r = await api_request(app, "groups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


async def test_token_exchange_service(
    request, app, create_user_with_scopes, mockservice_url
):

    user = create_user_with_scopes("access:services", "read:users")
    service = mockservice_url
    service_name = service.name
    api_token = user.new_api_token(
        scopes=["access:services", "read:users:name"],
    )
    _, token, jwt_claims = await token_exchange(
        app,
        api_token,
        audience=service.oauth_client.identifier,
        scopes=["inherit"],
    )
    expected_scopes = [f"access:services!service={service_name}", "read:users:name"]
    assert jwt_claims["scopes"] == expected_scopes
    # make sure user_info works,
    # even though audience is not 'jupyterhub'
    r = await api_request(app, "user", headers={"Authorization": f"Bearer {token}"})
    assert r.ok
    response = r.json()
    assert response["name"] == user.name
    assert response["scopes"] == expected_scopes

    # can access service
    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/',
        headers={'Authorization': f'token {token}'},
    )
    assert r.ok
    reply = r.json()
    assert reply["name"] == user.name

    # cannot access jupyterhub
    # because of mismatched audience, despite holding read:users:name scope
    r = await api_request(
        app, "users", user.name, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            {"requested_token_type": "access_token"},
            "token_type must be",
            id="requested_token_type",
        ),
        pytest.param(
            {"expires_in": "notanumber"},
            "expires_in must be",
            id="expires_in not a number",
        ),
        pytest.param({"expires_in": "0"}, "expires_in must be", id="expires_in=0"),
        pytest.param({"expires_in": "-10"}, "expires_in must be", id="expires_in<0"),
        pytest.param(
            {"audience": "xyz", "resource": "abc"},
            "exactly one",
            id="audience-and-resource",
        ),
        pytest.param(
            {"audience": None},
            "exactly one",
            id="missing-audience",
        ),
    ],
)
async def test_token_exchange_validation(
    app, create_user_with_scopes, params, expected
):

    request = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
    }
    user = create_user_with_scopes("self")
    token = user.new_api_token()
    request["subject_token"] = token
    for key, value in params.items():
        if value is None:
            # allow clearing with None
            request.pop(key, None)
        else:
            request[key] = params[key]

    if "resource" not in params and "audience" not in params:
        request["audience"] = "jupyterhub"

    r = await api_request(
        app,
        "oauth2/token",
        method="post",
        data=request,
    )
    response = r.json()
    assert r.status_code == 400
    assert expected in response["message"]


@pytest.mark.parametrize(
    "resource, expected",
    [
        # valid
        ("PUBLIC/hub", "jupyterhub"),
        ("PUBLIC/users/USER", "user"),
        ("PUBLIC/users/USER/named", "user/named"),
        ("PUBLIC/services/SERVICE", "service"),
        # valid, no match
        ("PUBLIC/users/nomatch", False),
        ("PUBLIC/users/nomatch/nomatch", False),
        ("PUBLIC/users/USER/nomatch", False),
        ("PUBLIC/services/nomatch", False),
        # errors
        ("PUBLIC/hub/sub", "error"),
        ("PUBLIC/user/USER", "error"),
        ("PUBLIC/services/SERVICE/subpath", "error"),
        ("PUBLIC/users/USER/named/subpath", "error"),
        ("https://jupyter.org/users/USER", "error"),
    ],
)
async def test_token_exchange_resource_lookup(
    request,
    app,
    user_needs_escaping,
    resource,
    expected,
    service_name,
):
    user = user_needs_escaping
    named_spawner = user.get_or_create_spawner("named", "")
    # make sure oauth clients are populated
    assert user.spawner.orm_spawner.oauth_client is not None
    assert named_spawner.orm_spawner.oauth_client is not None
    public = public_url(app)
    resource = resource.replace("PUBLIC", public.rstrip("/"))
    resource = resource.replace("USER", user.escaped_name)
    if "services" in resource:
        # start service only when needed
        service = await _mockservice(request, app, name=service_name, url=True)
    resource = resource.replace("SERVICE", service_name)

    if expected == "error":
        context = pytest.raises(web.HTTPError)
    else:
        context = nullcontext()

    with context:
        oauth_client = _lookup_resource(
            resource,
            app.db,
            base_url=app.tornado_settings["base_url"],
            public_url=app.tornado_settings["public_url"],
            log=app.log,
        )
    if expected == "error":
        return
    if not expected:
        assert oauth_client is None
        return

    assert oauth_client is not None

    match expected:
        case "jupyterhub":
            assert oauth_client.identifier == "jupyterhub"
        case "user":
            assert oauth_client is user.orm_spawners[""].oauth_client
        case "user/named":
            assert oauth_client is user.orm_spawners["named"].oauth_client
        case "service":
            assert oauth_client is service.oauth_client
        case _:
            raise ValueError(f"unexpected result: {expected}")
