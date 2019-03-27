# Configuration Basics

The section contains basic information about configuring settings for a JupyterHub
deployment. The [Technical Reference](../reference/index)
documentation provides additional details.

This section will help you learn how to:

- generate a default configuration file, `jupyterhub_config.py`
- start with a specific configuration file
- configure JupyterHub using command line options
- find information and examples for some common deployments

## Generate a default config file

On startup, JupyterHub will look by default for a configuration file,
`jupyterhub_config.py`, in the current working directory.

To generate a default config file, `jupyterhub_config.py`:

```bash
jupyterhub --generate-config
```

This default `jupyterhub_config.py` file contains comments and guidance for all
configuration variables and their default values. We recommend storing
configuration files in the standard UNIX filesystem location, i.e.
`/etc/jupyterhub`.

## Start with a specific config file

You can load a specific config file and start JupyterHub using:

```bash
jupyterhub -f /path/to/jupyterhub_config.py
```

If you have stored your configuration file in the recommended UNIX filesystem
location, `/etc/jupyterhub`, the following command will start JupyterHub using
the configuration file:

```bash
jupyterhub -f /etc/jupyterhub/jupyterhub_config.py
```

The IPython documentation provides additional information on the
[config system](http://ipython.readthedocs.io/en/stable/development/config)
that Jupyter uses.

## Configure using command line options

To display all command line options that are available for configuration:

```bash
    jupyterhub --help-all
```

Configuration using the command line options is done when launching JupyterHub.
For example, to start JupyterHub on ``10.0.1.2:443`` with https, you
would enter:

```bash
    jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert
```

All configurable options may technically be set on the command-line,
though some are inconvenient to type. To set a particular configuration
parameter, `c.Class.trait`, you would use the command line option,
`--Class.trait`, when starting JupyterHub. For example, to configure the
`c.Spawner.notebook_dir` trait from the command-line, use the
`--Spawner.notebook_dir` option:

```bash
jupyterhub --Spawner.notebook_dir='~/assignments'
```

## Configure for various deployment environments

The default authentication and process spawning mechanisms can be replaced, and
specific [authenticators](./authenticators-users-basics) and
[spawners](./spawners-basics) can be set in the configuration file.
This enables JupyterHub to be used with a variety of authentication methods or
process control and deployment environments. [Some examples](../reference/config-examples),
meant as illustration, are:

- Using GitHub OAuth instead of PAM with [OAuthenticator](https://github.com/jupyterhub/oauthenticator)
- Spawning single-user servers with Docker, using the [DockerSpawner](https://github.com/jupyterhub/dockerspawner)

## Run the proxy separately

This is *not* strictly necessary, but useful in many cases.  If you
use a custom proxy (e.g. Traefik), this also not needed.

Connections to user servers go through the proxy, and *not* the hub
itself.  If the proxy stays running when the hub restarts (for
maintenance, re-configuration, etc.), then use connections are not
interrupted.  For simplicity, by default the hub starts the proxy
automatically, so if the hub restarts, the proxy restarts, and user
connections are interrupted.  It is easy to run the proxy separately,
for information see [the separate proxy page](../reference/separate-proxy).
