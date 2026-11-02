(explanation:hub-oauth)=

# JupyterHub and OAuth

JupyterHub uses [OAuth 2](https://oauth.net/2/) as an internal mechanism for authenticating users.
As such, JupyterHub itself always functions as an OAuth **provider**.
You can find out more about what that means [below](oauth-terms).

As of JupyterHub 6.2, JupyterHub is also an [OIDC] Provider.

Additionally, JupyterHub is _often_ deployed with [OAuthenticator](https://oauthenticator.readthedocs.io),
where an external identity provider, such as GitHub or KeyCloak, is used to authenticate users.
When this is the case, there are _two_ nested OAuth flows:
an _internal_ OAuth flow where JupyterHub is the **provider**,
and an _external_ OAuth flow, where JupyterHub is the **client**.

This means that when you are using JupyterHub, there is always _at least one_ and often two layers of OAuth involved in a user logging in and accessing their server.

The following points are noteworthy:

- Single-user servers _never_ need to communicate with or be aware of the upstream provider configured in your Authenticator.
  As far as the servers are concerned, only JupyterHub is an OAuth provider,
  and how users authenticate with the Hub itself is irrelevant.
- When interacting with a single-user server,
  there are ~always two tokens:
  first, a token issued to the server itself to communicate with the Hub API,
  and second, a per-user token in the browser to represent the completed login process and authorized permissions.
  More on this [later](two-tokens).

(oauth-terms)=

## Key OAuth terms

Here are some key definitions to keep in mind when we are talking about OAuth.
You can also read more in detail [here](https://www.oauth.com/oauth2-servers/definitions/).

- **provider**: The entity responsible for managing identity and authorization;
  always a web server.
  JupyterHub is _always_ an OAuth provider for JupyterHub's components.
  When OAuthenticator is used, an external service, such as GitHub or KeyCloak, is also an OAuth provider.
- **client**: An entity that requests OAuth **tokens** on a user's behalf;
  generally a web server of some kind.
  OAuth **clients** are services that _delegate_ authentication and/or authorization
  to an OAuth **provider**.
  JupyterHub _services_ or single-user _servers_ are OAuth **clients** of the JupyterHub **provider**.
  When OAuthenticator is used, JupyterHub is itself _also_ an OAuth **client** for the external OAuth **provider**, e.g. GitHub.
- **browser**: A user's web browser, which makes requests and stores things like cookies.
- **token**: The secret value used to represent a user's authorization. This is the final product of the OAuth process.
- **code**: A short-lived temporary secret that the **client** exchanges
  for a **token** at the conclusion of OAuth,
  in what's generally called the "OAuth callback handler."
- **PKCE**: pronounced "pixie", this is an additional layer of security to verify the oauth process.
- **OIDC**: short for OpenID Connect, this is a layer of standardization _on top of_ OAuth, making configuration simpler. JupyterHub is an OIDC provider as of 6.2.
- **JWT**: JSON Web Token - a format of tokens used in OIDC, and supported by JupyterHub starting in 6.2.

## One oauth flow

OAuth **flow** is what we call the sequence of HTTP requests involved in authenticating a user and issuing a token, ultimately used for authorizing access to a service or single-user server.

A single OAuth flow typically goes like this:

### OAuth request and redirect

1. A **browser** makes an HTTP request to an OAuth **client**.
2. There are no credentials, so the client _redirects_ the browser to an "authorize" page on the OAuth **provider** with some extra information:
   - the OAuth **client ID** of the client itself.
   - the **redirect URI** to be redirected back to after completion.
   - the **scopes** requested, which the user should be presented with to confirm.
     This is the "X would like to be able to Y on your behalf. Allow this?" page you see on all the "Login with ..." pages around the Internet.
3. During this authorize step,
   the browser must be _authenticated_ with the provider.
   This is often already stored in a cookie,
   but if not the provider webapp must begin its _own_ authentication process before serving the authorization page.
   This _may_ even begin another OAuth flow!
4. After the user tells the provider that they want to proceed with the authorization,
   the provider records this authorization in a short-lived record called an **OAuth code**.
5. Finally, the oauth provider redirects the browser _back_ to the oauth client's "redirect URI"
   (or "OAuth callback URI"),
   with the OAuth code in a URL parameter.

That marks the end of the requests made between the **browser** and the **provider**.

### State after redirect

At this point:

- The browser is authenticated with the _provider_.
- The user's authorized permissions are recorded in an _OAuth code_.
- The _provider_ knows that the permissions requested by the OAuth client have been granted, but the client doesn't know this yet.
- All the requests so far have been made directly by the browser.
  No requests have originated from the client or provider.

### OAuth Client Handles Callback Request

At this stage, we get to finish the OAuth process.
Let's dig into what the OAuth client does when it handles
the OAuth callback request.

- The OAuth client receives the _code_ and makes an API request to the _provider_ to exchange the code for a real _token_.
  This is the first direct request between the OAuth _client_ and the _provider_.
- Once the token is retrieved, the client _usually_
  makes a second API request to the _provider_
  to retrieve information about the owner of the token (the user).
  This is the step where behavior diverges for different OAuth providers.
  Up to this point, all OAuth providers are the same, following the OAuth specification.
  However, OAuth does not define a standard for issuing tokens in exchange for information about their owner or permissions ([OpenID Connect](https://openid.net/developers/how-connect-works/) does that),
  so this step may be different for each OAuth provider.
- Finally, the OAuth client stores its own record that the user is authorized in a cookie.
  This could be the token itself, or any other appropriate representation of successful authentication.
- Now that credentials have been established,
  the browser can be redirected to the _original_ URL where it started,
  to try the request again.
  If the client wasn't able to keep track of the original URL all this time
  (not always easy!),
  you might end up back at a default landing page instead of where you started the login process. This is frustrating!

😮‍💨 _phew_.

So that's _one_ OAuth process.

## Full sequence of OAuth in JupyterHub

Let's go through the above OAuth process in JupyterHub,
with specific examples of each HTTP request and what information it contains.
For bonus points, we are using the double-OAuth example of JupyterHub configured with GitHubOAuthenticator.

To disambiguate, we will call the OAuth process where JupyterHub is the **provider** "internal OAuth,"
and the one with JupyterHub as a **client** "external OAuth."

Our starting point:

- a user's single-user server is running. Let's call them `danez`
- Jupyterhub is running with GitHub as an OAuth provider (this means two full instances of OAuth),
- Danez has a fresh browser session with no cookies yet.

First request:

- browser->single-user server running JupyterLab or Jupyter Classic
- `GET /user/danez/notebooks/mynotebook.ipynb`
- no credentials, so single-user server (as an OAuth **client**) starts internal OAuth process with JupyterHub (the **provider**)
- response: 302 redirect -> `/hub/api/oauth2/authorize`
  with:
  - client-id=`jupyterhub-user-danez`
  - redirect-uri=`/user/danez/oauth_callback` (we'll come back later!)

Second request, following redirect:

- browser->JupyterHub
- `GET /hub/api/oauth2/authorize`
- no credentials, so JupyterHub starts external OAuth process _with GitHub_
- response: 302 redirect -> `https://github.com/login/oauth/authorize`
  with:
  - client-id=`jupyterhub-client-uuid`
  - redirect-uri=`/hub/oauth_callback` (we'll come back later!)

_pause_ This is where JupyterHub configuration comes into play.
Recall, in this case JupyterHub is using:

```python
c.JupyterHub.authenticator_class = 'github'
```

That means authenticating a request to the Hub itself starts
a _second_, external OAuth process with GitHub as a provider.
This external OAuth process is optional, though.
If you were using the default username+password PAMAuthenticator,
this redirect would have been to `/hub/login` instead, to present the user
with a login form.

Third request, following redirect:

- browser->GitHub
- `GET https://github.com/login/oauth/authorize`

Here, GitHub prompts for login and asks for confirmation of authorization
(more redirects if you aren't logged in to GitHub yet, but ultimately back to this `/authorize` URL).

After successful authorization
(either by looking up a pre-existing authorization,
or recording it via form submission)
GitHub issues an **OAuth code** and redirects to `/hub/oauth_callback?code=github-code`

Next request:

- browser->JupyterHub
- `GET /hub/oauth_callback?code=github-code`

Inside the callback handler, JupyterHub makes two API requests:

The first:

- JupyterHub->GitHub
- `POST https://github.com/login/oauth/access_token`
- request made with OAuth **code** from URL parameter
- response includes an access **token**

The second:

- JupyterHub->GitHub
- `GET https://api.github.com/user`
- request made with access **token** in the `Authorization` header
- response is the user model, including username, email, etc.

Now the external OAuth callback request completes with:

- set cookie on `/hub/` path, recording jupyterhub authentication so we don't need to do external OAuth with GitHub again for a while
- redirect -> `/hub/api/oauth2/authorize`

🎉 At this point, we have completed our first OAuth flow! 🎉

Now, we get our first repeated request:

- browser->jupyterhub
- `GET /hub/api/oauth2/authorize`
- this time with credentials,
  so jupyterhub either
  1. serves the internal authorization confirmation page, or
  2. automatically accepts authorization (shortcut taken when a user is visiting their own server)
- redirect -> `/user/danez/oauth_callback?code=jupyterhub-code`

Here, we start the same OAuth callback process as before, but at Danez's single-user server for the _internal_ OAuth.

- browser->single-user server
- `GET /user/danez/oauth_callback`

(in handler)

Inside the internal OAuth callback handler,
Danez's server makes two API requests to JupyterHub:

The first:

- single-user server->JupyterHub
- `POST /hub/api/oauth2/token`
- request made with oauth code from url parameter
- response includes an API token

The second:

- single-user server->JupyterHub
- `GET /hub/api/user`
- request made with token in the `Authorization` header
- response is the user model, including username, groups, etc.

Finally completing `GET /user/danez/oauth_callback`:

- response sets cookie, storing encrypted access token
- _finally_ redirects back to the original `/user/danez/notebooks/mynotebook.ipynb`

Final request:

- browser -> single-user server
- `GET /user/danez/notebooks/mynotebook.ipynb`
- encrypted jupyterhub token in cookie

To authenticate this request, the single token stored in the encrypted cookie is passed to the Hub for verification:

- single-user server -> Hub
- `GET /hub/api/user`
- browser's token in Authorization header
- response: user model with name, groups, etc.

If the user model matches who should be allowed (e.g. Danez),
then the request is allowed.
See [Scopes in JupyterHub](jupyterhub-scopes) for how JupyterHub uses scopes to determine authorized access to servers and services.

_the end_

## Token caches and expiry

Because tokens represent information from an external source,
they can become 'stale,'
or the information they represent may no longer be accurate.
For example: a user's GitHub account may no longer be authorized to use JupyterHub,
that should ultimately propagate to revoking access and force logging in again.

To handle this, OAuth tokens and the various places they are stored can _expire_,
which should have the same effect as no credentials,
and trigger the authorization process again.

In JupyterHub's internal OAuth, we have these layers of information that can go stale:

- The OAuth client has a **cache** of Hub responses for tokens,
  so it doesn't need to make API requests to the Hub for every request it receives.
  This cache has an expiry of five minutes by default,
  and is governed by the configuration `HubAuth.cache_max_age` in the single-user server.
- The internal OAuth token is stored in a cookie, which has its own expiry (default: 14 days),
  governed by `JupyterHub.cookie_max_age_days`.
- The internal OAuth token itself can also expire,
  which is by default the same as the cookie expiry,
  since it makes sense for the token itself and the place it is stored to expire at the same time.
  This is governed by `JupyterHub.cookie_max_age_days` first,
  or can overridden by `JupyterHub.oauth_token_expires_in`.

That's all for _internal_ auth storage,
but the information from the _external_ authentication provider
(could be PAM or GitHub OAuth, etc.) can also expire.
Authenticator configuration governs when JupyterHub needs to ask again,
triggering the external login process anew before letting a user proceed.

- `jupyterhub-hub-login` cookie stores that a browser is authenticated with the Hub.
  This expires according to `JupyterHub.cookie_max_age_days` configuration,
  with a default of 14 days.
  The `jupyterhub-hub-login` cookie is encrypted with `JupyterHub.cookie_secret`
  configuration.
- {meth}`.Authenticator.refresh_user` is a method to refresh a user's auth info.
  By default, it does nothing, but it can return an updated user model if a user's information has changed,
  or force a full login process again if needed.
- {attr}`.Authenticator.auth_refresh_age` configuration governs how often
  `refresh_user()` will be called to check if a user must login again (default: 300 seconds).
- {attr}`.Authenticator.refresh_pre_spawn` configuration governs whether
  `refresh_user()` should be called prior to spawning a server,
  to force fresh auth info when a server is launched (default: False).
  This can be useful when Authenticators pass access tokens to spawner environments, to ensure they aren't getting a stale token that's about to expire.

**So what happens when these things expire or get stale?**

- If the HubAuth **token response cache** expires,
  when a request is made with a token,
  the Hub is asked for the latest information about the token.
  This usually has no visible effect, since it is just refreshing a cache.
  If it turns out that the token itself has expired or been revoked,
  the request will be denied.
- If the token has expired, but is still in the cookie:
  when the token response cache expires,
  the next time the server asks the hub about the token,
  no user will be identified and the internal OAuth process begins again.
- If the token _cookie_ expires, the next browser request will be made with no credentials,
  and the internal OAuth process will begin again.
  This will usually have the form of a transparent redirect browsers won't notice.
  However, if this occurs on an API request in a long-lived page visit
  such as a JupyterLab session, the API request may fail and require
  a page refresh to get renewed credentials.
- If the _JupyterHub_ cookie expires, the next time the browser makes a request to the Hub,
  the Hub's authorization process must begin again (e.g. login with GitHub).
  Hub cookie expiry on its own **does not** mean that a user can no longer access their single-user server!
- If credentials from the upstream provider (e.g. GitHub) become stale or outdated,
  these will not be refreshed until/unless `refresh_user` is called
  _and_ `refresh_user()` on the given Authenticator is implemented to perform such a check.
  At this point, few Authenticators implement `refresh_user` to support this feature.
  If your Authenticator does not or cannot implement `refresh_user`,
  the only way to force a check is to reset the `JupyterHub.cookie_secret` encryption key,
  which invalidates the `jupyterhub-hub-login` cookie for all users.

### Logging out

Logging out of JupyterHub means clearing and revoking many of these credentials:

- The `jupyterhub-hub-login` cookie is revoked, meaning the next request to the Hub itself will require a new login.
- The token stored in the `jupyterhub-user-username` cookie for the single-user server
  will be revoked, based on its association with `jupyterhub-session-id`, but the _cookie itself cannot be cleared at this point_
- The shared `jupyterhub-session-id` is cleared, which ensures that the HubAuth **token response cache** will not be used,
  and the next request with the expired token will ask the Hub, which will inform the single-user server that the token has expired

(oidc)=

## OpenID Connect and JSON Web Tokens

Support for OpenID Connect (OIDC) and JSON Web Tokens (JWT) are new in JupyterHub 6.2.

OIDC means that all the configuration information you need to authenticate with JupyterHub is the "issuer url",
which is your `{JupyterHub.public_url}/hub`.
From this information, an OIDC client can request

```
{issuer_url}/.well-known/openid-configuration
```

and receive all the information needed to implement OAuth with JupyterHub, such as the `authorization_endpoint`, `token_endpoint`, etc.

When OAuth completes with the `openid` scope, included in the token response is an `id_token` field,
which is a JWT.
This is a signed token describing the authenticated user,
which can be used to verify the user _without_ any requests to the Hub,
because the _signature_ can be verified, using something called JSON Web Keys (JWKs),
found at `jwks_uri` in the openid configuration.

### Token Exchange and JWT Bearer tokens

JupyterHub API tokens are generally opaque strings, which must be passed to JupyterHub to check what user they correspond to, what permissions they have, etc.
However, JupyterHub 6.2 also introduces support for JWT _Bearer tokens_.

```{note}
When relying on JupyterHub's OIDC features,
it is strongly recommended to set `JupyterHub.public_url` to the public URL of your deployment.
This affects things like the OIDC issuer and resource URLs,
and JupyterHub will have to guess at these values if they are not set,
and the guessed values can change over time.
```

Differences between API tokens, OIDC id_tokens, and JWT Bearer tokens (in JupyterHub):

|                                                            | API token | id_token | JWT Bearer token |
| ---------------------------------------------------------- | --------- | -------- | ---------------- |
| can be verified without a request to the Hub               | ❌        | ✅       | ✅               |
| can be used to access JupyterHub APIs or services          | ✅        | ❌       | ✅               |
| tied to single JupyterHub service (audience)               | ❌        | ✅       | ✅               |
| can be used to access multiple JupyterHub APIs or services | ✅        | ❌       | ❌               |
| can be revoked                                             | ✅        | ❌       | ❌               |
| can change permissions over time                           | ✅        | ❌       | ❌               |

There's an advantage of JWT Bearer tokens, in that they can be verified without any requests to the Hub.
However, this also means they cannot be _revoked_, and they can only be for a single **audience**, so they are limited to a shorter lifetime (default 1 hour, max 1 day).

To get a JWT Bearer token, first you need a regular API token with access to some APIs.
You can make a [Token Exchange] request, following [RFC8693] to JupyterHub's `token_endpoint`,
to exchange an API token for a JWT Bearer token for a specific audience.

RFC 8693 specifies a few arguments that we'll always provide:

| field                | value                                             |
| -------------------- | ------------------------------------------------- |
| `grant_type`         | `urn:ietf:params:oauth:grant-type:token-exchange` |
| `subject_token_type` | `urn:ietf:params:oauth:token-type:access_token`   |
| `subject_token`      | our existing JupyterHub API token                 |

We will then need to specify the one "audience" (JupyterHub server, service, or the Hub itself) that the token may be used to address.
There are two ways to specify an audience:

- `audience` if you already know the oauth client id you want to talk to (e.g. the `$JUPYTERHUB_CLIENT_ID` environment variable for a JupyterHub server or managed service).
- `resource` is a URL identifying the resource.

A resource url will always start with JupyterHub's public URL and have one of the forms:

```
https://hub.example/hub
https://hub.example/user/:user_name[/:server_name]
https://hub.example/services/:service_name
```

```{note}
Eeven when using per-user or per-service subdomains or non-proxied external services,
resource URLs always begin with the Hub's public url as the base.
In the default JupyterHub configuration, these are the actual addresses where the services can be accessed,
but they are not guaranteed to be.
```

There are also _optional_ fields, like `expires_in`

| `expires_in` | expiry in seconds (default: 1 hour, cannot exceed 1 day or issuing token's expiration, whichever is lower) |
| `scope` | space-delimited list of JupyterHub scopes to grant the token |

If `scope` is not specified, the resulting token will have the minimal scopes required to access the audience (e.g. `access:services!service=service-name`).
If `scope` is the singular `inherit`, the JWT will have all the scopes of the requesting token,
_excluding_ any access scopes to audiences other than the specified audience.
`scope` is not permitted to exceed any of the scopes held by the requesting token.

An example of a token-exchange request, given an API token:

```python
import os
import requests

# your inputs
public_url = "https://hub.example"
api_token = "..."


openid_url = f"{public_url}/hub/.well-known/openid-configuration"
openid_configuration = requests.get(openid_url).json()
token_endpoint = openid_configuration["token_endpoint"]
resource_url = f"{public_url}/services/service-oauth2-proxy",

r = requests.post(
    token_endpoint,
    data={
        "subject_token": api_token,
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "resource": resource_url,
    },
)
r.json()
```

which will return something like

```python
{'access_token': 'eyJhbGciOiJSUzI1NiIsImtpZCI6ImsxIiwidHlwIjoiSldUIn0.eyJhdWQiOiJzZXJ2aWNlLW9hdXRoMi1wcm94eSIsImlhdCI6MTc5MzI5MTYzMCwic2NvcGVzIjpbImFjY2VzczpzZXJ2aWNlcyFzZXJ2aWNlPW9hdXRoMi1wcm94eSJdLCJpc3MiOiJodHRwOi8vMTI3LjAuMC4xOjgwMDAvaHViIiwic3ViIjoidXNlci90ZXN0IiwibmFtZSI6InRlc3QiLCJraW5kIjoidXNlciIsImV4cCI6MTc5MzI5NTIzMH0.HQymN86uY7BmlZzuSvrVVkgJxNGTS0rGAkeH7fdxmbFjrDNEwefaxUGsRgP-wrpNaOiOuOV7mAlxLHXLidG0FvTnSItDzp3VuFieBkYNMB3Z5MIGe8g5dNmqwVteNsHuGLjzSx0l-AkYy8KGGIAYyqKRjsJ0N5_Ir80AuamARV5vqZtmvToN0b4VjanDQYXExOYVX1WbIVdotbCe4rhUPmBX8EFbdu8YRdtgVcQ1R-c5z8hc0ajinqziGLxWeP0xIyTN8xkXGoEfWrrCU_QtszCms8Lvvt-EBLwXuObFjOk3Kw2vkQFhwC_2sVPL4kv-uLmbj1BkX9_8u9znvPn3mg',
 'token_type': 'urn:ietf:params:oauth:token-type:jwt',
 'expires_in': 3600}
```

which can be used to access the target service.

[Token Exchange]: https://oauth.net/2/token-exchange/
[RFC8693]: https://www.rfc-editor.org/rfc/rfc8693

### Validating a JWT

If you want to validate a JWT Bearer token to protect your service, OIDC specifies how to do that,
and the `pyjwt` package provides a useful implementation.
When accepting a JWT that was not issued directly to your service, it is important to verify:

1. (most important) the signature
2. the issuer (`iss`)
3. the audience (`aud`)
4. the expiration (`exp`)

pyjwt will do all that for you. Starting from the `openid_configuration` above,
given a `jwt_bearer` token

```python
import jwt

audience = "my_client_id"
issuer = openid_configuration["issuer"]
jwks_uri = openid_configuration["jwks_uri"]

jwks_client = jwt.PyJWKClient(openid_configuration["jwks_uri"])
jwt_bearer = r.json()["access_token"]
signing_key = jwks_client.get_signing_key_from_jwt(jwt_bearer)
# jwt.decode will verify audience, signature, issuer, expiration
claims = jwt.decode(
  jwt_bearer,
  signing_key,
  audience=audience,
  issuer=issuer,
  algorithms=["RS256"],
)
```

which will look like:

```python
{'aud': 'service-oauth2-proxy',
 'iat': 1793318246,
 'scopes': ['access:services!service=oauth2-proxy'],
 'iss': 'http://127.0.0.1:8000/hub',
 'sub': 'user/test',
 'name': 'test',
 'kind': 'user',
 'exp': 1793321846}
```

and can be used to manage access to your service without any requests to the Hub.

## Extra bits

(two-tokens)=

### A tale of two tokens

**TODO**: discuss API token issued to server at startup ($JUPYTERHUB_API_TOKEN)
and OAuth-issued token in the cookie,
and some details of how JupyterLab currently deals with that.
They are different, and JupyterLab should be making requests using the token from the cookie,
not the token from the server,
but that is not currently the case.

### Redirect loops

In general, an authenticated web endpoint has this behavior,
based on the authentication/authorization state of the browser:

- If authorized, allow the request to happen
- If authenticated (I know who you are) but not authorized (you are not allowed), fail with a 403 permission denied error
- If not authenticated, start a redirect process to establish authorization,
  which should end in a redirect back to the original URL to try again.
  **This is why problems in authentication result in redirect loops!**
  If the second request fails to detect the authentication that should have been established during the redirect,
  it will start the authentication redirect process over again,
  and keep redirecting in a loop until the browser balks.

### PKCE

PKCE stands for "Proof Key for Code Exchange."
JupyterHub added support for PKCE in 6.0,
as it is expected to be [required in OAuth 2.1](https://oauth.net/2.1/).
PKCE is an additional layer of security in the OAuth flow.

PKCE adds two arguments to the OAuth flow:

1. a `code_verifier`, which is a random secret, unique to each OAuth flow
1. a `code_challenge`, which is the sha256 hash of the verifier

When PKCE is enabled, the initial OAuth `authorize` request includes the `code_challenge`, and the final token exchange includes the `code_verifier`.
The OAuth provider makes sure these two values match before issuing a token and completing the oauth flow.

For backward-compatibility, in JupyterHub 6.0, PKCE is not _enforced_ by default, but it is _enabled_ by default.
That means if an OAuth request does not send the `code_challenge`, there will be no check for the `code_verifier`, which means older clients that do not yet support PKCE will not break.
However, if a `code_challenge` is sent, the `code_verifier` will be checked and required before completing OAuth.

For clients, it is always safe to enable PKCE, even with old versions of JupyterHub, because OAuth providers MUST ignore unhandled parameters.

For enhanced security, JupyterHub deployments may set

```python
c.JupyterHub.oauth_require_pkce = True
```

This _only_ changes JupyterHub's behavior when no PKCE arguments are passed, as `jupyterhub-singleuser` and services authentication always send PKCE arguments.
This should work as long as `jupyterhub` is up-to-date in the user environments, and any _custom_ OAuth-enabled services also implement PKCE.

```{seealso}
https://datatracker.ietf.org/doc/html/rfc7636#section-4
```
