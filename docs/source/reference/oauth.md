# JupyterHub and OAuth

JupyterHub uses OAuth 2 internally as a mechanism for authenticating users.
As such, JupyterHub itself always functions as an OAuth **provider**.
More on what that means below.

Additionally, JupyterHub is _often_ deployed with [oauthenticator](https://oauthenticator.readthedocs.io),
where an external identity provider, such as GitHub or KeyCloak, is used to authenticate users.
When this is the case, there are \*two nested

This means that when you are using JupyterHub, there is always _at least one_ and often two layers of OAuth involved in a user logging in and accessing their server.

Some relevant points:

- Single-user servers _never_ need to communicate with or be aware of the upstream provider.
  As far as they are concerned, only JupyterHub is an OAuth provider,
  and how users authenticate with the Hub itself is irrelevant.
- When talking to a single-user server,
  there are ~always two tokens:
  a token issued to the server itself to communicate with the Hub API,
  and a second per-user token in the browser to represent the completed login process and authorized permissions.
  More on this later.

### Key OAuth terms

- **provider** the entity responsible for managing.
  JupyterHub is _always_ an oauth provider for JupyterHub's components.
  When OAuthenticator is used, an external service, such as GitHub or KeyCloak, is also an oauth provider.
- **client** An entity that requests OAuth tokens on a user's behalf.
  JupyterHub _services_ or single-user _servers_ are OAuth clients of the JupyterHub _provider_.
  When OAuthenticator is used, JupyterHub is itself also an OAuth _client_ for the external oauth _provider_, e.g. GitHub.
- **browser** A user's web browser, which makes requests and stores things like cookies
- **token** The secret value used to represent a user's authorization. This is the final product of the OAuth process.

### The oauth flow

OAuth flow is what we call the sequence of HTTP requests involved in authenticating a user and issuing a token, ultimately used for authorized access to a service or single-user server.

It generally goes like this:

#### Oauth request and redirect
1. A _browser_ makes an HTTP request to an oauth _client_.
2. There are no credentials, so the client _redirects_ the browser to an "authorize" page on the oauth _provider_ with some extra information:
   - the oauth **client id** of the client itself
   - the **redirect uri** to be redirected back to after completion
   - the **scopes** requested, which the user should be presented with to confirm.
     This is the "X would like to be able to Y on your behalf. Allow this?" page you see on all the "Login with ..." pages around the Internet.
3. During this authorize step,
   the browser must be _authenticated_ with the provider.
   This is often already stored in a cookie,
   but if not the provider webapp must begin its _own_ authentication process before serving the authorization page.
4. After the user tells the provider that they want to proceed with the authorization,
   the provider records this authorization in a short-lived record called an **oauth code**.
5. Finally,
   the oauth provider redirects the browser _back_ to the oauth client's "redirect uri"
   (or "oauth callback uri"),
   with the oauth code in a url parameter.

#### State after redirect
At this point:

- The browser is authenticated with the _provider_
- The user's authorized permissions are recorded in an _oauth code_
- The _provider_ knows that the given oauth client's requested permissions have been granted, but the client doesn't know this yet.
- All requests so far have been made directly by the browser.
  No requests have originated at the client or provider.

#### OAuth Client Handles Callback Request
Now we get to finish the OAuth process.
Let's dig into what the oauth client does when it handles
the oauth callback request with the

- The OAuth client receives the _code_ and makes an API request to the _provider_ to exchange the code for a real _token_.
  This is the first direct request between the OAuth _client_ and the _provider_.
- Once the token is retrieved, the client _usually_
  makes a second API request to the _provider_
  to retrieve information about the owner of the token (the user)
- Finally, the oauth client stores its own record that the user is authorized in a cookie.
  This could be the token itself, or any other appropriate representation of successful authentication.

_phew_

So that's _one_ OAuth process.

## Full sequence of OAuth in JupyterHub

Let's go through the above oauth process in Jupyter,
with specific examples of each HTTP request and what information is contained.

Our starting point:

- a user's single-user server is running. Let's call them `danez`
- jupyterhub is running with GitHub as an oauth provider,
- Danez has a fresh browser session with no cookies yet

First request:

- browser->single-user server running JupyterLab or Jupyter Classic
- `GET /user/danez/notebooks/mynotebook.ipynb`
- no credentials, so client starts oauth process with JupyterHub
- response: 302 redirect -> `/hub/api/oauth2/authorize`
  with:
  - client-id=`jupyterhub-user-danez`
  - redirect-uri=`/user/danez/oauth_callback` (we'll come back later!)

Second request, following redirect:

- browser->jupyterhub
- `GET /hub/api/oauth2/authorize`
- no credentials, so jupyterhub starts oauth process _with GitHub_
- response: 302 redirect -> `/hub/api/oauth2/authorize`
  with:
  - client-id=`jupyterhub-client-uuid`
  - redirect-uri=`/hub/oauth_callback` (we'll come back later!)

Third request, following redirect:

- browser->GitHub
- `GET https://github.com/login/oauth/authorize`

Prompts for login and asks for confirmation of authorization.

After successful authorization
(either by looking up a pre-existing authorization,
or recording it via form submission)
GitHub issues oauth code and redirects to `/hub/oauth_callback?code=github-code`

Next request:

- browser->JupyterHub
- `GET /hub/oauth_callback?code=github-code`

Inside the callback handler, JupyterHub makes two API requests:

The first:

- JupyterHub->GitHub
- `POST https://github.com/login/oauth/access_token`
- request made with oauth code from url parameter
- response includes an access token

The second:

- JupyterHub->GitHub
- `GET https://api.github.com/user`
- request made with access token in the `Authorization` header
- response is the user model, including username, email, etc.

Now the oauth callback request completes with:

- set cookie on `/hub/` recording jupyterhub authentication so we don't need to do oauth with github again for a while
- redirect -> `/hub/api/oauth2/authorize`

Now, we get our first repeated request:

- browser->jupyterhub
- `GET /hub/api/oauth2/authorize`
- this time with credentials,
  so jupyterhub either
  1. serves the authorization confirmation page, or
  2. automatically accepts authorization (shortcut taken when a user is visiting their own server)
- redirect -> `/user/danez/oauth_callback?code=jupyterhub-code`

Here, we start the same oauth callback process as before, but at Danez's single-user server

- browser->single-user server
- `GET /user/danez/oauth_callback`

(in handler)

Inside the callback handler, Danez's server makes two API requests to JupyterHub:

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

_the end_

## A tale of two tokens

**TODO**: discuss API token issued to server at startup and oauth-issued token in cookie, and some details of how JupyterLab currently deals with that.
`

## Notes

- I omitted some information about the distinction between tokens issued to the server, due to RBAC changes. But they are different!
