(api-index)=

# JupyterHub API Reference

<!--
    Below is a MyST field list, using MyST substitution, as supported
    by enabling the respective MyST extensions in docs/source/conf.py.
-->

:Date: {{ date }}
:Release: {{ version }}

JupyterHub also provides a REST API for administration of the Hub and users.
The documentation on [Using JupyterHub's REST API](using-jupyterhub-rest-api) provides
information on:

- what you can do with the API
- creating an API token
- adding API tokens to the config files
- making an API request programmatically using the requests library
- learning more about JupyterHub's API

```{toctree}
:maxdepth: 1

../rest-api
app
auth
spawner
proxy
user
service
services.auth
```

[openapi initiative]: https://www.openapis.org/
