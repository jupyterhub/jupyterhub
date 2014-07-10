# Multi-user server for Jupyter notebooks

This repo hosts the development of a multi-user server to manage and proxy multiple instances of the single-user IPython notebook server.

Three actors:

- multi-user server (tornado process)
- configurable http proxy (node-http-proxy)
- multiple single-user IPython notbeook servers (Python/IPython/tornado)

Basic principals:

- MUS spawns proxy
- proxy forwards ~all requests to MUS by default
- MUS handles login, and spawns single-user servers on demand
- MUS configures proxy to forward url prefixes to single-user servers

## dependencies

    npm install
    pip install -r requirements.txt

## to use

    $> python -m multiuser

visit `http://localhost:8000`, and login (any username, password=`password`).

