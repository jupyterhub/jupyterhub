# Forced login example

Example for forcing user login via URL without disabling token-in-url protection.

An external application issues tokens associated with usernames.
A JupyterHub Authenticator only allows login via these tokens in a URL parameter (`/hub/login?login_token=....`),
which are then exchanged for a username, which is used to login the user.

Each token can be used for login only once, and must be used within 30 seconds of issue.

To run:

in one shell:

```
python3 external_app.py
```

in another:

```
jupyterhub
```

Then visit http://127.0.0.1:9000

Sometimes, JupyterHub is integrated into an existing application,
which has already handled login, etc.
It is often preferable in these applications to be able to link users to their running JupyterHub server without _prompting_ the user for login to the Hub when the Hub should really be an implementation detail.

One way to do this has been to use "API only mode", issue tokens for users, and redirect users to a URL like `/users/name/?token=abc123`.
This is [disabled by default]() in JupyterHub 5, because it presents a vulnerability for users to craft links that let _other_ users login as them, which can lead to inter-user attacks.

But that leaves the question: how do I as an _application developer_ generate a link that can login a user?

_Ideally_, the best way to set this up is with the external service as an OAuth provider,
though in some cases it works best to use proxy-based authentication like Shibboleth / [REMOTE_USER]().

If your service is an OAuth provider, sharing links to `/hub/user-redirect/lab/tree/path/to/notebook...` should work just fine.
JupyterHub will:

1. authenticate the user
2. redirect to your identity provider via oauth (you can set `Authenticator.auto_login = True` if you want to skip prompting the user)
3. complete oauth
4. start their single-user server if it's not running (show the launch progress page while it's waiting)
5. redirect to their server once it's up
6. oauth (again), this time between the single-user server and the Hub

If your application chooses to launch the server and wait for it to be ready before redirecting

[API only mode]() is sometimes useful
