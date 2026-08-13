# Internal HTTP Client configuration

This private http client is used for internal communication between JupyterHub components.
The client and class are not intended for direct public use,
but can be configured for performance tuning of the underlying [aiohttp] Client objects.

[aiohttp]: https://docs.aiohttp.org

```{eval-rst}
.. module:: jupyterhub.httpclient
```

## {class}`JupyterHubHTTPClient`

```{eval-rst}
.. autoconfigurable:: JupyterHubHTTPClient
```
