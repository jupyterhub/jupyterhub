# Troubleshooting

When troubleshooting, you may see unexpected behaviors or receive an error
message. This section provide links for identifying the cause of the
problem and how to resolve it.


## Behavior

### JupyterHub proxy fails to start

If you have tried to start the JupyterHub proxy and it fails to start:

- check if the JupyterHub IP configuration setting is
  ``c.JupyterHub.ip = '*'``; if it is, try ``c.JupyterHub.ip = ''``
- Try starting with ``jupyterhub --ip=0.0.0.0``


## Errors

### 500 error after spawning my single-user server

You receive a 500 error when accessing the URL `/user/<your_name>/...`.
This is often seen when your single-user server cannot verify your user cookie
with the Hub.

There are two likely reasons for this:

1. The single-user server cannot connect to the Hub's API (networking
   configuration problems)
2. The single-user server cannot *authenticate* its requests (invalid token)

#### Symptoms

The main symptom is a failure to load *any* page served by the single-user
server, met with a 500 error. This is typically the first page at `/user/<your_name>`
after logging in or clicking "Start my server". When a single-user notebook server
receives a request, the notebook server makes an API request to the Hub to 
check if the cookie corresponds to the right user. This request is logged.

If everything is working, the response logged will be similar to this:

```
200 GET /hub/api/authorizations/cookie/jupyter-hub-token-name/[secret] (@10.0.1.4) 6.10ms
```

You should see a similar 200 message, as above, in the Hub log when you first
visit your single-user notebook server. If you don't see this message in the log, it
may mean that your single-user notebook server isn't connecting to your Hub.

If you see 403 (forbidden) like this, it's a token problem:

```
403 GET /hub/api/authorizations/cookie/jupyter-hub-token-name/[secret] (@10.0.1.4) 4.14ms
```

Check the logs of the single-user notebook server, which may have more detailed
information on the cause.

#### Causes and resolutions

##### No authorization request

If you make an API request and it is not received by the server, you likely
have a network configuration issue. Often, this happens when the Hub is only
listening on 127.0.0.1 (default) and the single-user servers are not on the
same 'machine' (can be physically remote, or in a docker container or VM). The
fix for this case is to make sure that `c.JupyterHub.hub_ip` is an address
that all single-user servers can connect to, e.g.:

```python
c.JupyterHub.hub_ip = '10.0.0.1'
```

##### 403 GET /hub/api/authorizations/cookie

If you receive a 403 error, the API token for the single-user server is likely
invalid. Commonly, the 403 error is caused by resetting the JupyterHub
database (either removing jupyterhub.sqlite or some other action) while
leaving single-user servers running. This happens most frequently when using
DockerSpawner, because Docker's default behavior is to stop/start containers
which resets the JupyterHub database, rather than destroying and recreating
the container every time. This means that the same API token is used by the
server for its whole life, until the container is rebuilt.

The fix for this Docker case is to remove any Docker containers seeing this
issue (typically all containers created before a certain point in time):

    docker rm -f jupyter-name

After this, when you start your server via JupyterHub, it will build a
new container. If this was the underlying cause of the issue, you should see
your server again.


## How do I...?

### Use a chained SSL certificate

Some certificate providers, i.e. Entrust, may provide you with a chained
certificate that contains multiple files. If you are using a chained
certificate you will need to concatenate the individual files by appending the
chain cert and root cert to your host cert:

    cat your_host.crt chain.crt root.crt > your_host-chained.crt

You would then set in your `jupyterhub_config.py` file the `ssl_key` and
`ssl_cert` as follows:

    c.JupyterHub.ssl_cert = your_host-chained.crt
    c.JupyterHub.ssl_key = your_host.key


#### Example

Your certificate provider gives you the following files: `example_host.crt`,
`Entrust_L1Kroot.txt` and `Entrust_Root.txt`.

Concatenate the files appending the chain cert and root cert to your host cert:

    cat example_host.crt Entrust_L1Kroot.txt Entrust_Root.txt > example_host-chained.crt

You would then use the `example_host-chained.crt` as the value for
JupyterHub's `ssl_cert`. You may pass this value as a command line option
when starting JupyterHub or more conveniently set the `ssl_cert` variable in
JupyterHub's configuration file, `jupyterhub_config.py`. In `jupyterhub_config.py`,
set:

    c.JupyterHub.ssl_cert = /path/to/example_host-chained.crt
    c.JupyterHub.ssl_key = /path/to/example_host.key

where `ssl_cert` is example-chained.crt and ssl_key to your private key.

Then restart JupyterHub.

See also [JupyterHub SSL encryption](getting-started.md#ssl-encryption).
