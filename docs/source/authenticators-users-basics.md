# Authentication and Users

The default Authenticator uses [PAM][] to authenticate system users with
their username and password. The default behavior of this Authenticator
is to allow any user with an account and password on the system to login.

## Creating a whitelist of users

You can restrict which users are allowed to login with `Authenticator.whitelist`:


```python
c.Authenticator.whitelist = {'mal', 'zoe', 'inara', 'kaylee'}
```

Users listed in the whitelist are added to the Hub database when the Hub is
started.

## Managing Hub administrators

### Configuring admins (`admin_users`)

Admin users of JupyterHub, `admin_users`, have the ability to add and remove
users from the user `whitelist` or to take actions on the users' behalf,
such as stopping and restarting their servers.

A set of initial admin users, `admin_users` can configured be as follows:

```python
c.Authenticator.admin_users = {'mal', 'zoe'}
```
Users in the admin list are automatically added to the user `whitelist`,
if they are not already present.

### Admin access to other users' notebook servers (`admin_access`)

By default the admin users do not have permission to log in *as other users*
since the default `JupyterHub.admin_access` setting is False.
If `JupyterHub.admin_access` is set to True, then admin users have permission
to log in *as other users* on their respective machines, for debugging.
**You should make sure your users know if admin_access is enabled.**

Note: additional configuration examples are provided in this guide's
[Configuration Examples section](./config-examples.html).

### Add or remove users from the Hub

Users can be added to and removed from the Hub via either the admin panel or
REST API.

If a user is **added**, the user will be automatically added to the whitelist
and database. Restarting the Hub will not require manually updating the
whitelist in your config file, as the users will be loaded from the database.

After starting the Hub once, it is not sufficient to **remove** a user from
the whitelist in your config file. You must also remove the user from the Hub's
database, either by deleting the user from the admin page, or you can clear
the `jupyterhub.sqlite` database and start fresh.

The default `PAMAuthenticator` is one case of a special kind of authenticator, called a
`LocalAuthenticator`, indicating that it manages users on the local system. When you add a user to
the Hub, a `LocalAuthenticator` checks if that user already exists. Normally, there will be an
error telling you that the user doesn't exist. If you set the configuration value

```python
c.LocalAuthenticator.create_system_users = True
```

however, adding a user to the Hub that doesn't already exist on the system will result in the Hub
creating that user via the system `adduser` command line tool. This option is typically used on
hosted deployments of JupyterHub, to avoid the need to manually create all your users before
launching the service. It is not recommended when running JupyterHub in situations where
JupyterHub users maps directly onto UNIX users.

[PAM]: https://en.wikipedia.org/wiki/Pluggable_authentication_module
