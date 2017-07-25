# Technical Overview

JupyterHub is a set of processes that together provide a single user Jupyter
Notebook server for each person in a group.

This section gives you an overview of:
- JupyterHub's subsystems
- basic operations
- logging in
-

## Subsystems of JupyterHub

Three major subsystems are started by the `jupyterhub` command line program:

- **Hub** (Python/Tornado): manages user accounts, authentication, and
  coordinates Single User Notebook Servers using a Spawner.

- **Proxy**: the public facing part of JupyterHub that uses a dynamic proxy
  to route HTTP requests to the Hub and Single User Notebook Servers.
  [configurable http proxy](https://github.com/jupyterhub/configurable-http-proxy)
  (node-http-proxy) is the default proxy.

- **Single-User Notebook Server** (Python/IPython/Tornado): a dedicated,
  single-user, Jupyter Notebook server is started for each user on the system
  when the user logs in. The object that starts the single-user notebook
  servers is called a **Spawner**.    

![JupyterHub subsystems](images/jhub-parts.png)

## Basic operation

Users access JupyterHub through a web browser, by going to the IP address or
the domain name of the server.

The basic principles of operation are:

- The Hub spawns proxy
- The proxy forwards all requests to the Hub by default
- The Hub handles login, and spawns single-user notebook servers on demand
- The Hub configures the proxy to forward url prefixes to single-user notebook
  servers

The proxy is the only process that listens on a public interface. The Hub sits
behind the proxy at `/hub`. Single-user servers sit behind the proxy at
`/user/[username]`.

Different **[authenticators](authenticators.html)** control access
to JupyterHub. The default one (PAM) uses the user accounts on the server where
JupyterHub is running. If you use this, you will need to create a user account
on the system for each user on your team. Using other authenticators, you can
allow users to sign in with e.g. a GitHub account, or with any single-sign-on
system your organization has.

Next, **[spawners](spawners.html)** control how JupyterHub starts
the individual notebook server for each user. The default spawner will
start a notebook server on the same machine running under their system username.
The other main option is to start each server in a separate container, often
using Docker.

## Logging in

When a new browser logs in to JupyterHub, the following events take place:

- Login data is handed to the [Authenticator](#authentication) instance for validation
- The Authenticator returns the username, if login information is valid
- A single-user server instance is [Spawned](#spawning) for the logged-in user
- When the server starts, the proxy is notified to forward `/user/[username]/*` to the single-user server
- Two cookies are set, one for `/hub/` and another for `/user/[username]`,
  containing an encrypted token.
- The browser is redirected to `/user/[username]`, which is handled by the single-user server

Logging into a single-user server is authenticated via the Hub:

- On request, the single-user server forwards the encrypted cookie to the Hub for verification
- The Hub replies with the username if it is a valid cookie
- If the user is the owner of the server, access is allowed
- If it is the wrong user or an invalid cookie, the browser is redirected to `/hub/login`

## Customizing JupyterHub

There are two basic extension points for JupyterHub: How users are authenticated,
and how their server processes are started.
Each is governed by a customizable class,
and JupyterHub ships with just the most basic version of each.

To enable custom authentication and/or spawning,
subclass Authenticator or Spawner,
and override the relevant methods.

## Default behavior

**IMPORTANT: You should not run JupyterHub without SSL encryption on a public network.**

See [Security documentation](#security) for how to configure JupyterHub to use SSL,
or put it behind SSL termination in another proxy server, such as nginx.

To start JupyterHub in its default configuration, type the following at the command line:

```bash
    sudo jupyterhub
```

The default Authenticator that ships with JupyterHub authenticates users
with their system name and password (via [PAM][]).
Any user on the system with a password will be allowed to start a single-user notebook server.

The default Spawner starts servers locally as each user, one dedicated server per user.
These servers listen on localhost, and start in the given user's home directory.

By default, the **Proxy** listens on all public interfaces on port 8000.
Thus you can reach JupyterHub through either:

- `http://localhost:8000`
- or any other public IP or domain pointing to your system.

In their default configuration, the other services, the **Hub** and **Single-User Servers**,
all communicate with each other on localhost only.

By default, starting JupyterHub will write two files to disk in the current working directory:

- `jupyterhub.sqlite` is the sqlite database containing all of the state of the **Hub**.
  This file allows the **Hub** to remember what users are running and where,
  as well as other information enabling you to restart parts of JupyterHub separately. It is
  important to note that this database contains *no* sensitive information other than **Hub**
  usernames.
- `jupyterhub_cookie_secret` is the encryption key used for securing cookies.
  This file needs to persist in order for restarting the Hub server to avoid invalidating cookies.
  Conversely, deleting this file and restarting the server effectively invalidates all login cookies.
  The cookie secret file is discussed in the [Cookie Secret documentation](#cookie-secret).

The location of these files can be specified via configuration.

[PAM]: https://en.wikipedia.org/wiki/Pluggable_authentication_module

### Authentication

Authentication is customizable via the Authenticator class.
Authentication can be replaced by any mechanism,
such as OAuth, Kerberos, etc.

JupyterHub only ships with [PAM](https://en.wikipedia.org/wiki/Pluggable_authentication_module) authentication,
which requires the server to be run as root,
or at least with access to the PAM service,
which regular users typically do not have
(on Ubuntu, this requires being added to the `shadow` group).

[More info on custom Authenticators](authenticators.html).

See a list of custom Authenticators [on the wiki](https://github.com/jupyterhub/jupyterhub/wiki/Authenticators).


### Spawning

Each single-user server is started by a Spawner.
The Spawner represents an abstract interface to a process,
and needs to be able to take three actions:

1. start the process
2. poll whether the process is still running
3. stop the process

[More info on custom Spawners](spawners.html).

See a list of custom Spawners [on the wiki](https://github.com/jupyterhub/jupyterhub/wiki/Spawners).
