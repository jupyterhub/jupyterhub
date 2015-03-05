# JupyterHub: A multi-user server for Jupyter notebooks

JupyterHub is a multi-user server that manages and proxies multiple instances of the single-user <del>IPython</del> Jupyter notebook server.

Three actors:

- multi-user Hub (tornado process)
- configurable http proxy (node-http-proxy)
- multiple single-user IPython notebook servers (Python/IPython/tornado)

Basic principles:

- Hub spawns proxy
- Proxy forwards ~all requests to hub by default
- Hub handles login, and spawns single-user servers on demand
- Hub configures proxy to forward url prefixes to single-user servers


## Dependencies

JupyterHub requires IPython >= 3.0 (current master) and Python >= 3.3.

You will need nodejs/npm, which you can get from your package manager:

    sudo apt-get install npm nodejs-legacy

(The `nodejs-legacy` package installs the `node` executable,
which is required for npm to work on Debian/Ubuntu at this point)

Then install javascript dependencies:

    sudo npm install -g configurable-http-proxy


## Installation

Then you can install the Python package by doing:

    pip install -r requirements.txt
    pip install .

This will fetch client-side javascript dependencies and compile CSS,
and install these files to `sys.prefix`/share/jupyter, as well as
install any Python dependencies.


### Development install

For a development install:

    pip install -r dev-requirements.txt
    pip install -e .

In which case you may need to manually update javascript and css after some updates, with:

    python setup.py js    # fetch updated client-side js (changes rarely)
    python setup.py css   # recompile CSS from LESS sources


## Running the server

To start the server, run the command:

    jupyterhub

and then visit `http://localhost:8000`, and sign in with your unix credentials.

If you want multiple users to be able to sign into the server, you will need to run the
`jupyterhub` command as a privileged user, such as root.
The [wiki](https://github.com/jupyter/jupyterhub/wiki/Using-sudo-to-run-JupyterHub-without-root-privileges) describes how to run the server
as a less privileged user, which requires more configuration of the system.

### Some examples

generate a default config file:

    jupyterhub --generate-config

spawn the server on 10.0.1.2:443 with https:

    jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert

The authentication and process spawning mechanisms can be replaced,
which should allow plugging into a variety of authentication or process control environments.
Some examples, meant as illustration and testing of this concept:

- Using GitHub OAuth instead of PAM with [OAuthenticator](https://github.com/jupyter/oauthenticator)
- Spawning single-user servers with docker, using the [DockerSpawner](https://github.com/jupyter/dockerspawner)
