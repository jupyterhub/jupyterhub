## Technical Overview

JupyterHub is a set of processes that together provide a single user Jupyter
Notebook server for each person in a group.

### Three subsystems
Three major subsystems run by the `jupyterhub` command line program:

- **Single-User Notebook Server**: a dedicated, single-user, Jupyter Notebook server is
  started for each user on the system when the user logs in. The object that
  starts these servers is called a **Spawner**.
- **Proxy**: the public facing part of JupyterHub that uses a dynamic proxy
  to route HTTP requests to the Hub and Single User Notebook Servers.
- **Hub**: manages user accounts, authentication, and coordinates Single User
  Notebook Servers using a Spawner.

![JupyterHub subsystems](images/jhub-parts.png)

### Deployment server

To use JupyterHub, you need a Unix server (typically Linux) running somewhere
that is accessible to your team on the network. The JupyterHub server can be
on an internal network at your organization, or it can run on the public
internet (in which case, take care with the Hub's
[security](#security)).

### Basic operation
Users access JupyterHub through a web browser, by going to the IP address or
the domain name of the server.

Basic principles of operation:

* Hub spawns proxy
* Proxy forwards all requests to hub by default
* Hub handles login, and spawns single-user servers on demand
* Hub configures proxy to forward url prefixes to single-user servers

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

### Default behavior

**IMPORTANT: You should not run JupyterHub without SSL encryption on a public network.**

See [Security documentation](#security) for how to configure JupyterHub to use SSL,
or put it behind SSL termination in another proxy server, such as nginx.

---

**Deprecation note:** Removed `--no-ssl` in version 0.7.

JupyterHub versions 0.5 and 0.6 require extra confirmation via `--no-ssl` to
allow running without SSL using the command `jupyterhub --no-ssl`. The
`--no-ssl` command line option is not needed anymore in version 0.7.

---

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
