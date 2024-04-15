(authenticators-reference)=

# Authenticators

The {class}`.Authenticator` is the mechanism for authorizing users to use the
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
- OpenShift

A [generic implementation](https://github.com/jupyterhub/oauthenticator/blob/master/oauthenticator/generic.py), which you can use for OAuth authentication with any provider, is also available.

## The Dummy Authenticator

When testing, it may be helpful to use the
{class}`~.jupyterhub.auth.DummyAuthenticator`. This allows for any username and
password unless a global password has been set. Once set, any username will
still be accepted but the correct password will need to be provided.

:::{versionadded} 5.0
The DummyAuthenticator's default `allow_all` is True,
unlike most other Authenticators.
:::

## Additional Authenticators

Additional authenticators can be found on GitHub
by searching for [topic:jupyterhub topic:authenticator](https://github.com/search?q=topic%3Ajupyterhub%20topic%3Aauthenticator&type=repositories).

## Technical Overview of Authentication

### How the Base Authenticator works

The base authenticator uses simple username and password authentication.

The base Authenticator has one central method:

#### Authenticator.authenticate

{meth}`.Authenticator.authenticate`

This method is passed the Tornado `RequestHandler` and the `POST data`
from JupyterHub's login form. Unless the login form has been customized,
`data` will have two keys:

- `username`
- `password`

If authentication is successful the `authenticate` method must return either:

- the username (non-empty str) of the authenticated user
- or a dictionary with fields:
  - `name`: the username
  - `admin`: optional, a boolean indicating whether the user is an admin.
    In most cases it is better to use fine grained [RBAC permissions](rbac) instead of giving users full admin privileges.
  - `auth_state`: optional, a dictionary of [auth state that will be persisted](authenticator-auth-state)
  - `groups`: optional, a list of JupyterHub [group memberships](authenticator-groups)

Otherwise, it must return `None`.

Writing an Authenticator that looks up passwords in a dictionary
requires only overriding this one method:

```python
from secrets import compare_digest
from traitlets import Dict
from jupyterhub.auth import Authenticator

class DictionaryAuthenticator(Authenticator):

    passwords = Dict(config=True,
        help="""dict of username:password for authentication"""
    )

    async def authenticate(self, handler, data):
        username = data["username"]
        password = data["password"]
        check_password = self.passwords.get(username, "")
        # always call compare_digest, for timing attacks
        if compare_digest(check_password, password) and username in self.passwords:
            return username
        else:
            return None
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
as ActiveDirectory, yes, this really happens). When
`pam_normalize_username` is on, usernames are _not_ normalized to
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

## How to write a custom authenticator

You can use custom Authenticator subclasses to enable authentication
via other mechanisms. One such example is using [GitHub OAuth][].

Because the username is passed from the Authenticator to the Spawner,
a custom Authenticator and Spawner are often used together.
For example, the Authenticator methods, {meth}`.Authenticator.pre_spawn_start`
and {meth}`.Authenticator.post_spawn_stop`, are hooks that can be used to do
auth-related startup (e.g. opening PAM sessions) and cleanup
(e.g. closing PAM sessions).

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
admins can select your authenticator with the configuration:

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

(authenticator-allow)=

### Allowing access

When dealing with logging in, there are generally two _separate_ steps:

authentication
: identifying who is trying to log in, and

authorization
: deciding whether an authenticated user is allowed to access your JupyterHub

{meth}`Authenticator.authenticate` is responsible for authenticating users.
It is perfectly fine in the simplest cases for `Authenticator.authenticate` to be responsible for authentication _and_ authorization,
in which case `authenticate` may return `None` if the user is not authorized.

However, Authenticators also have two methods, {meth}`~.Authenticator.check_allowed` and {meth}`~.Authenticator.check_blocked_users`, which are called after successful authentication to further check if the user is allowed.

If `check_blocked_users()` returns False, authorization stops and the user is not allowed.

If `Authenticator.allow_all` is True OR `check_allowed()` returns True, authorization proceeds.

:::{versionadded} 5.0
{attr}`.Authenticator.allow_all` and {attr}`.Authenticator.allow_existing_users` are new in JupyterHub 5.0.

By default, `allow_all` is False,
which is a change from pre-5.0, where `allow_all` was implicitly True if `allowed_users` was empty.
:::

### Overriding `check_allowed`

:::{versionchanged} 5.0
`check_allowed()` is **not called** if `allow_all` is True.
:::

:::{versionchanged} 5.0
Starting with 5.0, `check_allowed()` should **NOT** return True if no allow config
is specified (`allow_all` should be used instead).

:::

The base implementation of {meth}`~.Authenticator.check_allowed` checks:

- if username is in the `allowed_users` set, return True
- else return False

:::{versionchanged} 5.0
Prior to 5.0, this would also return True if `allowed_users` was empty.

For clarity, this is no longer the case. A new `allow_all` property (default False) has been added which is checked _before_ calling `check_allowed`.
If `allow_all` is True, this takes priority over `check_allowed`, which will be ignored.

If your Authenticator subclass similarly returns True when no allow config is defined,
this is fully backward compatible for your users, but means `allow_all = False` has no real effect.

You can make your Authenticator forward-compatible with JupyterHub 5 by defining `allow_all` as a boolean config trait on your class:

```python
class MyAuthenticator(Authenticator):

    # backport allow_all from JupyterHub 5
    allow_all = Bool(False, config=True)

    def check_allowed(self, username, authentication):
        if self.allow_all:
            # replaces previous "if no auth config"
            return True
        ...
```

:::

If an Authenticator defines additional sources of `allow` configuration,
such as membership in a group or other information,
it should override `check_allowed` to account for this.

:::{note}
`allow_` configuration should generally be _additive_,
i.e. if access is granted by _any_ allow configuration,
a user should be authorized.

JupyterHub recommends that Authenticators applying _restrictive_ configuration should use names like `block_` or `require_`,
and check this during `check_blocked_users` or `authenticate`, not `check_allowed`.
:::

In general, an Authenticator's skeleton should look like:

```python
class MyAuthenticator(Authenticator):
    # backport allow_all for compatibility with JupyterHub < 5
    allow_all = Bool(False, config=True)
    require_something = List(config=True)
    allowed_something = Set()

    def authenticate(self, data, handler):
        ...
        if success:
            return {"username": username, "auth_state": {...}}
        else:
            return None

    def check_blocked_users(self, username, authentication=None):
        """Apply _restrictive_ configuration"""

        if self.require_something and not has_something(username, self.request_):
            return False
        # repeat for each restriction
        if restriction_defined and restriction_not_met:
            return False
        return super().check_blocked_users(self, username, authentication)

    def check_allowed(self, username, authentication=None):
        """Apply _permissive_ configuration

        Only called if check_blocked_users returns True
        AND allow_all is False
        """
        if self.allow_all:
            # check here to backport allow_all behavior
            # from JupyterHub 5
            # this branch will never be taken with jupyterhub >=5
            return True
        if self.allowed_something and user_has_something(username):
            return True
        # repeat for each allow
        if allow_config and allow_met:
            return True
        # should always have this at the end
        if self.allowed_users and username in self.allowed_users:
            return True
        # do not call super!
        # super().check_allowed is not safe with JupyterHub < 5.0,
        # as it will return True if allowed_users is empty
        return False
```

Key points:

- `allow_all` is backported from JupyterHub 5, for consistent behavior in all versions of JupyterHub (optional)
- restrictive configuration is checked in `check_blocked_users`
- if any restriction is not met, `check_blocked_users` returns False
- permissive configuration is checked in `check_allowed`
- if any `allow` condition is met, `check_allowed` returns True

So the logical expression for a user being authorized should look like:

> if ALL restrictions are met AND ANY admissions are met: user is authorized

#### Custom error messages

Any of these authentication and authorization methods may raise a `web.HTTPError` Exception

```python
from tornado import web

raise web.HTTPError(403, "informative message")
```

if you want to show a more informative login failure message rather than the generic one.

(authenticator-auth-state)=

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
The {meth}`Authenticator.pre_spawn_start` method can be used to pass information from authenticator state
to Spawner environment:

```python
class MyAuthenticator(Authenticator):
    async def authenticate(self, handler, data=None):
        username = await identify_user(handler, data)
        upstream_token = await token_for_user(username)
        return {
            'name': username,
            'auth_state': {
                'upstream_token': upstream_token,
            },
        }

    async def pre_spawn_start(self, user, spawner):
        """Pass upstream_token to spawner via environment variable"""
        auth_state = await user.get_auth_state()
        if not auth_state:
            # auth_state not enabled
            return
        spawner.environment['UPSTREAM_TOKEN'] = auth_state['upstream_token']
```

Note that environment variable names and values are always strings, so passing multiple values means setting multiple environment variables or serializing more complex data into a single variable, e.g. as a JSON string.

auth state can also be used to configure the spawner via _config_ without subclassing
by setting `c.Spawner.auth_state_hook`. This function will be called with `(spawner, auth_state)`,
only when auth_state is defined.

For example:
(for KubeSpawner)

```python
def auth_state_hook(spawner, auth_state):
    spawner.volumes = auth_state['user_volumes']
    spawner.mounts = auth_state['user_mounts']

c.Spawner.auth_state_hook = auth_state_hook
```

(authenticator-groups)=

## Authenticator-managed group membership

:::{versionadded} 2.2
:::

Some identity providers may have their own concept of group membership that you would like to preserve in JupyterHub.
This is now possible with `Authenticator.manage_groups`.

You can set the config:

```python
c.Authenticator.manage_groups = True
```

to enable this behavior.
The default is False for Authenticators that ship with JupyterHub,
but may be True for custom Authenticators.
Check your Authenticator's documentation for `manage_groups` support.

If True, {meth}`.Authenticator.authenticate` and {meth}`.Authenticator.refresh_user` may include a field `groups`
which is a list of group names the user should be a member of:

- Membership will be added for any group in the list
- Membership in any groups not in the list will be revoked
- Any groups not already present in the database will be created
- If `None` is returned, no changes are made to the user's group membership

If authenticator-managed groups are enabled,
all group-management via the API is disabled,
and roles cannot be specified with `load_groups` traitlet.

(authenticator-roles)=

## Authenticator-managed roles

:::{versionadded} 5.0
:::

Some identity providers may have their own concept of role membership that you would like to preserve in JupyterHub.
This is now possible with {attr}`.Authenticator.manage_roles`.

You can set the config:

```python
c.Authenticator.manage_roles = True
```

to enable this behavior.
The default is False for Authenticators that ship with JupyterHub,
but may be True for custom Authenticators.
Check your Authenticator's documentation for `manage_roles` support.

If True, {meth}`.Authenticator.authenticate` and {meth}`.Authenticator.refresh_user` may include a field `roles`
which is a list of roles that user should be assigned to:

- User will be assigned each role in the list
- User will be revoked roles not in the list (but they may still retain the role privileges if they inherit the role from their group)
- Any roles not already present in the database will be created
- Attributes of the roles (`description`, `scopes`, `groups`, `users`, and `services`) will be updated if given
- If `None` is returned, no changes are made to the user's roles

If authenticator-managed roles are enabled,
all role-management via the API is disabled,
and roles cannot be assigned to groups nor users via `load_roles` traitlet
(roles can still be created via `load_roles` or assigned to services).

When an authenticator manages roles, the initial roles and role assignments
can be loaded from role specifications returned by the {meth}`.Authenticator.load_managed_roles()` method.

The authenticator-manged roles and role assignment will be deleted after restart if:

- {attr}`.Authenticator.reset_managed_roles_on_startup` is set to `True`, and
- the roles and role assignments are not included in the initial set of roles returned by the {meth}`.Authenticator.load_managed_roles()` method.

## pre_spawn_start and post_spawn_stop hooks

Authenticators use two hooks, {meth}`.Authenticator.pre_spawn_start` and
{meth}`.Authenticator.post_spawn_stop(user, spawner)` to add pass additional state information
between the authenticator and a spawner. These hooks are typically used auth-related
startup, i.e. opening a PAM session, and auth-related cleanup, i.e. closing a
PAM session.

## JupyterHub as an OAuth provider

Beginning with version 0.8, JupyterHub is an OAuth provider.

[pam]: https://en.wikipedia.org/wiki/Pluggable_authentication_module
[oauth]: https://en.wikipedia.org/wiki/OAuth
[github oauth]: https://developer.github.com/v3/oauth/
[oauthenticator]: https://github.com/jupyterhub/oauthenticator
