# JupyterHub and OAuth

JupyterHub uses OAuth 2 internally as a mechanism for authenticating users.
As such, JupyterHub itself always functions as an OAuth **provider**.
More on what that means [below](oauth-terms).

Additionally, JupyterHub is _often_ deployed with [oauthenticator](https://oauthenticator.readthedocs.io),
where an external identity provider, such as GitHub or KeyCloak, is used to authenticate users.
When this is the case, there are _two_ nested oauth flows:
an _internal_ oauth flow where JupyterHub is the **provider**,
and and _external_ oauth flow, where JupyterHub is a **client**.

This means that when you are using JupyterHub, there is always _at least one_ and often two layers of OAuth involved in a user logging in and accessing their server.

Some relevant points:

- Single-user servers _never_ need to communicate with or be aware of the upstream provider configured in your Authenticator.
  As far as they are concerned, only JupyterHub is an OAuth provider,
  and how users authenticate with the Hub itself is irrelevant.
- When talking to a single-user server,
  there are ~always two tokens:
  a token issued to the server itself to communicate with the Hub API,
  and a second per-user token in the browser to represent the completed login process and authorized permissions.
  More on this [later](two-tokens).

(oauth-terms)=

## Key OAuth terms

Here are some key definitions to keep in mind when we are talking about OAuth.
You can also read more detail [here](https://www.oauth.com/oauth2-servers/definitions/).

- **provider** the entity responsible for managing identity and authorization,
  always a web server.
  JupyterHub is _always_ an oauth provider for JupyterHub's components.
  When OAuthenticator is used, an external service, such as GitHub or KeyCloak, is also an oauth provider.
- **client** An entity that requests OAuth **tokens** on a user's behalf,
  generally a web server of some kind.
  OAuth **clients** are services that _delegate_ authentication and/or authorization
  to an OAuth **provider**.
  JupyterHub _services_ or single-user _servers_ are OAuth **clients** of the JupyterHub **provider**.
  When OAuthenticator is used, JupyterHub is itself _also_ an OAuth **client** for the external oauth **provider**, e.g. GitHub.
- **browser** A user's web browser, which makes requests and stores things like cookies
- **token** The secret value used to represent a user's authorization. This is the final product of the OAuth process.
- **code** A short-lived temporary secret that the **client** exchanges
  for a **token** at the conclusion of oauth,
  in what's generally called the "oauth callback handler."

## One oauth flow

OAuth **flow** is what we call the sequence of HTTP requests involved in authenticating a user and issuing a token, ultimately used for authorized access to a service or single-user server.

A single oauth flow generally goes like this:

### OAuth request and redirect

1. A **browser** makes an HTTP request to an oauth **client**.
2. There are no credentials, so the client _redirects_ the browser to an "authorize" page on the oauth **provider** with some extra information:
   - the oauth **client id** of the client itself
   - the **redirect uri** to be redirected back to after completion
   - the **scopes** requested, which the user should be presented with to confirm.
     This is the "X would like to be able to Y on your behalf. Allow this?" page you see on all the "Login with ..." pages around the Internet.
3. During this authorize step,
   the browser must be _authenticated_ with the provider.
   This is often already stored in a cookie,
   but if not the provider webapp must begin its _own_ authentication process before serving the authorization page.
   This _may_ even begin another oauth flow!
4. After the user tells the provider that they want to proceed with the authorization,
   the provider records this authorization in a short-lived record called an **oauth code**.
5. Finally, the oauth provider redirects the browser _back_ to the oauth client's "redirect uri"
   (or "oauth callback uri"),
   with the oauth code in a url parameter.

That's the end of the requests made between the **browser** and the **provider**.

### State after redirect

At this point:

- The browser is authenticated with the _provider_
- The user's authorized permissions are recorded in an _oauth code_
- The _provider_ knows that the given oauth client's requested permissions have been granted, but the client doesn't know this yet.
- All requests so far have been made directly by the browser.
  No requests have originated at the client or provider.

### OAuth Client Handles Callback Request

Now we get to finish the OAuth process.
Let's dig into what the oauth client does when it handles
the oauth callback request with the

- The OAuth client receives the _code_ and makes an API request to the _provider_ to exchange the code for a real _token_.
  This is the first direct request between the OAuth _client_ and the _provider_.
- Once the token is retrieved, the client _usually_
  makes a second API request to the _provider_
  to retrieve information about the owner of the token (the user).
  This is the step where behavior diverges for different OAuth providers.
  Up to this point, all oauth providers are the same, following the oauth specification.
  However, oauth does not define a standard for exchanging tokens for information about their owner or permissions ([OpenID Connect](https://openid.net/connect/) does that),
  so this step may be different for each OAuth provider.
- Finally, the oauth client stores its own record that the user is authorized in a cookie.
  This could be the token itself, or any other appropriate representation of successful authentication.
- Last of all, now that credentials have been established,
  the browser can be redirected to the _original_ URL where it started,
  to try the request again.
  If the client wasn't able to keep track of the original URL all this time
  (not always easy!),
  you might end up back at a default landing page instead of where you started the login process. This is frustrating!

😮‍💨 _phew_.

So that's _one_ OAuth process.

## Full sequence of OAuth in JupyterHub

Let's go through the above oauth process in JupyterHub,
with specific examples of each HTTP request and what information is contained.
For bonus points, we are using the double-oauth example of JupyterHub configured with GitHubOAuthenticator.

To disambiguate, we will call the OAuth process where JupyterHub is the **provider** "internal oauth,"
and the one with JupyterHub as a **client** "external oauth."

Our starting point:

- a user's single-user server is running. Let's call them `danez`
- jupyterhub is running with GitHub as an oauth provider (this means two full instances of oauth),
- Danez has a fresh browser session with no cookies yet

First request:

- browser->single-user server running JupyterLab or Jupyter Classic
- `GET /user/danez/notebooks/mynotebook.ipynb`
- no credentials, so single-user server (as an oauth **client**) starts internal oauth process with JupyterHub (the **provider**)
- response: 302 redirect -> `/hub/api/oauth2/authorize`
  with:
  - client-id=`jupyterhub-user-danez`
  - redirect-uri=`/user/danez/oauth_callback` (we'll come back later!)

Second request, following redirect:

- browser->jupyterhub
- `GET /hub/api/oauth2/authorize`
- no credentials, so jupyterhub starts external oauth process _with GitHub_
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
a _second_, external oauth process with GitHub as a provider.
This external oauth process is optional, though.
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
GitHub issues an **oauth code** and redirects to `/hub/oauth_callback?code=github-code`

Next request:

- browser->JupyterHub
- `GET /hub/oauth_callback?code=github-code`

Inside the callback handler, JupyterHub makes two API requests:

The first:

- JupyterHub->GitHub
- `POST https://github.com/login/oauth/access_token`
- request made with oauth **code** from url parameter
- response includes an access **token**

The second:

- JupyterHub->GitHub
- `GET https://api.github.com/user`
- request made with access **token** in the `Authorization` header
- response is the user model, including username, email, etc.

Now the external oauth callback request completes with:

- set cookie on `/hub/` path, recording jupyterhub authentication so we don't need to do external oauth with GitHub again for a while
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

Here, we start the same oauth callback process as before, but at Danez's single-user server for the _internal_ oauth

- browser->single-user server
- `GET /user/danez/oauth_callback`

(in handler)

Inside the internal oauth callback handler,
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
See {doc}`../rbac/scopes` for how JupyterHub uses scopes to determine authorized access to servers and services.

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

In JupyterHub's internal oauth, we have these layers of information that can go stale:

- The oauth client has a **cache** of Hub responses for tokens,
  so it doesn't need to make API requests to the Hub for every request it receives.
  This cache has an expiry of five minutes by default,
  and is governed by the configuration `HubAuth.cache_max_age` in the single-user server.
- The internal oauth token is stored in a cookie, which has its own expiry (default: 14 days),
  governed by `JupyterHub.cookie_max_age_days`.
- The internal oauth token can also itself expire,
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
  no user will be identified and the internal oauth process begins again.
- If the token _cookie_ expires, the next browser request will be made with no credentials,
  and the internal oauth process will begin again.
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
  will be revoked, based on its associaton with `jupyterhub-session-id`, but the _cookie itself cannot be cleared at this point_
- The shared `jupyterhub-session-id` is cleared, which ensures that the HubAuth **token response cache** will not be used,
  and the next request with the expired token will ask the Hub, which will inform the single-user server that the token has expired

## Extra bits

(two-tokens)=

### A tale of two tokens

**TODO**: discuss API token issued to server at startup ($JUPYTERHUB_API_TOKEN)
and oauth-issued token in the cookie,
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
