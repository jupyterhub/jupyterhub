(howto:upgrading-v5)=

# Upgrading to JupyterHub 5

This document describes the specific considerations.
For general upgrading tips, see the [docs on upgrading jupyterhub](upgrading).

You can see the [changelog](changelog) for more detailed information.

## Python version

JupyterHub 5 requires Python 3.8.
Make sure you have at least Python 3.8 in your user and hub environments before upgrading.

## Database upgrades

JupyterHub 5 does have a database schema upgrade,
so you should backup your database and run `jupyterhub upgrade-db` after upgrading and before starting JupyterHub.
The updated schema only adds some columns, so is one that should be not too disruptive to roll back if you need to.

## User subdomains

All JupyterHub deployments which care about protecting users from each other are encouraged to enable per-user domains, if possible,
as this provides the best isolation between user servers.

To enable subdomains, set:

```python
c.JupyterHub.subdomain_host = "https://myjupyterhub.example.org"
```

If you were using subdomains before, some user servers and all services will be on different hosts in the default configuration.

JupyterHub 5 allows complete customization of the subdomain scheme via the new {attr}`.JupyterHub.subdomain_hook`,
and changes the default subdomain scheme.
.

You can provide a completely custom subdomain scheme, or select one of two default implementations by name: `idna` or `legacy`. `idna` is the default.

The new default behavior can be selected explicitly via:

```python
c.JupyterHub.subdomain_hook = "idna"
```

Or to delay any changes to URLs for your users, you can opt-in to the pre-5.0 behavior with:

```python
c.JupyterHub.subdomain_hook = "legacy"
```

The key differences of the new `idna` scheme:

- It should always produce valid domains, regardless of username (not true for the legacy scheme when using characters that might need escaping or usernames that are long)
- each Service gets its own subdomain on `service--` rather than sharing `services.`

Below is a table of examples of users and services with their domains with the old and new scheme, assuming the configuration:

```python
c.JupyterHub.subdomain_host = "https://jupyter.example.org"
```

| kind    | name               | legacy                                                     | idna                                                                                                  |
| ------- | ------------------ | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| user    | laudna             | `laudna.jupyter.example.org`                               | `laudna.jupyter.example.org`                                                                          |
| service | bells              | `services.jupyter.example.org`                             | `bells--service.jupyter.example.org`                                                                  |
| user    | jester@mighty.nein | `jester_40mighty.nein.jupyter.example.org` (may not work!) | `u-jestermi--8037680.jupyter.example.org` (not as pretty, but guaranteed to be valid and not collide) |

## Tokens in URLs

JupyterHub 5 does not accept `?token=...` URLs by default in single-user servers.
These URLs allow one user to force another to login as them,
which can be the start of an inter-user attack.

There is a valid use case for producing links which allow starting a fully authenticated session,
so you may still opt in to this behavior by setting:

```python
c.Spawner.environment.update({"JUPYTERHUB_ALLOW_TOKEN_IN_URL": "1"})
```

if you are not concerned about protecting your users from each other.
If you have subdomains enabled, the threat is substantially reduced.

## Sharing

The big new feature in JupyterHub 5.0 is sharing.
Check it out in [the sharing docs](sharing-tutorial).

## Authenticator.allow_all and allow_existing_users

Prior to JupyterHub 5, JupyterHub Authenticators had the _implicit_ default behavior to allow any user who successfully authenticates to login **if no users are explicitly allowed** (i.e. `allowed_users` is empty on the base class).
This behavior was considered a too-permissive default in Authenticators that source large user pools like OAuthenticator, which would accept e.g. all users with a Google account by default.
As a result, OAuthenticator 16 introduced two configuration options: `allow_all` and `allow_existing_users`.

JupyterHub 5 adopts these options for all Authenticators:

1. `Authenticator.allow_all` (default: False)
2. `Authenticator.allow_existing_users` (default: True if allowed_users is non-empty, False otherwise)

having the effect that _some_ allow configuration is required for anyone to be able to login.
If you want to preserve the pre-5.0 behavior with no explicit `allow` configuration, set:

```python
c.Authenticator.allow_all = True
```

`allow_existing_users` defaults are meant to be backward-compatible, but you can now _explicitly_ allow or not based on presence in the database by setting `Authenticator.allow_existing_users` to True or False.

:::{seealso}

[Authenticator config docs](authenticators) for details on these and other Authenticator options.
:::

## Bootstrap 5

JupyterHub uses the CSS framework [bootstrap](https://getbootstrap.com), which is upgraded from 3.4 to 5.3.
If you don't have any custom HTML templates, you are likely to only see relatively minor aesthetic changes.
If you have custom HTML templates or spawner options forms, they may need some updating to look right.

See the bootstrap documentation. Since we upgraded two major versions, you might need to look at both v4 and v5 documentation for what has changed since 3.x:

- [migrating to v4](https://getbootstrap.com/docs/4.6/migration/)
- [migrating to v5](https://getbootstrap.com/docs/5.3/migration/)

If you customized the JupyterHub CSS by recompiling from LESS files, bootstrap migrated to SCSS.
You can start by autoconverting your LESS to SCSS (it's not that different) with [less2sass](https://github.com/ekryski/less2sass):

```bash
npm install --global less2scss
# converts less/foo.less to scss/foo.scss
less2scss --src ./less --dst ./scss
```

Bootstrap also allows configuring things with [CSS variables](https://getbootstrap.com/docs/5.3/customize/css-variables/), so depending on what you have customized, you may be able to get away with just adding a CSS file defining variables without rebuilding the whole SCSS.

## groups required with Authenticator.manage_groups

Setting `Authenticator.manage_groups = True` allows the Authenticator to manage group membership by returning `groups` from the authentication model.
However, this option is available even on Authenticators that do not support it, which led to confusion.
Starting with JupyterHub 5, if `manage_groups` is True `authenticate` _must_ return a groups field, otherwise an error is raised.
This prevents confusion when users enable managed groups that is not implemented.

If an Authenticator _does_ support managing groups but was not providing a `groups` field in order to leave membership unmodified, it must specify `"groups": None` to make this explicit instead of implicit (this is backward-compatible).
