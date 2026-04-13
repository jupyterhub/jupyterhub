(howto:upgrading-v6)=

# Upgrading to JupyterHub 6

This document describes considerations specific to the JupyterHub 6 upgrade.
For general upgrading tips, see the [docs on upgrading jupyterhub](upgrading).

You can see the [changelog](changelog) for more detailed information.

## Python version

JupyterHub 6 requires Python 3.10.
Make sure you have at least Python 3.10 in your user and hub environments before upgrading.

## Database upgrades

JupyterHub 6 include a database schema upgrade,
so you should backup your database and run `jupyterhub upgrade-db` after upgrading and before starting JupyterHub.

## Named server restrictions

Prior to JupyterHub 6 there were almost no restrictions on the naming of named servers.
Core JupyterHub components correctly handled these, but names with unsual characters caused problems for some extensions, or when interacting with external components.

JupyterHub 6 imposes strict limits on the naming of named servers:

- Between 1 and 32 characters
- Consists of lowercase ASCII letters, digits, and zero or one hyphen (`-`)
- Must start with a lowercase letter
- Must end with a lowercase letter or digit

A new field `display_name` means users can still provide an arbitrary name, separate from the server name.

### Web interface

Users can name a named server as normal.
This will be used as the display_name, and if this doesn't comply with the above restriction a server name will be automatically generated.
The server name is used in labels, URL, etc.

### API

API clients that create named servers must provide a name that complies with the above restrictions.
They can optionally provide a user-facing display_name.

### Migrating old named servers

A new `c.JupyterHub.allow_existing_invalid_named_servers` property controls how named servers created prior to JupyterHub 6 are handled.

JupyterHub can automatically migrate servers, but this is not safe to run unless your spawner keeps track of all external resources such as storage volumes/paths.
For example, if you currently mount the filesystem path `/data/USERNAME/INVALID-SERVERNAME` into the JupyterHub singleuser server and the servername is automatically migrated to `NEW-SERVERNAME`, when the server is started it will mount `/data/USERNAME/NEW-SERVERNAME` instead of the original path.

If this is the case we recommend you:

- create a new named server
- copy the data from the old path to the new path
- delete the old named server

To automatically migrate non-compliant named servers when JupyterHub starts set

```python
c.JupyterHub.allow_existing_invalid_named_servers = "autorename"
```

If a server has to be migrated its display_name will be set to the current server name, and a new compliant server name will be generated.
if `c.JupyterHub.cleanup_servers = False` and a running server has a non-compliant name it will not be migrated, ensure the server is shutdown before the hub is next restarted.

The default

```python
c.JupyterHub.allow_existing_invalid_named_servers = "allow-start"
```

allows named servers with non-compliant names to be started, stopped, and deleted.
Use this if you are unable to migrate servers.

```python
c.JupyterHub.allow_existing_invalid_named_servers = "allow-delete"
```

allows named servers with non-compliant names to be stopped and deleted.
This is to support migration of named servers which is unsafe to do with a running server.

There is no option to create named servers with non-compliant names.

Support for non-compliant names will be completely dropped in JupyterHub 7, i.e. it will be impossible to start those servers.
