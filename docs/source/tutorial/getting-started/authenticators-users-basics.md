(authenticators)=

# Authentication and User Basics

The default Authenticator uses [PAM][] (Pluggable Authentication Module) to authenticate system users with
their usernames and passwords. With the default Authenticator, any user
with an account and password on the system will be allowed to login.

## Deciding who is allowed

In the base Authenticator, there are 3 configuration options for granting users access to your Hub:

1. `allow_all` grants any user who can successfully authenticate access to the Hub
2. `allowed_users` defines a set of users who can access the Hub
3. `allow_existing_users` enables managing users via the JupyterHub API or admin page

These options should apply to all Authenticators.
Your chosen Authenticator may add additional configuration options to admit users, such as team membership, course enrollment, etc.

:::{important}
You should always specify at least one allow configuration if you want people to be able to access your Hub!
In most cases, this looks like:

```python
c.Authenticator.allow_all = True
# or
c.Authenticator.allowed_users = {"name", ...}
```

:::

:::{versionchanged} 5.0
If no allow config is specified, then by default **nobody will have access to your Hub**.
Prior to 5.0, the opposite was true; effectively `allow_all = True` if no other allow config was specified.
:::

You can restrict which users are allowed to login with a set,
`Authenticator.allowed_users`:

```python
c.Authenticator.allowed_users = {'mal', 'zoe', 'inara', 'kaylee'}
# c.Authenticator.allow_all = False
c.Authenticator.allow_existing_users = False
```

Users in the `allowed_users` set are added to the Hub database when the Hub is started.

:::{versionchanged} 5.0
{attr}`.Authenticator.allow_all` and {attr}`.Authenticator.allow_existing_users` are new in JupyterHub 5.0
to enable explicit configuration of previously implicit behavior.

Prior to 5.0, `allow_all` was implicitly True if `allowed_users` was empty.
Starting with 5.0, to allow all authenticated users by default,
`allow_all` must be explicitly set to True.

By default, `allow_existing_users` is True when `allowed_users` is not empty,
to ensure backward-compatibility.
To make the `allowed_users` set _restrictive_,
set `allow_existing_users = False`.
:::

## One Time Passwords ( request_otp )

By setting `request_otp` to true, the login screen will show and additional password input field
to accept an OTP:

```python
c.Authenticator.request_otp = True
```

By default, the prompt label is `OTP:`, but this can be changed by setting `otp_prompt`:

```python
c.Authenticator.otp_prompt = 'Google Authenticator:'
```

## Configure admins (`admin_users`)

```{note}
As of JupyterHub 2.0, the full permissions of `admin_users`
should not be required.
Instead, it is best to assign [roles](define-role-target) to users or groups
with only the scopes they require.
```

Admin users of JupyterHub, `admin_users`, can add and remove users from
the user `allowed_users` set. `admin_users` can take actions on other users'
behalf, such as stopping and restarting their servers.

A set of initial admin users, `admin_users` can be configured as follows:

```python
c.Authenticator.admin_users = {'mal', 'zoe'}
```

:::{warning}
`admin_users` config can only be used to _grant_ admin permissions.
Removing users from this set **does not** remove their admin permissions,
which must be done via the admin page or API.

Role assignments via `load_roles` are the only way to _revoke_ past permissions from configuration:

```python
c.JupyterHub.load_roles = [
    {
        "name": "admin",
        "users": ["admin1", "..."],
    }
]
```

or, better yet, [specify your own roles](define-role-target) with only the permissions your admins actually need.
:::

Users in the admin set are automatically added to the user `allowed_users` set,
if they are not already present.

Each Authenticator may have different ways of determining whether a user is an
administrator. By default, JupyterHub uses the PAMAuthenticator which provides the
`admin_groups` option and can set administrator status based on a user
group. For example, we can let any user in the `wheel` group be an admin:

```python
c.PAMAuthenticator.admin_groups = {'wheel'}
```

## Give some users access to other users' notebook servers

The `access:servers` scope can be granted to users to give them permission to visit other users' servers.
For example, to give members of the `teachers` group access to the servers of members of the `students` group:

```python
c.JupyterHub.load_roles = [
  {
    "name": "teachers",
    "scopes": [
      "admin-ui",
      "list:users",
      "access:servers!group=students",
    ],
    "groups": ["teachers"],
  }
]
```

By default, only the deprecated `admin` role has global `access` permissions.
**As a courtesy, you should make sure your users know if admin access is enabled.**

## Add or remove users from the Hub

:::{versionadded} 5.0
`c.Authenticator.allow_existing_users` is added in 5.0 and True by default _if_ any `allowed_users` are specified.

Prior to 5.0, this behavior was not optional.
:::

Users can be added to and removed from the Hub via the admin
panel or the REST API.

To enable this behavior, set:

```python
c.Authenticator.allow_existing_users = True
```

When a user is **added**, the user will be
automatically added to the `allowed_users` set and database.
If `allow_existing_users` is True, restarting the Hub will not require manually updating the `allowed_users` set in your config file,
as the users will be loaded from the database.
If `allow_existing_users` is False, users not granted access by configuration such as `allowed_users` will not be permitted to login,
even if they are present in the database.

After starting the Hub once, it is not sufficient to **remove** a user
from the allowed users set in your config file. You must also remove the user
from the Hub's database, either by deleting the user via JupyterHub's
admin page, or you can clear the `jupyterhub.sqlite` database and start
fresh.

## Use LocalAuthenticator to create system users

The `LocalAuthenticator` is a special kind of Authenticator that has
the ability to manage users on the local system. When you try to add a
new user to the Hub, a `LocalAuthenticator` will check if the user
already exists. If you set the configuration value, `create_system_users`,
to `True` in the configuration file, the `LocalAuthenticator` has
the ability to add users to the system. The setting in the config
file is:

```python
c.LocalAuthenticator.create_system_users = True
```

Adding a user to the Hub that doesn't already exist on the system will
result in the Hub creating that user via the system `adduser` command
line tool. This option is typically used on hosted deployments of
JupyterHub to avoid the need to manually create all your users before
launching the service. This approach is not recommended when running
JupyterHub in situations where JupyterHub users map directly onto the
system's UNIX users.

## Use OAuthenticator to support OAuth with popular service providers

JupyterHub's [OAuthenticator][] currently supports the following
popular services:

- [Auth0](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.auth0.html)
- [Azure AD](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.azuread.html)
- [Bitbucket](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.bitbucket.html)
- [CILogon](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.cilogon.html)
- [GitHub](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.github.html)
- [GitLab](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.gitlab.html)
- [Globus](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.globus.html)
- [Google](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.google.html)
- [MediaWiki](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.mediawiki.html)
- [OpenShift](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.openshift.html)

A [generic implementation](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.generic.html), which you can use for OAuth authentication
with any provider, is also available.

## Use DummyAuthenticator for testing

The `DummyAuthenticator` is a simple Authenticator that
allows for any username or password unless a global password has been set. If
set, it will allow for any username as long as the correct password is provided.
To set a global password, add this to the config file:

```python
c.DummyAuthenticator.password = "some_password"
```

[pam]: https://en.wikipedia.org/wiki/Pluggable_authentication_module
[oauthenticator]: https://github.com/jupyterhub/oauthenticator
