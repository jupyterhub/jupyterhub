# Configuration Basics

The [getting started document](docs/source/getting-started.md) contains
detailed information abouts configuring a JupyterHub deployment.

The JupyterHub **tutorial** provides a video and documentation that explains
and illustrates the fundamental steps for installation and configuration.
[Repo](https://github.com/jupyterhub/jupyterhub-tutorial)
| [Tutorial documentation](http://jupyterhub-tutorial.readthedocs.io/en/latest/)

## Generate a default configuration file

Generate a default config file:

    jupyterhub --generate-config

## Customize the configuration, authentication, and process spawning

Spawn the server on ``10.0.1.2:443`` with **https**:

    jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert

The authentication and process spawning mechanisms can be replaced,
which should allow plugging into a variety of authentication or process
control environments. Some examples, meant as illustration and testing of this
concept, are:

- Using GitHub OAuth instead of PAM with [OAuthenticator](https://github.com/jupyterhub/oauthenticator)
- Spawning single-user servers with Docker, using the [DockerSpawner](https://github.com/jupyterhub/dockerspawner)
