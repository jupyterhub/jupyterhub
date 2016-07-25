# The JupyterHub REST API

JupyterHub has a [REST API](https://en.wikipedia.org/wiki/Representational_state_transfer), which you can use to perform actions on the Hub,
such as checking what users are active, adding or removing users,
stopping or starting user servers, etc.

To get access to the JupyterHub API, you must create a token.
You can create a token for a particular user with:

    jupyterhub token USERNAME

Alternately, you can load API tokens in your `jupyterhub_config.py`:

```python
c.JupyterHub.api_tokens = {
    'secret-token': 'username',
}
```

To authenticate your requests, pass this token in the Authorization header.
For example, to list users with requests in Python:

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

You can see the full  [REST API Spec](../_static/rest-api/index.html) for details.
A fancier version of the same information can be viewed [on swagger's petstore][].

[on swagger's petstore]: http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyterhub/jupyterhub/master/docs/rest-api.yml#!/default
