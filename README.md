# JupyterHub: A multi-user server for Jupyter notebooks

This repo hosts the development of a multi-user server to manage and proxy multiple instances of the single-user <del>IPython</del> Jupyter notebook server.

Three actors:

- multi-user Hub (tornado process)
- configurable http proxy (node-http-proxy)
- multiple single-user IPython notebook servers (Python/IPython/tornado)

Basic principals:

- Hub spawns proxy
- Proxy forwards ~all requests to hub by default
- Hub handles login, and spawns single-user servers on demand
- Hub configures proxy to forward url prefixes to single-user servers


## dependencies

    # get the nodejs proxy (-g for global install)
    npm install [-g] jupyter/configurable-http-proxy
    
    # install the Python pargs (-e for editable/development install)
    pip install [-e] .
    
Note on debian/ubuntu machines, you may need to install the `nodejs-legacy` package
to get node executables to work:

    sudo apt-get install nodejs-legacy

This installs the traditional `node` executable, in addition to debian's renamed `nodejs`
executable, with which the apt-get installed `npm` doesn't actually work.


## to use

    $> jupyterhub

visit `http://localhost:8000`, and login with your unix credentials.

