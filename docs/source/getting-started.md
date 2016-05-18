# Getting started with JupyterHub

This document describes some of the basics of configuring JupyterHub to do what you want.
JupyterHub is highly customizable, so there's a lot to cover.


## Installation

See [the readme](https://github.com/jupyter/jupyterhub/blob/master/README.md) for help installing JupyterHub.


## Overview

JupyterHub is a set of processes that together provide a multiuser Jupyter Notebook server.
There are three main categories of processes run by the `jupyterhub` command line program:

- **Single User Server**: a dedicated, single-user, Jupyter Notebook is started for each user on the system
  when they log in. The object that starts these processes is called a Spawner.
- **Proxy**: the public facing part of the server that uses a dynamic proxy to route HTTP requests
  to the Hub and Single User Servers.
- **Hub**: manages user accounts and authentication and coordinates Single Users Servers using a Spawner.

## JupyterHub's default behavior

**IMPORTANT:** In its default configuration, JupyterHub requires SSL encryption (HTTPS) to run.
**You should not run JupyterHub without SSL encryption on a public network.**
See [Security documentation](#Security) for how to configure JupyterHub to use SSL, and in
certain cases, e.g. behind SSL termination in nginx, allowing the hub to run with no SSL
by requiring `--no-ssl` (as of [version 0.5](./changelog.html)).

To start JupyterHub in its default configuration, type the following at the command line:

    sudo jupyterhub

The default Authenticator that ships with JupyterHub authenticates users
with their system name and password (via [PAM][]).
Any user on the system with a password will be allowed to start a single-user notebook server.

The default Spawner starts servers locally as each user, one dedicated server per user.
These servers listen on localhost, and start in the given user's home directory.

By default, the **Proxy** listens on all public interfaces on port 8000.
Thus you can reach JupyterHub through either:

    http://localhost:8000

or any other public IP or domain pointing to your system.

In their default configuration, the other services, the **Hub** and **Single-User Servers**,
all communicate with each other on localhost only.

By default, starting JupyterHub will write two files to disk in the current working directory:

- `jupyterhub.sqlite` is the sqlite database containing all of the state of the **Hub**.
  This file allows the **Hub** to remember what users are running and where,
  as well as other information enabling you to restart parts of JupyterHub separately.
- `jupyterhub_cookie_secret` is the encryption key used for securing cookies.
  This file needs to persist in order for restarting the Hub server to avoid invalidating cookies.
  Conversely, deleting this file and restarting the server effectively invalidates all login cookies.
  The cookie secret file is discussed in the [Cookie Secret documentation](#Cookie secret).

The location of these files can be specified via configuration, discussed below.


## How to configure JupyterHub

JupyterHub is configured in two ways:

1. Configuration file
2. Command-line arguments

### Configuration file
By default, JupyterHub will look for a configuration file (which may not be created yet)
named `jupyterhub_config.py` in the current working directory.
You can create an empty configuration file with:

    jupyterhub --generate-config

This empty configuration file has descriptions of all configuration variables and their default
values. You can load a specific config file with:

    jupyterhub -f /path/to/jupyterhub_config.py

See also: [general docs](http://ipython.org/ipython-doc/dev/development/config.html)
on the config system Jupyter uses.

### Command-line arguments
Type the following for brief information about the command-line arguments:

    jupyterhub -h

or:

    jupyterhub --help-all

for the full command line help.

All configurable options are technically configurable on the command-line,
even if some are really inconvenient to type. Just replace the desired option,
c.Class.trait, with --Class.trait. For example, to configure
c.Spawner.notebook_dir = '~/assignments' from the command-line:

    jupyterhub --Spawner.notebook_dir='~/assignments'

## Networking

### Configuring the Proxy's IP address and port
The Proxy's main IP address setting determines where JupyterHub is available to users.
By default, JupyterHub is configured to be available on all network interfaces
(`''`) on port 8000. **Note**: Use of `'*'` is discouraged for IP configuration;
instead, use of `'0.0.0.0'` is preferred.

Changing the IP address and port can be done with the following command line
arguments:

    jupyterhub --ip=192.168.1.2 --port=443

Or by placing the following lines in a configuration file:

```python
c.JupyterHub.ip = '192.168.1.2'
c.JupyterHub.port = 443
```

Port 443 is used as an example since 443 is the default port for SSL/HTTPS.

Configuring only the main IP and port of JupyterHub should be sufficient for most deployments of JupyterHub.
However, more customized scenarios may need additional networking details to
be configured.

### Configuring the Proxy's REST API communication IP address and port (optional)
The Hub service talks to the proxy via a REST API on a secondary port,
whose network interface and port can be configured separately.
By default, this REST API listens on port 8081 of localhost only.

If running the Proxy separate from the Hub,
configure the REST API communication IP address and port with:

```python
# ideally a private network address
c.JupyterHub.proxy_api_ip = '10.0.1.4'
c.JupyterHub.proxy_api_port = 5432
```

### Configuring the Hub if Spawners or Proxy are remote or isolated in containers
The Hub service also listens only on localhost (port 8080) by default.
The Hub needs needs to be accessible from both the proxy and all Spawners.
When spawning local servers, an IP address setting of localhost is fine.
If *either* the Proxy *or* (more likely) the Spawners will be remote or
isolated in containers, the Hub must listen on an IP that is accessible.

```python
c.JupyterHub.hub_ip = '10.0.1.4'
c.JupyterHub.hub_port = 54321
```

## Security

**IMPORTANT:** In its default configuration, JupyterHub requires SSL encryption (HTTPS) to run.
**You should not run JupyterHub without SSL encryption on a public network.**

Security is the most important aspect of configuring Jupyter. There are three main aspects of the
security configuration:

1. SSL encryption (to enable HTTPS)
2. Cookie secret (a key for encrypting browser cookies)
3. Proxy authentication token (used for the Hub and other services to authenticate to the Proxy)

## SSL encryption

Since JupyterHub includes authentication and allows arbitrary code execution, you should not run
it without SSL (HTTPS). This will require you to obtain an official, trusted SSL certificate or
create a self-signed certificate. Once you have obtained and installed a key and certificate you
need to specify their locations in the configuration file as follows:

```python
c.JupyterHub.ssl_key = '/path/to/my.key'
c.JupyterHub.ssl_cert = '/path/to/my.cert'
```

It is also possible to use letsencrypt (https://letsencrypt.org/) to obtain a free, trusted SSL
certificate. If you run letsencrypt using the default options, the needed configuration is (replace `your.domain.com` by your fully qualified domain name):

```python
c.JupyterHub.ssl_key = '/etc/letsencrypt/live/your.domain.com/privkey.pem'
c.JupyterHub.ssl_cert = '/etc/letsencrypt/live/your.domain.com/fullchain.pem'
```

Some cert files also contain the key, in which case only the cert is needed. It is important that
these files be put in a secure location on your server, where they are not readable by regular
users.

Note on **chain certificates**: If you are using a chain certificate, see also
[chained certificate for SSL](troubleshooting.md#chained-certificates-for-ssl) in the JupyterHub troubleshooting FAQ).

Note: In certain cases, e.g. **behind SSL termination in nginx**, allowing no SSL
running on the hub may be desired. To run the Hub without SSL, you must opt
in by configuring and confirming the `--no-ssl` option, added as of [version 0.5](./changelog.html).

## Cookie secret

The cookie secret is an encryption key, used to encrypt the browser cookies used for
authentication. If this value changes for the Hub, all single-user servers must also be restarted.
Normally, this value is stored in a file, the location of which can be specified in a config file
as follows:

```python
c.JupyterHub.cookie_secret_file = '/srv/jupyterhub/cookie_secret'
```

The content of this file should be a long random string encoded in MIME Base64. An example would be to generate this file as:

```bash
openssl rand -base64 2048 > /srv/jupyterhub/cookie_secret
```

In most deployments of JupyterHub, you should point this to a secure location on the file
system, such as `/srv/jupyterhub/cookie_secret`. If the cookie secret file doesn't exist when
the Hub starts, a new cookie secret is generated and stored in the file. The
file must not be readable by group or other or the server won't start.
The recommended permissions for the cookie secret file are 600 (owner-only rw).


If you would like to avoid the need for files, the value can be loaded in the Hub process from
the `JPY_COOKIE_SECRET` environment variable, which is a hex-encoded string. You
can set it this way:

```bash
export JPY_COOKIE_SECRET=`openssl rand -hex 1024`
```

For security reasons, this environment variable should only be visible to the Hub.
If you set it dynamically as above, all users will be logged out each time the
Hub starts.

You can also set the secret in the configuration file itself as a binary string:

```python
c.JupyterHub.cookie_secret = bytes.fromhex('VERY LONG SECRET HEX STRING')
```

## Proxy authentication token

The Hub authenticates its requests to the Proxy using a secret token that the Hub and Proxy agree upon. The value of this string should be a random string (for example, generated by `openssl rand -hex 32`). You can pass this value to the Hub and Proxy using either the `CONFIGPROXY_AUTH_TOKEN` environment variable:

```bash
export CONFIGPROXY_AUTH_TOKEN=`openssl rand -hex 32`
```

This environment variable needs to be visible to the Hub and Proxy.

Or you can set the value in the configuration file:

```python
c.JupyterHub.proxy_auth_token = '0bc02bede919e99a26de1e2a7a5aadfaf6228de836ec39a05a6c6942831d8fe5'
```

If you don't set the Proxy authentication token, the Hub will generate a random key itself, which
means that any time you restart the Hub you **must also restart the Proxy**. If the proxy is a
subprocess of the Hub, this should happen automatically (this is the default configuration).

Another time you must set the Proxy authentication token yourself is if you want other services, such as [nbgrader](https://github.com/jupyter/nbgrader) to also be able to connect to the Proxy.

## Configuring authentication

The default Authenticator uses [PAM][] to authenticate system users with their username and password.
The default behavior of this Authenticator is to allow any user with an account and password on the system to login.
You can restrict which users are allowed to login with `Authenticator.whitelist`:


```python
c.Authenticator.whitelist = {'mal', 'zoe', 'inara', 'kaylee'}
```

Admin users of JupyterHub have the ability to take actions on users' behalf,
such as stopping and restarting their servers,
and adding and removing new users from the whitelist.
Any users in the admin list are automatically added to the whitelist,
if they are not already present.
The set of initial Admin users can configured as follows:

```python
c.Authenticator.admin_users = {'mal', 'zoe'}
```

If `JupyterHub.admin_access` is True (not default),
then admin users have permission to log in *as other users* on their respective machines, for debugging.
**You should make sure your users know if admin_access is enabled.**

### Adding and removing users

Users can be added and removed to the Hub via the admin panel or REST API. These users will be
added to the whitelist and database. Restarting the Hub will not require manually updating the
whitelist in your config file, as the users will be loaded from the database. This means that
after starting the Hub once, it is not sufficient to remove users from the whitelist in your
config file. You must also remove them from the database, either by discarding the database file,
or via the admin UI.

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

## Configuring single-user servers

Since the single-user server is an instance of `jupyter notebook`, an entire separate
multi-process application, there are many aspect of that server can configure, and a lot of ways
to express that configuration.

At the JupyterHub level, you can set some values on the Spawner. The simplest of these is
`Spawner.notebook_dir`, which lets you set the root directory for a user's server. This root
notebook directory is the highest level directory users will be able to access in the notebook
dashboard. In this example, the root notebook directory is set to `~/notebooks`, where `~` is
expanded to the user's home directory.

```python
c.Spawner.notebook_dir = '~/notebooks'
```

You can also specify extra command-line arguments to the notebook server with:

```python
c.Spawner.args = ['--debug', '--profile=PHYS131']
```

This could be used to set the users default page for the single user server:

```python
c.Spawner.args = ['--NotebookApp.default_url=/notebooks/Welcome.ipynb']
```

Since the single-user server extends the notebook server application,
it still loads configuration from the `ipython_notebook_config.py` config file.
Each user may have one of these files in `$HOME/.ipython/profile_default/`.
IPython also supports loading system-wide config files from `/etc/ipython/`,
which is the place to put configuration that you want to affect all of your users.

## External services

JupyterHub has a REST API that can be used by external services like the
[cull_idle_servers](https://github.com/jupyterhub/jupyterhub/blob/master/examples/cull-idle/cull_idle_servers.py)
script which monitors and kills idle single-user servers periodically. In order to run such an
external service, you need to provide it an API token. In the case of `cull_idle_servers`, it is passed
as the environment variable called `JPY_API_TOKEN`.

Currently there are two ways of registering that token with JupyterHub. The first one is to use
the `jupyterhub` command to generate a token for a specific hub user:

```
$ jupyterhub token <username>
```

As of [version 0.6.0](./changelog.html), the preferred way of doing this is to first generate an API token:

```
$ openssl rand -hex 32
```


and then write it to your JupyterHub configuration file (note that the **key** is the token while the **value** is the username):

```
c.JupyterHub.api_tokens = {'token' : 'username'}
```

Upon restarting JupyterHub, you should see a message like below in the logs:

```
Adding API token for <username>
```

Now you can run your script, i.e. `cull_idle_servers`, by providing it the API token and it will authenticate through
the REST API to interact with it.

## File locations

It is recommended to put all of the files used by JupyterHub into standard UNIX filesystem locations.

* `/srv/jupyterhub` for all security and runtime files
* `/etc/jupyterhub` for all configuration files
* `/var/log` for log files

## Example

In the following example, we show a configuration files for a fairly standard JupyterHub deployment with the following assumptions:

* JupyterHub is running on a single cloud server
* Using SSL on the standard HTTPS port 443
* You want to use [GitHub OAuth][oauthenticator] for login
* You need the users to exist locally on the server
* You want users' notebooks to be served from `~/assignments` to allow users to browse for notebooks within
  other users home directories
* You want the landing page for each user to be a Welcome.ipynb notebook in their assignments directory.
* All runtime files are put into `/srv/jupyterhub` and log files in `/var/log`.

Let's start out with `jupyterhub_config.py`:

```python
# jupyterhub_config.py
c = get_config()

import os
pjoin = os.path.join

runtime_dir = os.path.join('/srv/jupyterhub')
ssl_dir = pjoin(runtime_dir, 'ssl')
if not os.path.exists(ssl_dir):
    os.makedirs(ssl_dir)


# https on :443
c.JupyterHub.port = 443
c.JupyterHub.ssl_key = pjoin(ssl_dir, 'ssl.key')
c.JupyterHub.ssl_cert = pjoin(ssl_dir, 'ssl.cert')

# put the JupyterHub cookie secret and state db
# in /var/run/jupyterhub
c.JupyterHub.cookie_secret_file = pjoin(runtime_dir, 'cookie_secret')
c.JupyterHub.db_url = pjoin(runtime_dir, 'jupyterhub.sqlite')
# or `--db=/path/to/jupyterhub.sqlite` on the command-line

# put the log file in /var/log
c.JupyterHub.log_file = '/var/log/jupyterhub.log'

# use GitHub OAuthenticator for local users

c.JupyterHub.authenticator_class = 'oauthenticator.LocalGitHubOAuthenticator'
c.GitHubOAuthenticator.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
# create system users that don't exist yet
c.LocalAuthenticator.create_system_users = True

# specify users and admin
c.Authenticator.whitelist = {'rgbkrk', 'minrk', 'jhamrick'}
c.Authenticator.admin_users = {'jhamrick', 'rgbkrk'}

# start single-user notebook servers in ~/assignments,
# with ~/assignments/Welcome.ipynb as the default landing page
# this config could also be put in
# /etc/ipython/ipython_notebook_config.py
c.Spawner.notebook_dir = '~/assignments'
c.Spawner.args = ['--NotebookApp.default_url=/notebooks/Welcome.ipynb']
```

Using the GitHub Authenticator [requires a few additional env variables][oauth-setup],
which we will need to set when we launch the server:

```bash
export GITHUB_CLIENT_ID=github_id
export GITHUB_CLIENT_SECRET=github_secret
export OAUTH_CALLBACK_URL=https://example.com/hub/oauth_callback
export CONFIGPROXY_AUTH_TOKEN=super-secret
jupyterhub -f /path/to/aboveconfig.py
```

# Further reading

- [Custom Authenticators](./authenticators.html)
- [Custom Spawners](./spawners.html)
- [Troubleshooting](./troubleshooting.html)


[oauth-setup]: https://github.com/jupyter/oauthenticator#setup
[oauthenticator]: https://github.com/jupyter/oauthenticator
[PAM]: https://en.wikipedia.org/wiki/Pluggable_authentication_module
