# Proof of concept for configurable proxy

This is a proof of concept implementation of a configurable proxy for managed multi-user webapps,
ultimately for use in IPython.


Three actors:

- multi user server (tornado process)
- configurable http proxy (node-http-proxy)
- multiple single user servers (tornado)

Basic principals:

- MUS spawns proxy
- proxy forwards ~all requests to MUS by default
- MUS handles login, and spawns single-user servers on demand
- MUS configures proxy to forward url prefixes to single-user servers

## dependencies

    npm install node-http-proxy
    pip install tornado

## to use

    $> python -m multiuser_notebook

visit `http://localhost:8000`, and login (any username, password=`password`).

