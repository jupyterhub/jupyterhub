# Configuration Basics

The [getting started document](docs/source/getting-started.md) contains
general information about configuring a JupyterHub deployment and the
[configuration reference](docs/source/configuration-guide.md) provides more
comprehensive detail.

## JupyterHub configuration

Configuration parameters may be set by:
- a configuration file `jupyterhub_config.py`, or
- as options from the command line.

### Generate a default config file

On startup, JupyterHub will look by default for a configuration file named
`jupyterhub_config.py` in the current working directory.

To generate a default config file `jupyterhub_config.py`:

```bash
jupyterhub --generate-config
```

This default `jupyterhub_config.py` file contains comments and guidance for all
configuration variables and their default values.

### Configure using command line options

To display all command line options that are available for configuration:

    jupyterhub --help-all

Configuration using the command line options is done when launching JupyterHub.
For example, to start JupyterHub on ``10.0.1.2:443`` with **https**, you
would enter:

    jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert

All configurable options are technically configurable on the command-line,
even if some are really inconvenient to type. Just replace the desired option,
`c.Class.trait`, with `--Class.trait`. For example, to configure the
`c.Spawner.notebook_dir` trait from the command-line, use the
`--Spawner.notebook_dir` option:

```bash
jupyterhub --Spawner.notebook_dir='~/assignments'
```

### Load a specific config file

You can load a specific config file with:

```bash
jupyterhub -f /path/to/jupyterhub_config.py
```

See also: [general docs](http://ipython.org/ipython-doc/dev/development/config.html)
on the config system Jupyter uses.

### Configuration for different deployment environments

The default authentication and process spawning mechanisms can be replaced,
which allows plugging into a variety of authentication methods or process
control and deployment environments. Some examples, meant as illustration and
testing of this concept, are:

- Using GitHub OAuth instead of PAM with [OAuthenticator](https://github.com/jupyterhub/oauthenticator)
- Spawning single-user servers with Docker, using the [DockerSpawner](https://github.com/jupyterhub/dockerspawner)
