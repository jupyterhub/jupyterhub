# Logging users in via URL

Sometimes, JupyterHub is integrated into an existing application that has already handled user login, etc..
It is often preferable in these applications to be able to link users to their running JupyterHub server without _prompting_ the user to login again with the Hub when the Hub should really be an implementation detail,
and not part of the user experience.

One way to do this has been to use [API only mode](#howto:api-only), issue tokens for users, and redirect users to a URL like `/users/name/?token=abc123`.
This is [disabled by default](#HubAuth.allow_token_in_url) in JupyterHub 5, because it presents a vulnerability for users to craft links that let _other_ users login as them, which can lead to inter-user attacks.

But that leaves the question: how do I as an _application developer_ embedding JupyterHub link users to their own running server without triggering another login prompt?

The problem with `?token=...` in the URL is specifically that _users_ can get and create these tokens, and share URLs.
This wouldn't be an issue if only authorized applications could issue tokens that behave this way.
The single-user server doesn't exactly have the hooks to manage this easily, but the [Authenticator](#Authenticator) API does.

## Problem statement

We want our external application to be able to:

1. authenticate users
2. (maybe) create JupyterHub users
3. start JupyterHub servers
4. redirect users into running servers _without_ any login prompts/loading pages from JupyterHub, and without any prior JupyterHub credentials

Step 1 is up to the application and not JupyterHub's problem.
Step 2 and 3 use the JupyterHub [REST API](#jupyterhub-rest-API).
The service would need the scopes:

```
admin:users # creating users
servers # start/stop servers
```

That leaves the last step: sending users to their running server with credentials, without prompting login.
This is where things can get tricky!

### Ideal case: oauth

_Ideally_, the best way to set this up is with the external service as an OAuth provider,
though in some cases it works best to use proxy-based authentication like Shibboleth / [REMOTE_USER](https://github.com/cwaldbieser/jhub_remote_user_authenticator).
The main things to know are:

- Links to `/hub/user-redirect/some/path` will ultimately land users at `/users/theirserver/some/path` after completing login, ensuring the server is running, etc.
- Setting `Authenticator.auto_login = True` allows beginning the login process without JupyterHub's "Login with..." prompt

_If_ your OAuth provider allows logging in to external services via your oauth provider without prompting, this is enough.
Not all do, though.

If you've already ensured the server is running, this will _appear_ to the user as if they are being sent directly to their running server.
But what _actually_ happens is quite a series of redirects, state checks, and cookie-setting:

1. visiting `/hub/user-redirect/some/path` checks if the user is logged in
   1. if not, begin the login process (`/hub/login?next=/hub/user-redirect/...`)
   2. redirects to your oauth provider to authenticate the user
   3. redirects back to `/hub/oauth_callback` to complete login
   4. redirects back to `/hub/user-redirect/...`
2. once authenticated, checks that the user's server is running
   1. if not running, begins launch of the server
   2. redirects to `/hub/spawn-pending/?next=...`
3. once the server is running, redirects to the actual user server `/users/username/some/path`

Now we're done, right? Actually, no, because the browser doesn't have credentials for their user server!
This sequence of redirects happens all the time in JupyterHub launch, and is usually totally transparent.

4. at the user server, check for a token in cookie
   1. if not present or not valid, begin oauth with the Hub (redirect to `/hub/api/oauth2/authorize/...`)
   2. hub redirects back to `/users/user/oauth_callback` to complete oauth
   3. redirect again to the URL that started this internal oauth
5. finally, arrive at `/users/username/some/path`, the ultimate destination, with valid JupyterHub credentials

The steps that will show users something other than the page you want them to are:

- Step 1.1 will be a prompt e.g. with "Login with..." unless you set `c.Authenticator.auto_login = True`
- Step 1.2 _may_ be a prompt from your oauth provider. This isn't controlled by JupyterHub, and may not be avoidable.
- Step 2.2 will show the spawn pending page only if the server is not already running

Otherwise, this is all transparent redirects to the final destination.

#### Using an authentication proxy (REMOTE_USER)

If you use an Authentication proxy like Shibboleth that sets e.g. the REMOTE_USER header,
you can use an Authenticator like [RemoteUserAuthenticator](https://github.com/cwaldbieser/jhub_remote_user_authenticator) to automatically login users based on headers in the request.
The same process will work, but instead of step 1.1 redirecting to the oauth provider, it logs in immediately.
If you do support an auth proxy, you also need to be extremely sure that requests only come from the auth proxy, and don't accept any requests setting the REMOTE_USER header coming from other sources.

### Custom case

But let's say you can't use OAuth or REMOTE_USER, and you still want to hide JupyterHub implementation details.
All you really want is a way to write a URL that will take users to their servers without any login prompts.

You can do this if you create an Authenticator with `auto_login=True` that logs users in based on something in the _request_, e.g. a query parameter.

We have an _example_ in the JupyterHub repo in `examples/forced-login` that does this.
It is a sample 'external service' where you type in a username and a destination path.
When you 'login' with this username:

1. a token is issued
2. the token is stored and associated with the username
3. redirect to `/hub/login?login_token=...&next=/hub/user-redirect/destination/path`

Then on the JupyterHub side, there is the `ForcedLoginAuthenticator`.
This class implements `authenticate`, which:

1. has `auto_login = True` so visiting `/hub/login` calls `authenticate()` directly instead of serving a page
2. gets the token from the `login_token` URL parameter
3. makes a POST request to the external application with the token, requesting a username
4. the external application returns the username and deletes the token, so it cannot be re-used
5. Authenticator returns the username

This doesn't _bypass_ JupyterHub authentication, as some deployments have done, but it does _hide_ it.
If your service launches servers via the API, you could run this in [API only mode](#howto:api-only) by adding `/hub/login` as well:

```python
c.JupyterHub.hub_routespec = "/hub/api/"
c.Proxy.additional_routes = {"/hub/login": "http://hub:8080"}
```

```{literalinclude} ../../../examples/forced-login/jupyterhub_config.py
:language: python
:start-at: class ForcedLoginAuthenticator
:end-before: c = get_config()
```

**Why does this work?**

This is still logging in with a token in the URL, right?
Yes, but the key difference is that users cannot issue these tokens.
The sample application is still technically vulnerable, because the token link should really be non-transferrable, even if it can only be used once.
The only defense the sample application has against this is rapidly expiring tokens (they expire after 30 seconds).
You can use state cookies, etc. to manage that more rigorously, as done in OAuth (at which point, maybe implement OAuth itself, why not?).
