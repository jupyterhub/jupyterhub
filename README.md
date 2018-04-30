**[Technical Overview](#technical-overview)** |
**[Installation](#installation)** |
**[Configuration](#configuration)** |
**[Docker](#docker)** |
**[Contributing](#contributing)** |
**[License](#license)** |
**[Help and Resources](#help-and-resources)**


# [JupyterHub](https://github.com/jupyterhub/jupyterhub)


[![PyPI](https://img.shields.io/pypi/v/jupyterhub.svg)](https://pypi.python.org/pypi/jupyterhub)
[![Documentation Status](https://readthedocs.org/projects/jupyterhub/badge/?version=latest)](http://jupyterhub.readthedocs.org/en/latest/?badge=latest)
[![Documentation Status](http://readthedocs.org/projects/jupyterhub/badge/?version=0.7.2)](http://jupyterhub.readthedocs.io/en/0.7.2/?badge=0.7.2)
[![Build Status](https://travis-ci.org/jupyterhub/jupyterhub.svg?branch=master)](https://travis-ci.org/jupyterhub/jupyterhub)
[![Circle CI](https://circleci.com/gh/jupyterhub/jupyterhub.svg?style=shield&circle-token=b5b65862eb2617b9a8d39e79340b0a6b816da8cc)](https://circleci.com/gh/jupyterhub/jupyterhub)
[![codecov.io](https://codecov.io/github/jupyterhub/jupyterhub/coverage.svg?branch=master)](https://codecov.io/github/jupyterhub/jupyterhub?branch=master)
[![Google Group](https://img.shields.io/badge/google-group-blue.svg)](https://groups.google.com/forum/#!forum/jupyter)

With [JupyterHub](https://jupyterhub.readthedocs.io) you can create a
**multi-user Hub** which spawns, manages, and proxies multiple instances of the
single-user [Jupyter notebook](https://jupyter-notebook.readthedocs.io)
server.

[Project Jupyter](https://jupyter.org) created JupyterHub to support many
users. The Hub can offer notebook servers to a class of students, a corporate
data science workgroup, a scientific research project, or a high performance
computing group.

## Technical overview

Three main actors make up JupyterHub:

- multi-user **Hub** (tornado process)
- configurable http **proxy** (node-http-proxy)
- multiple **single-user Jupyter notebook servers** (Python/Jupyter/tornado)

Basic principles for operation are:

- Hub launches a proxy.
- Proxy forwards all requests to Hub by default.
- Hub handles login, and spawns single-user servers on demand.
- Hub configures proxy to forward url prefixes to the single-user notebook
  servers.

JupyterHub also provides a
[REST API](http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyter/jupyterhub/master/docs/rest-api.yml#/default)
for administration of the Hub and its users.

## Installation

### Check prerequisites

A Linux/Unix based system with the following:

- [Python](https://www.python.org/downloads/) 3.4 or greater
- [nodejs/npm](https://www.npmjs.com/) Install a recent version of
  [nodejs/npm](https://docs.npmjs.com/getting-started/installing-node)
  For example, install it on Linux (Debian/Ubuntu) using:

      sudo apt-get install npm nodejs-legacy

  The `nodejs-legacy` package installs the `node` executable and is currently
  required for npm to work on Debian/Ubuntu.

- TLS certificate and key for HTTPS communication
- Domain name

### Install packages

JupyterHub can be installed with `pip`, and the proxy with `npm`:

```bash
npm install -g configurable-http-proxy
pip3 install jupyterhub    
```

If you plan to run notebook servers locally, you will need to install the
[Jupyter notebook](https://jupyter.readthedocs.io/en/latest/install.html)
package:

    pip3 install --upgrade notebook

### Run the Hub server

To start the Hub server, run the command:

    jupyterhub

Visit `https://localhost:8000` in your browser, and sign in with your unix
PAM credentials.

*Note*: To allow multiple users to sign into the server, you will need to
run the `jupyterhub` command as a *privileged user*, such as root.
The [wiki](https://github.com/jupyterhub/jupyterhub/wiki/Using-sudo-to-run-JupyterHub-without-root-privileges)
describes how to run the server as a *less privileged user*, which requires
more configuration of the system.

## Configuration

The [Getting Started](http://jupyterhub.readthedocs.io/en/latest/getting-started/index.html) section of the
documentation explains the common steps in setting up JupyterHub.

The [**JupyterHub tutorial**](https://github.com/jupyterhub/jupyterhub-tutorial)
provides an in-depth video and sample configurations of JupyterHub.

### Create a configuration file

To generate a default config file with settings and descriptions:

    jupyterhub --generate-config

### Start the Hub

To start the Hub on a specific url and port ``10.0.1.2:443`` with **https**:

    jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert

### Authenticators

| Authenticator                                                               | Description                                       |
| --------------------------------------------------------------------------- | ------------------------------------------------- |
| PAMAuthenticator                                                            | Default, built-in authenticator                   |
| [OAuthenticator](https://github.com/jupyterhub/oauthenticator)              | OAuth + JupyterHub Authenticator = OAuthenticator |
| [ldapauthenticator](https://github.com/jupyterhub/ldapauthenticator)        | Simple LDAP Authenticator Plugin for JupyterHub   |
| [kdcAuthenticator](https://github.com/bloomberg/jupyterhub-kdcauthenticator)| Kerberos Authenticator Plugin for JupyterHub      |

### Spawners

| Spawner                                                        | Description                                                                |
| -------------------------------------------------------------- | -------------------------------------------------------------------------- |
| LocalProcessSpawner                                            | Default, built-in spawner starts single-user servers as local processes    |
| [dockerspawner](https://github.com/jupyterhub/dockerspawner)   | Spawn single-user servers in Docker containers                             |
| [kubespawner](https://github.com/jupyterhub/kubespawner)       | Kubernetes spawner for JupyterHub                                          |
| [sudospawner](https://github.com/jupyterhub/sudospawner)       | Spawn single-user servers without being root                               |
| [systemdspawner](https://github.com/jupyterhub/systemdspawner) | Spawn single-user notebook servers using systemd                           |
| [batchspawner](https://github.com/jupyterhub/batchspawner)     | Designed for clusters using batch scheduling software                      |
| [wrapspawner](https://github.com/jupyterhub/wrapspawner)       | WrapSpawner and ProfilesSpawner enabling runtime configuration of spawners |

## Docker

A starter [**docker image for JupyterHub**](https://hub.docker.com/r/jupyterhub/jupyterhub/)
gives a baseline deployment of JupyterHub using Docker.

**Important:** This `jupyterhub/jupyterhub` image contains only the Hub itself,
with no configuration. In general, one needs to make a derivative image, with
at least a `jupyterhub_config.py` setting up an Authenticator and/or a Spawner.
To run the single-user servers, which may be on the same system as the Hub or
not, Jupyter Notebook version 4 or greater must be installed.

The JupyterHub docker image can be started with the following command:

    docker run -p 8000:8000 -d --name jupyterhub jupyterhub/jupyterhub jupyterhub

This command will create a container named `jupyterhub` that you can
**stop and resume** with `docker stop/start`.

The Hub service will be listening on all interfaces at port 8000, which makes
this a good choice for **testing JupyterHub on your desktop or laptop**.

If you want to run docker on a computer that has a public IP then you should
(as in MUST) **secure it with ssl** by adding ssl options to your docker
configuration or by using a ssl enabled proxy.

[Mounting volumes](https://docs.docker.com/engine/admin/volumes/volumes/) will
allow you to **store data outside the docker image (host system) so it will be persistent**, even when you start
a new image.

The command `docker exec -it jupyterhub bash` will spawn a root shell in your docker
container. You can **use the root shell to create system users in the container**.
These accounts will be used for authentication in JupyterHub's default configuration.

## Contributing

If you would like to contribute to the project, please read our
[contributor documentation](http://jupyter.readthedocs.io/en/latest/contributor/content-contributor.html)
and the [`CONTRIBUTING.md`](CONTRIBUTING.md). The `CONTRIBUTING.md` file
explains how to set up a development installation, how to run the test suite,
and how to contribute to documentation.

### A note about platform support

JupyterHub is supported on Linux/Unix based systems.

JupyterHub officially **does not** support Windows. You may be able to use
JupyterHub on Windows if you use a Spawner and Authenticator that work on
Windows, but the JupyterHub defaults will not. Bugs reported on Windows will not
be accepted, and the test suite will not run on Windows. Small patches that fix
minor Windows compatibility issues (such as basic installation) **may** be accepted,
however. For Windows-based systems, we would recommend running JupyterHub in a
docker container or Linux VM.

[Additional Reference:](http://www.tornadoweb.org/en/stable/#installation) Tornado's documentation on Windows platform support

## License

We use a shared copyright model that enables all contributors to maintain the
copyright on their contributions.

All code is licensed under the terms of the revised BSD license.

## Help and resources

We encourage you to ask questions on the [Jupyter mailing list](https://groups.google.com/forum/#!forum/jupyter).
To participate in development discussions or get help, talk with us on
our JupyterHub [Gitter](https://gitter.im/jupyterhub/jupyterhub) channel.

- [Reporting Issues](https://github.com/jupyterhub/jupyterhub/issues)
- [JupyterHub tutorial](https://github.com/jupyterhub/jupyterhub-tutorial)
- [Documentation for JupyterHub](http://jupyterhub.readthedocs.io/en/latest/) | [PDF (latest)](https://media.readthedocs.org/pdf/jupyterhub/latest/jupyterhub.pdf) | [PDF (stable)](https://media.readthedocs.org/pdf/jupyterhub/stable/jupyterhub.pdf)
- [Documentation for JupyterHub's REST API](http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyter/jupyterhub/master/docs/rest-api.yml#/default)
- [Documentation for Project Jupyter](http://jupyter.readthedocs.io/en/latest/index.html) | [PDF](https://media.readthedocs.org/pdf/jupyter/latest/jupyter.pdf)
- [Project Jupyter website](https://jupyter.org)

---

**[Technical Overview](#technical-overview)** |
**[Installation](#installation)** |
**[Configuration](#configuration)** |
**[Docker](#docker)** |
**[Contributing](#contributing)** |
**[License](#license)** |
**[Help and Resources](#help-and-resources)**
