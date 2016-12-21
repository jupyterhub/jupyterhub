# Using JupyterHub's REST API

Using the [JupyterHub REST API][], you can perform actions on the Hub,
such as:

- checking which users are active
- adding or removing users
- stopping or starting single user notebook servers
- authenticating services

A [REST](https://en.wikipedia.org/wiki/Representational_state_transfer)
API provides a standard way for users to get and send information to the
Hub.


## Creating an API token
To send requests using JupyterHub API, you must pass an API token with the
request. You can create a token for an individual user using the following
command:

    jupyterhub token USERNAME


## Adding tokens to the config file
You may also add a dictionary of API tokens and usernames to the hub's
configuration file, `jupyterhub_config.py`:

```python
c.JupyterHub.api_tokens = {
    'secret-token': 'username',
}
```


## Making an API request

To authenticate your requests, pass the API token in the request's
Authorization header.

**Example: List the hub's users**

Using the popular Python requests library, the following code sends an API
request and an API token for authorization:

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


## Learning more about the API

You can see the full [JupyterHub REST API][] for details.
The same REST API Spec can be viewed in a more interactive style [on swagger's petstore][].
Both resources contain the same information and differ only in its display.
Note: The Swagger specification is being renamed the [OpenAPI Initiative][].

[on swagger's petstore]: http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyterhub/jupyterhub/master/docs/rest-api.yml#!/default
[OpenAPI Initiative]: https://www.openapis.org/
[JupyterHub REST API]: ./_static/rest-api/index.html
