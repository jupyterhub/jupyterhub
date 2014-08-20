# Multi-user server for Jupyter notebooks

This repo hosts the development of a multi-user server to manage and proxy multiple instances of the single-user IPython notebook server.

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

    npm install
    pip install -r requirements.txt

## to use

    $> python -m multiuser

visit `http://localhost:8000`, and login (any username, password=`password`).

