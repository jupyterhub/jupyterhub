# How JupyterHub works

JupyterHub is a multi-user server that manages and proxies multiple instances of the single-user Jupyter notebook server.

There are three basic processes involved:

- multi-user Hub (Python/Tornado)
- [configurable http proxy](https://github.com/jupyterhub/configurable-http-proxy) (node-http-proxy)
- multiple single-user IPython notebook servers (Python/IPython/Tornado)

The proxy is the only process that listens on a public interface.
The Hub sits behind the proxy at `/hub`.
Single-user servers sit behind the proxy at `/user/[username]`.


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


## Customizing  JupyterHub

There are two basic extension points for JupyterHub: How users are authenticated,
and how their server processes are started.
Each is governed by a customizable class,
and JupyterHub ships with just the most basic version of each.

To enable custom authentication and/or spawning,
subclass Authenticator or Spawner,
and override the relevant methods.


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
