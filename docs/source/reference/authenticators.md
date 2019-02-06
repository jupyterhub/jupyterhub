# Authenticators

The [Authenticator][] is the mechanism for authorizing users to use the
Hub and single user notebook servers.

## The default PAM Authenticator

JupyterHub ships with the default [PAM][]-based Authenticator, for
logging in with local user accounts via a username and password.

## The OAuthenticator

Some login mechanisms, such as [OAuth][], don't map onto username and
password authentication, and instead use tokens. When using these
mechanisms, you can override the login handlers.

You can see an example implementation of an Authenticator that uses
[GitHub OAuth][] at [OAuthenticator][].

JupyterHub's [OAuthenticator][] currently supports the following
popular services:

- Auth0
- Bitbucket
- CILogon
- GitHub
- GitLab
- Globus
- Google
- MediaWiki
- Okpy
- OpenShift

A generic implementation, which you can use for OAuth authentication
with any provider, is also available.

## The Dummy Authenticator

When testing, it may be helpful to use the
:class:`~jupyterhub.auth.DummyAuthenticator`. This allows for any username and
password unless if a global password has been set. Once set, any username will
still be accepted but the correct password will need to be provided.

## Additional Authenticators

A partial list of other authenticators is available on the
[JupyterHub wiki](https://github.com/jupyterhub/jupyterhub/wiki/Authenticators).

## Technical Overview of Authentication

### How the Base Authenticator works

The base authenticator uses simple username and password authentication.

The base Authenticator has one central method:

#### Authenticator.authenticate method

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
from IPython.utils.traitlets import Dict
from jupyterhub.auth import Authenticator

class DictionaryAuthenticator(Authenticator):

    passwords = Dict(config=True,
        help="""dict of username:password for authentication"""
    )

    async def authenticate(self, handler, data):
        if self.passwords.get(data['username']) == data['password']:
            return data['username']
```


#### Normalize usernames

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

When using `PAMAuthenticator`, you can set
`c.PAMAuthenticator.pam_normalize_username = True`, which will
normalize usernames using PAM (basically round-tripping them: username
to uid to username), which is useful in case you use some external
service that allows multiple usernames mapping to the same user (such
as ActiveDirectory, yes, this really happens).  When
`pam_normalize_username` is on, usernames are *not* normalized to
lowercase.


#### Validate usernames

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


### How to write a custom authenticator

You can use custom Authenticator subclasses to enable authentication
via other mechanisms. One such example is using [GitHub OAuth][].

Because the username is passed from the Authenticator to the Spawner,
a custom Authenticator and Spawner are often used together.
For example, the Authenticator methods, [pre_spawn_start(user, spawner)][]
and [post_spawn_stop(user, spawner)][], are hooks that can be used to do
auth-related startup (e.g. opening PAM sessions) and cleanup
(e.g. closing PAM sessions).


See a list of custom Authenticators [on the wiki](https://github.com/jupyterhub/jupyterhub/wiki/Authenticators).

If you are interested in writing a custom authenticator, you can read
[this tutorial](http://jupyterhub-tutorial.readthedocs.io/en/latest/authenticators.html).

### Registering custom Authenticators via entry points

As of JupyterHub 1.0, custom authenticators can register themselves via
the `jupyterhub.authenticators` entry point metadata.
To do this, in your `setup.py` add:

```python
setup(
  ...
  entry_points={
    'jupyterhub.authenticators': [
        'myservice = mypackage:MyAuthenticator',
    ],
  },
)
```

If you have added this metadata to your package,
users can select your authenticator with the configuration:

```python
c.JupyterHub.authenticator_class = 'myservice'
```

instead of the full

```python
c.JupyterHub.authenticator_class = 'mypackage:MyAuthenticator'
```

previously required.
Additionally, configurable attributes for your authenticator will
appear in jupyterhub help output and auto-generated configuration files
via `jupyterhub --generate-config`.


### Authentication state

JupyterHub 0.8 adds the ability to persist state related to authentication,
such as auth-related tokens.
If such state should be persisted, `.authenticate()` should return a dictionary of the form:

```python
{
  'name': username,
  'auth_state': {
    'key': 'value',
  }
}
```

where `username` is the username that has been authenticated,
and `auth_state` is any JSON-serializable dictionary.

Because `auth_state` may contain sensitive information,
it is encrypted before being stored in the database.
To store auth_state, two conditions must be met:

1. persisting auth state must be enabled explicitly via configuration
   ```python
   c.Authenticator.enable_auth_state = True
   ```
2. encryption must be enabled by the presence of `JUPYTERHUB_CRYPT_KEY` environment variable,
   which should be a hex-encoded 32-byte key.
   For example:
   ```bash
   export JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)
   ```


JupyterHub uses [Fernet](https://cryptography.io/en/latest/fernet/) to encrypt auth_state.
To facilitate key-rotation, `JUPYTERHUB_CRYPT_KEY` may be a semicolon-separated list of encryption keys.
If there are multiple keys present, the **first** key is always used to persist any new auth_state.


#### Using auth_state

Typically, if `auth_state` is persisted it is desirable to affect the Spawner environment in some way.
This may mean defining environment variables, placing certificate in the user's home directory, etc.
The `Authenticator.pre_spawn_start` method can be used to pass information from authenticator state
to Spawner environment:

```python
class MyAuthenticator(Authenticator):
    @gen.coroutine
    def authenticate(self, handler, data=None):
        username = yield identify_user(handler, data)
        upstream_token = yield token_for_user(username)
        return {
            'name': username,
            'auth_state': {
                'upstream_token': upstream_token,
            },
        }

    @gen.coroutine
    def pre_spawn_start(self, user, spawner):
        """Pass upstream_token to spawner via environment variable"""
        auth_state = yield user.get_auth_state()
        if not auth_state:
            # auth_state not enabled
            return
        spawner.environment['UPSTREAM_TOKEN'] = auth_state['upstream_token']
```

## pre_spawn_start and post_spawn_stop hooks

Authenticators uses two hooks, [pre_spawn_start(user, spawner)][] and
[post_spawn_stop(user, spawner)][] to add pass additional state information
between the authenticator and a spawner. These hooks are typically used auth-related
startup, i.e. opening a PAM session, and auth-related cleanup, i.e. closing a
PAM session.

## JupyterHub as an OAuth provider

Beginning with version 0.8, JupyterHub is an OAuth provider.


[Authenticator]: https://github.com/jupyterhub/jupyterhub/blob/master/jupyterhub/auth.py
[PAM]: https://en.wikipedia.org/wiki/Pluggable_authentication_module
[OAuth]: https://en.wikipedia.org/wiki/OAuth
[GitHub OAuth]: https://developer.github.com/v3/oauth/
[OAuthenticator]: https://github.com/jupyterhub/oauthenticator
[pre_spawn_start(user, spawner)]: https://jupyterhub.readthedocs.io/en/latest/api/auth.html#jupyterhub.auth.Authenticator.pre_spawn_start
[post_spawn_stop(user, spawner)]: https://jupyterhub.readthedocs.io/en/latest/api/auth.html#jupyterhub.auth.Authenticator.post_spawn_stop
