# Authentication and User Basics

The default Authenticator uses [PAM][] to authenticate system users with
their username and password. With the default Authenticator, any user
with an account and password on the system will be allowed to login.

## Create a set of allowed users

You can restrict which users are allowed to login with a set,
`Authenticator.allowed_users`:

```python
c.Authenticator.allowed_users = {'mal', 'zoe', 'inara', 'kaylee'}
```

Users in the `allowed_users` set are added to the Hub database when the Hub is
started.

## Configure admins (`admin_users`)

```{note}
As of JupyterHub 2.0, the full permissions of `admin_users`
should not be required.
Instead, you can assign [roles][] to users or groups
with only the scopes they require.
```

Admin users of JupyterHub, `admin_users`, can add and remove users from
the user `allowed_users` set. `admin_users` can take actions on other users'
behalf, such as stopping and restarting their servers.

A set of initial admin users, `admin_users` can be configured as follows:

```python
c.Authenticator.admin_users = {'mal', 'zoe'}
```

Users in the admin set are automatically added to the user `allowed_users` set,
if they are not already present.

Each authenticator may have different ways of determining whether a user is an
administrator. By default JupyterHub uses the PAMAuthenticator which provides the
`admin_groups` option and can set administrator status based on a user
group. For example we can let any user in the `wheel` group be admin:

```python
c.PAMAuthenticator.admin_groups = {'wheel'}
```

## Give admin access to other users' notebook servers (`admin_access`)

Since the default `JupyterHub.admin_access` setting is `False`, the admins
do not have permission to log in to the single user notebook servers
owned by _other users_. If `JupyterHub.admin_access` is set to `True`,
then admins have permission to log in _as other users_ on their
respective machines, for debugging. **As a courtesy, you should make
sure your users know if admin_access is enabled.**

## Add or remove users from the Hub

Users can be added to and removed from the Hub via either the admin
panel or the REST API. When a user is **added**, the user will be
automatically added to the `allowed_users` set and database. Restarting the Hub
will not require manually updating the `allowed_users` set in your config file,
as the users will be loaded from the database.

After starting the Hub once, it is not sufficient to **remove** a user
from the allowed users set in your config file. You must also remove the user
from the Hub's database, either by deleting the user from JupyterHub's
admin page, or you can clear the `jupyterhub.sqlite` database and start
fresh.

## Use LocalAuthenticator to create system users

The `LocalAuthenticator` is a special kind of authenticator that has
the ability to manage users on the local system. When you try to add a
new user to the Hub, a `LocalAuthenticator` will check if the user
already exists. If you set the configuration value, `create_system_users`,
to `True` in the configuration file, the `LocalAuthenticator` has
the privileges to add users to the system. The setting in the config
file is:

```python
c.LocalAuthenticator.create_system_users = True
```

Adding a user to the Hub that doesn't already exist on the system will
result in the Hub creating that user via the system `adduser` command
line tool. This option is typically used on hosted deployments of
JupyterHub, to avoid the need to manually create all your users before
launching the service. This approach is not recommended when running
JupyterHub in situations where JupyterHub users map directly onto the
system's UNIX users.

## Use OAuthenticator to support OAuth with popular service providers

JupyterHub's [OAuthenticator][] currently supports the following
popular services:

- Auth0
- Azure AD
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

## Use DummyAuthenticator for testing

The `DummyAuthenticator` is a simple authenticator that
allows for any username/password unless a global password has been set. If
set, it will allow for any username as long as the correct password is provided.
To set a global password, add this to the config file:

```python
c.DummyAuthenticator.password = "some_password"
```

[pam]: https://en.wikipedia.org/wiki/Pluggable_authentication_module
[oauthenticator]: https://github.com/jupyterhub/oauthenticator
