# Using JupyterHub's REST API

This section will give you information on:

- what you can do with the API
- create an API token
- add API tokens to the config files
- make an API request programmatically using the requests library
- learn more about JupyterHub's API

## What you can do with the API

Using the [JupyterHub REST API][], you can perform actions on the Hub,
such as:

- checking which users are active
- adding or removing users
- stopping or starting single user notebook servers
- authenticating services

A [REST](https://en.wikipedia.org/wiki/Representational_state_transfer)
API provides a standard way for users to get and send information to the
Hub.

## Create an API token

To send requests using JupyterHub API, you must pass an API token with
the request.

As of [version 0.6.0](../changelog.html), the preferred way of
generating an API token is:

```bash
openssl rand -hex 32
```

This `openssl` command generates a potential token that can then be
added to JupyterHub using `.api_tokens` configuration setting in
`jupyterhub_config.py`.

Alternatively, use the `jupyterhub token` command to generate a token
for a specific hub user by passing the 'username':

```bash
jupyterhub token <username>
```

This command generates a random string to use as a token and registers
it for the given user with the Hub's database.

In [version 0.8.0](../changelog.html), a TOKEN request page for
generating an API token is available from the JupyterHub user interface:

![Request API TOKEN page](../images/token-request.png)

![API TOKEN success page](../images/token-request-success.png)

## Add API tokens to the config file

You may also add a dictionary of API tokens and usernames to the hub's
configuration file, `jupyterhub_config.py` (note that
the **key** is the 'secret-token' while the **value** is the 'username'):

```python
c.JupyterHub.api_tokens = {
    'secret-token': 'username',
}
```

## Make an API request

To authenticate your requests, pass the API token in the request's
Authorization header.

### Use requests

Using the popular Python [requests](http://docs.python-requests.org/en/master/)
library, here's example code to make an API request for the users of a JupyterHub
deployment. An API GET request is made, and the request sends an API token for
authorization. The response contains information about the users:

```python
import requests

api_url = 'http://127.0.0.1:8081/hub/api'

r = requests.get(api_url + '/users',
    headers={
             'Authorization': 'token %s' % token,
            }
    )

r.raise_for_status()
users = r.json()
```

This example provides a slightly more complicated request, yet the
process is very similar:

```python
import requests

api_url = 'http://127.0.0.1:8081/hub/api'

data = {'name': 'mygroup', 'users': ['user1', 'user2']}

r = requests.post(api_url + '/groups/formgrade-data301/users',
    headers={
             'Authorization': 'token %s' % token,
            },
    json=data
)
r.raise_for_status()
r.json()
```

Note that the API token authorizes **JupyterHub** REST API requests. The same
token does **not** authorize access to the [Jupyter Notebook REST API][]
provided by notebook servers managed by JupyterHub. A different token is used
to access the **Jupyter Notebook** API.

## Learn more about the API

You can see the full [JupyterHub REST API][] for details. This REST API Spec can
be viewed in a more [interactive style on swagger's petstore][].
Both resources contain the same information and differ only in its display.
Note: The Swagger specification is being renamed the [OpenAPI Initiative][].

[interactive style on swagger's petstore]: http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyterhub/jupyterhub/master/docs/rest-api.yml#!/default
[OpenAPI Initiative]: https://www.openapis.org/
[JupyterHub REST API]: ../_static/rest-api/index.html
[Jupyter Notebook REST API]: http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyter/notebook/master/notebook/services/api/api.yaml
