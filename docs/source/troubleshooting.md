# Troubleshooting

This document is under active development.

When troubleshooting, you may see unexpected behaviors or receive an error
message. These two lists provide links to identifying the cause of the
problem and how to resolve it.

## Behavior problems
- JupyterHub proxy fails to start

## Errors
- 500 error after spawning a single-user server

----

## If JupyterHub proxy fails to start:

- check if the JupyterHub IP configuration setting is
  ``c.JupyterHub.ip = '*'``; if it is, try ``c.JupyterHub.ip = ''``
- Try starting with ``jupyterhub --ip=0.0.0.0``

----

## I am receiving a 500 error after spawning my single-user server (on the
URL `/user/you/...`).

This is often because your single-user server cannot check your cookies with
the Hub.

There are two likely reasons for this:

1. The single-user server cannot connect to the Hub's API (networking
   configuration problems)
2. The single-user server cannot *authenticate* its requests (invalid token)

### Symptoms:

The main symptom is a failure to load *any* page served by the single-user
server, met with a 500 error. This is typically the first page at `/user/you`
after logging in or clicking "Start my server". When a single-user server
receives a request, it makes an API request to the Hub to check if the cookie
corresponds to the right user. This request is logged.

If everything is working, it will look like this:

```
200 GET /hub/api/authorizations/cookie/jupyter-hub-token-name/[secret] (@10.0.1.4) 6.10ms
```

You should see a similar 200 message, as above, in the Hub log when you first
visit your single-user server. If you don't see this message in the log, it
may mean that your single-user server isn't connecting to your Hub.

If you see 403 (forbidden) like this, it's a token problem:

```
403 GET /hub/api/authorizations/cookie/jupyter-hub-token-name/[secret] (@10.0.1.4) 4.14ms
```

Check the logs of the single-user server, which may have more detailed
information on the cause.

### Causes and resolutions:

#### No authorization request

If you make an API request and it is not received by the server, you likely
have a network configuration issue. Often, this happens when the Hub is only
listening on 127.0.0.1 (default) and the single-user servers are not on the
same 'machine' (can be physically remote, or in a docker container or VM). The
fix for this case is to make sure that `c.JupyterHub.hub_ip` is an address
that all single-user servers can connect to, e.g.:

```python
c.JupyterHub.hub_ip = '10.0.0.1'
```

#### 403 GET /hub/api/authorizations/cookie

If you receive a 403 error, the API token for the single-user server is likely
invalid. Commonly, the 403 error is caused by resetting the JupyterHub
database (either removing jupyterhub.sqlite or some other action) while
leaving single-user servers running. This happens most frequently when using
DockerSpawner, because Docker's default behavior is to stop/start containers
which resets the JupyterHub database, rather than destroying and recreating
the container every time. This means that the same API token is used by the
server for its whole life, until the container is rebuilt.

The fix for this Docker case is to remove any Docker containers seeing this
issue (typicaly all containers created before a certain point in time):

    docker rm -f jupyter-name

After this, when you start your server via JupyterHub, it will build a
new container. If this was the underlying cause of the issue, you should see
your server again.
