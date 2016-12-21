**[Technical overview](#technical-overview)** |
**[Prerequisites](#prerequisites)** |
**[Installation](#installation)** |
**[Running the Hub Server](#running-the-hub-server)** |
**[Configuration](#configuration)** |
**[Docker](#docker)** |
**[Contributing](#contributing)** |
**[License](#license)** |
**[Getting help](#getting-help)**

# [JupyterHub](https://github.com/jupyterhub/jupyterhub)

[![Build Status](https://travis-ci.org/jupyterhub/jupyterhub.svg?branch=master)](https://travis-ci.org/jupyterhub/jupyterhub)
[![Circle CI](https://circleci.com/gh/jupyterhub/jupyterhub.svg?style=shield&circle-token=b5b65862eb2617b9a8d39e79340b0a6b816da8cc)](https://circleci.com/gh/jupyterhub/jupyterhub)
[![codecov.io](https://codecov.io/github/jupyterhub/jupyterhub/coverage.svg?branch=master)](https://codecov.io/github/jupyterhub/jupyterhub?branch=master)
"
[![Documentation Status](https://readthedocs.org/projects/jupyterhub/badge/?version=latest)](http://jupyterhub.readthedocs.org/en/latest/?badge=latest)
"
[![Google Group](https://img.shields.io/badge/-Google%20Group-lightgrey.svg)](https://groups.google.com/forum/#!forum/jupyter)

With [JupyterHub](https://jupyterhub.readthedocs.io) you can create a
**multi-user Hub** which spawns, manages, and proxies multiple instances of the
single-user [Jupyter notebook *(IPython notebook)* ](https://jupyter-notebook.readthedocs.io) server.

JupyterHub provides **single-user notebook servers to many users**. For example,
JupyterHub could serve notebooks to a class of students, a corporate
workgroup, or a science research group.

by [Project Jupyter](https://jupyter.org)

----

## Technical overview
Three main actors make up JupyterHub:

- multi-user **Hub** (tornado process)
- configurable http **proxy** (node-http-proxy)
- multiple **single-user Jupyter notebook servers** (Python/IPython/tornado)

JupyterHub's basic principles for operation are:

- Hub spawns a proxy
- Proxy forwards all requests to Hub by default
- Hub handles login, and spawns single-user servers on demand
- Hub configures proxy to forward url prefixes to the single-user servers

JupyterHub also provides a
[REST API](http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyter/jupyterhub/master/docs/rest-api.yml#/default)
for administration of the Hub and users.

----

## Prerequisites
Before installing JupyterHub, you need:

- [Python](https://www.python.org/downloads/) 3.3 or greater

  An understanding of using [`pip`](https://pip.pypa.io/en/stable/) for installing
  Python packages is recommended.

- [nodejs/npm](https://www.npmjs.com/)

  [Install nodejs/npm](https://docs.npmjs.com/getting-started/installing-node), which is available from your
  package manager. For example, install on Linux (Debian/Ubuntu) using:

      sudo apt-get install npm nodejs-legacy

  (The `nodejs-legacy` package installs the `node` executable and is currently
  required for npm to work on Debian/Ubuntu.)

- TLS certificate and key for HTTPS communication

- Domain name

Before running the single-user notebook servers (which may be on the same system as the Hub or not):

- [Jupyter Notebook](https://jupyter.readthedocs.io/en/latest/install.html) version 4 or greater

## Installation
JupyterHub can be installed with `pip`, and the proxy with `npm`:

```bash
npm install -g configurable-http-proxy
pip3 install jupyterhub    
```

If you plan to run notebook servers locally, you will need to install the
Jupyter notebook:

    pip3 install --upgrade notebook

## Running the Hub server
To start the Hub server, run the command:

    jupyterhub

Visit `https://localhost:8000` in your browser, and sign in with your unix credentials.

To allow multiple users to sign into the server, you will need to
run the `jupyterhub` command as a *privileged user*, such as root.
The [wiki](https://github.com/jupyterhub/jupyterhub/wiki/Using-sudo-to-run-JupyterHub-without-root-privileges)
describes how to run the server as a *less privileged user*, which requires more
configuration of the system.

----

## Configuration
The [getting started document](docs/source/getting-started.md) contains the
basics of configuring a JupyterHub deployment.

The JupyterHub **tutorial** provides a video and documentation that explains and illustrates the fundamental steps for installation and configuration. [Repo](https://github.com/jupyterhub/jupyterhub-tutorial)
| [Tutorial documentation](http://jupyterhub-tutorial.readthedocs.io/en/latest/)

#### Generate a default configuration file
Generate a default config file:

    jupyterhub --generate-config

#### Customize the configuration, authentication, and process spawning
Spawn the server on ``10.0.1.2:443`` with **https**:

    jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert

The authentication and process spawning mechanisms can be replaced,
which should allow plugging into a variety of authentication or process control environments.
Some examples, meant as illustration and testing of this concept:

- Using GitHub OAuth instead of PAM with [OAuthenticator](https://github.com/jupyterhub/oauthenticator)
- Spawning single-user servers with Docker, using the [DockerSpawner](https://github.com/jupyterhub/dockerspawner)

----

## Docker
A starter [docker image for JupyterHub](https://hub.docker.com/r/jupyterhub/jupyterhub/) gives a baseline deployment of JupyterHub.

**Important:** This `jupyterhub/jupyterhub` image contains only the Hub itself, with no configuration. In general, one needs
to make a derivative image, with at least a `jupyterhub_config.py` setting up an Authenticator and/or a Spawner. To run the
single-user servers, which may be on the same system as the Hub or not, Jupyter Notebook version 4 or greater must be installed.

#### Starting JupyterHub with docker
The JupyterHub docker image can be started with the following command:

    docker run -d --name jupyterhub jupyterhub/jupyterhub jupyterhub

This command will create a container named `jupyterhub` that you can **stop and resume** with `docker stop/start`.

The Hub service will be listening on all interfaces at port 8000, which makes this a good choice for **testing JupyterHub on your desktop or laptop**.

If you want to run docker on a computer that has a public IP then you should (as in MUST) **secure it with ssl** by
adding ssl options to your docker configuration or using a ssl enabled proxy.

[Mounting volumes](https://docs.docker.com/engine/userguide/containers/dockervolumes/) will
allow you to **store data outside the docker image (host system) so it will be persistent**, even when you start
a new image.

The command `docker exec -it jupyterhub bash` will spawn a root shell in your docker
container. You can **use the root shell to create system users in the container**. These accounts will be used for authentication
in JupyterHub's default configuration.

----

## Contributing
If you would like to contribute to the project, please read our [contributor documentation](http://jupyter.readthedocs.io/en/latest/contributor/content-contributor.html) and the [`CONTRIBUTING.md`](CONTRIBUTING.md).

For a **development install**, clone the [repository](https://github.com/jupyterhub/jupyterhub) and then install from source:

```bash
git clone https://github.com/jupyterhub/jupyterhub
cd jupyterhub
pip3 install -r dev-requirements.txt -e .
```

If the `pip3 install` command fails and complains about `lessc` being unavailable, you may need to explicitly install some additional JavaScript dependencies:

    npm install

This will fetch client-side JavaScript dependencies necessary to compile CSS.

You may also need to manually update JavaScript and CSS after some development updates, with:

```bash
python3 setup.py js    # fetch updated client-side js
python3 setup.py css   # recompile CSS from LESS sources
```

We use [pytest](http://doc.pytest.org/en/latest/) for testing. To run tests:

```bash
pytest jupyterhub/tests
```

----
## License
We use a shared copyright model that enables all contributors to maintain the
copyright on their contributions.

All code is licensed under the terms of the revised BSD license.

## Getting help
We encourage you to ask questions on the [mailing list](https://groups.google.com/forum/#!forum/jupyter),
and you may participate in development discussions or get live help on [Gitter](https://gitter.im/jupyterhub/jupyterhub).

## Resources
- [Reporting Issues](https://github.com/jupyterhub/jupyterhub/issues)
- JupyterHub tutorial | [Repo](https://github.com/jupyterhub/jupyterhub-tutorial)
  | [Tutorial documentation](http://jupyterhub-tutorial.readthedocs.io/en/latest/)
- [Documentation for JupyterHub](http://jupyterhub.readthedocs.io/en/latest/) | [PDF (latest)](https://media.readthedocs.org/pdf/jupyterhub/latest/jupyterhub.pdf) | [PDF (stable)](https://media.readthedocs.org/pdf/jupyterhub/stable/jupyterhub.pdf)
- [Documentation for JupyterHub's REST API](http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyter/jupyterhub/master/docs/rest-api.yml#/default)
- [Documentation for Project Jupyter](http://jupyter.readthedocs.io/en/latest/index.html) | [PDF](https://media.readthedocs.org/pdf/jupyter/latest/jupyter.pdf)
- [Project Jupyter website](https://jupyter.org)
