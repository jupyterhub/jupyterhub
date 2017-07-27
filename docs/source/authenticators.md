# Authenticators

## Basics of Authenticators

The [Authenticator][] is the mechanism for authorizing users.
Basic authenticators use simple username and password authentication.
JupyterHub ships only with the default [PAM][]-based Authenticator,
for logging in with local user accounts.

You can use custom Authenticator subclasses to enable authentication
via other mechanisms. One such example is using [GitHub OAuth][].

Because the username is passed from the Authenticator to the Spawner,
a custom Authenticator and Spawner are often used together.

See a list of custom Authenticators [on the wiki](https://github.com/jupyterhub/jupyterhub/wiki/Authenticators).


A basic Authenticator has one central method:

### Authenticator.authenticate

    Authenticator.authenticate(handler, data)

This method is passed the Tornado `RequestHandler` and the `POST data`
from JupyterHub's login form. Unless the login form has been customized,
`data` will have two keys:

- `username`
- `password`

The `authenticate` method's job is simple:

- return the username (non-empty str) of the authenticated user if
  authentication is successful
- return `None` otherwise

Writing an Authenticator that looks up passwords in a dictionary
requires only overriding this one method:

```python
from tornado import gen
from IPython.utils.traitlets import Dict
from jupyterhub.auth import Authenticator

class DictionaryAuthenticator(Authenticator):

    passwords = Dict(config=True,
        help="""dict of username:password for authentication"""
    )

    @gen.coroutine
    def authenticate(self, handler, data):
        if self.passwords.get(data['username']) == data['password']:
            return data['username']
```

## Normalize usernames

Since the Authenticator and Spawner both use the same username,
sometimes you want to transform the name coming from the authentication service
(e.g. turning email addresses into local system usernames) before adding them to the Hub service.
Authenticators can define `normalize_username`, which takes a username.
The default normalization is to cast names to lowercase

For simple mappings, a configurable dict `Authenticator.username_map` is used to turn one name into another:

```python
c.Authenticator.username_map  = {
  'service-name': 'localname'
}
```

## Validate usernames

In most cases, there is a very limited set of acceptable usernames.
Authenticators can define `validate_username(username)`,
which should return True for a valid username and False for an invalid one.
The primary effect this has is improving error messages during user creation.

The default behavior is to use configurable `Authenticator.username_pattern`,
which is a regular expression string for validation.

To only allow usernames that start with 'w':

```python
c.Authenticator.username_pattern = r'w.*'
```

## How to use OAuth and other non-password logins

Some login mechanisms, such as [OAuth][], don't map onto username and
password authentication, and instead use tokens. When using these
mechanisms, you can override the login handlers.

You can see an example implementation of an Authenticator that uses
[GitHub OAuth][] at [OAuthenticator][].

## How to write a custom authenticator

If you are interested in writing a custom authenticator, you can read
[this tutorial](http://jupyterhub-tutorial.readthedocs.io/en/latest/authenticators.html).

[Authenticator]: https://github.com/jupyterhub/jupyterhub/blob/master/jupyterhub/auth.py
[PAM]: https://en.wikipedia.org/wiki/Pluggable_authentication_module
[OAuth]: https://en.wikipedia.org/wiki/OAuth
[GitHub OAuth]: https://developer.github.com/v3/oauth/
[OAuthenticator]: https://github.com/jupyterhub/oauthenticator
