# Using JupyterHub + OAuth2 Proxy to protect external services

[OAuth2 Proxy] is a reverse proxy that can protect arbitrary web services with credentials from an OIDC provider.
JupyterHub 6.2 has been upgraded from an OAuth 2.0 provider to an OIDC provider.
Together, this means that JupyterHub deployments can grant Hub users access to shared external services _using_ a shared credential, but _without_ disclosing that shared credential to users.

## How it works

### The proxied service (echo)

In this example, we have `echo.py` as a stand-in for our upstream service.
All it does is respond to any HTTP requests with information about the requests it receives, so we can see what the proxy injected.
The echo service is running on `http://127.0.0.1:9999`.

### OAuth2 Proxy

[OAuth2 Proxy] is the auth proxy, protecting `echo.py`.
The proxy is running on `http://127.0.0.1:4180`.
You'll need to install OAuth2 Proxy, according to their documentation.

At a high level, the goal is for the proxy to:

1. verify that requests have access to the proxy service via the `access:services!service=service-oauth2-proxy` scope.
2. if authorized, make an upstream request with the shared Bearer token, stored in `upstream-bearer-token`

To accomplish this, we register `oauth2-proxy` as an OAuth Client with JupyterHub.
OAuth2 Proxy can function in two ways:

1. browser login via oauth flow (we won't use this)
2. Accepting [JWT] Bearer tokens in the Authorization header

The former is relatively simple and Just Works® with very little configuration.
It's a great choice for services that users access directly with their browser.

But we are using the latter, so that backend services can communicate with the authenticated service.
Our goal: given a valid JupyterHub access token, access the proxied service.

The most relevant aspects of JWT (as used in OIDC) are that:

1. they represent a verified set of `claims`, which is a JSON dictionary serialized within the token itself
2. a JWT has an Issuer (`iss`) which identifies who issued the token (JupyterHub in our case), and
3. an Audience (`aud`), representing the endpoint
4. JupyterHub access tokens are _not_ JWTs

So when you login to your server on JupyterHub, an ID token is issued with `iss=https://your-jupyterhub.example.org/hub` and `aud=your-servers-client-id`.
Each JupyterHub service and user's server has its own client id.

OAuth2 Proxy always validates the audience of a JWT to make sure it should have access to the proxied service.
This works well for the browser login mode, because a token issued during oauth will always have the proxy itself as the audience, but makes it hard to use JWTs issued to your user server as a Bearer token to access the proxied service, since the audience doesn't match.

First, we instruct OAuth2 Proxy to accept JWT Bearer tokens in the `Authorization` header, rather than forcing an OAuth login flow:

```toml
skip_jwt_bearer_tokens = true
bearer_token_login_fallback = false
force_json_errors = true # optional
```

We want to use the JupyterHub `scopes` of the token to determine if it should be authorized.
Not all JupyterHub tokens will have access to this service, so we don't want the proxy to accept _every_ JupyterHub token.
To reconcile this, we configure OAuth2 Proxy to treat the `scopes` field as a list of audiences,
and accept the appropriate JupyterHub access scopes as "extra audiences":

```yaml
audienceClaims:
  - scopes
  - aud
extraAudiences:
  - access:services
  - access:services!service=service-oauth2-proxy
```

Next, we want to inject an Authorization header with our protected shared token,
so that when a request is authorized via JupyterHub credentials, the proxied request uses the protected, shared access token:

```
Bearer super-secret-upstream-token
```

which is never shared directly with your Hub users.

Customizing injected headers requires using the OAuth2 Proxy's [AlphaConfig], in `oauth2-proxy.yaml`

### JupyterHub

This JupyterHub configuration is mostly boilerplate for running a local test, with JupyterHub listening on localhost with a dummy authenticator (any username and password will be allowed).

The relevant JupyterHub configuration for OIDC is:

1. set `JupyterHub.public_url`, which is needed for consistent resolution of JupyterHub's OIDC Issuer, which must match the issuer in `oauth2-proxy.cfg`.
2. register `oauth2-proxy` as a service with the client id and secret in `oauth2-proxy.cfg`

We also want the $JUPYTERHUB_API_TOKEN issued to user servers to be able to access the proxy service, so we set:

```python
# users have access to services
c.JupyterHub.extra_user_scopes = {"access:services"}
# server token also has access to services
c.Spawner.server_token_scopes = ["access:services"]
```

For convenience in this demo, JupyterHub manages the processes for both oauth2-proxy and echo.py.
In practice, the upstream service is likely already running somewhere else, and
`oauth2-proxy` is likely an externally-managed JupyterHub service.

### Getting an access token

So now OAuth2 Proxy accepts JWT Bearer tokens issued by JupyterHub with the appropriate `access:services` scopes.
But JupyterHub **API Tokens aren't JWTs!**.
How do we deal with this?

```{warning}
The exact flow of Bearer -> JWT exchange is still under development.
```

When you request information about your token via `GET /hub/api/user`, a matching JWT is included in the `id_token` field.

So when you have a JupyterHub access token, you can _exchange it_ for a JWT,
which can then be used to access the proxied service.

## Running the demo

start JupyterHub in the demo directory:

```
jupyterhub
```

visit http://127.0.0.1:8000 and login with any username.

You will see in your JupyterLab home directory, the `auth-proxy.ipynb` notebook.
Run this, and it will:

1. exchange $JUPYTERHUB_API_TOKEN for an equivalent signed JWT
2. make a request to the proxied service with the JWT

[JWT]: https://jwt.io
[OAuth2 Proxy]: https://oauth2-proxy.github.io
[AlphaConfig]: https://oauth2-proxy.github.io/oauth2-proxy/configuration/alpha-config
