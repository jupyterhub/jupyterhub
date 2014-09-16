# JupyterHub: A multi-user server for Jupyter notebooks

This repo hosts the development of a multi-user server to manage and proxy multiple instances of the single-user <del>IPython</del> Jupyter notebook server.

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

First install the configurable HTTP proxy package (-g for global install):

    npm install [-g] jupyter/configurable-http-proxy

Next install `bower` to fetch the JavaScript dependencies and `less` to compile CSS:

    npm install -g bower less

Note on debian/ubuntu machines, you may need to install the `nodejs-legacy` package
to get node executables to work:

    sudo apt-get install nodejs-legacy

This installs the traditional `node` executable, in addition to debian's renamed `nodejs`
executable, with which the apt-get installed `npm` doesn't actually work.

## Installation

Then you can install the Python package by doing:

    pip install .
    
This will fetch Javascript dependencies and compile CSS, and install these files to `sys.prefix`/share/jupyter.


### Development install

For a development install:

    pip install -e .

In which case you may need to manually update javascript and css after some updates, with:

    python setup.py bower # fetch updated js (changes rarely)
    python setup.py css   # recompile CSS from LESS sources


## Running the server

To start the server, run the command:

    jupyterhub

and then visit `http://localhost:8000`, and sign in with your unix credentials.

If you want multiple users to be able to sign into the server, you will need to run the
`jupyterhub` command as a privileged user, such as root.

### Some examples

generate a default config file:

    jupyterhub --generate-config

spawn the server on 10.0.1.2:443 with https:

    jupyterhub --ip 10.0.1.2 --port 443 --ssl-key my_ssl.key --ssl-cert my_ssl.cert

