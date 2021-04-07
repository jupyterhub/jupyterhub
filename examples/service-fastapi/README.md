# Fastapi

[FastAPI](https://fastapi.tiangolo.com/) is a popular new web framework attractive for its type hinting, async support, and [OpenAPI](https://github.com/OAI/OpenAPI-Specification) integration -- meaning you get a Swagger UI for your endpoints right out of the box.

The example Jupyter service in this repo is built with FastAPI and runs with the ASGI server [uvicorn](https://www.uvicorn.org/).  It hardly scratches the surface of FastAPI features, noteably not including any [Pydantic](https://pydantic-docs.helpmanual.io/) models.  The main mechanics to highlight are the multiple auth options in `security.py`, and testing authenticated vs non-authenticated endpoints with the Swagger UI.

# Swagger UI with OAuth demo

![Fastapi Service Example](./fastapi_example.gif)

# Try it out locally

1. Install `fastapi` and other dependencies, then launch Jupyterhub

```
pip install -r requirements.txt
jupyterhub --ip=127.0.0.1
```

2. Visit http://127.0.0.1:8000/services/fastapi or http://127.0.0.1:8000/services/fastapi/docs

3. Try interacting programmatically.  If you create a new token in your control panel or pull out the `JUPYTERHUB_API_TOKEN` in the single user environment, you can skip the third step here.  

```
$ curl -X GET http://127.0.0.1:8000/services/fastapi/
{"Hello":"World"}

$ curl -X GET http://127.0.0.1:8000/services/fastapi/me
{"detail":"Must login with token parameter, cookie, or header"}

$ curl -X POST http://127.0.0.1:8000/hub/api/authorizations/token \
       -d '{"username": "myname", "password": "mypasswd!"}' \
       | jq '.token'
"3fee13ce6d2845da9bd5f2c2170d3428"

$ curl -X GET http://127.0.0.1:8000/services/fastapi/me \
       -H "Authorization: Bearer 3fee13ce6d2845da9bd5f2c2170d3428" \
       | jq .
{
  "kind": "user",
  "name": "myname",
  "admin": false,
  "groups": [],
  "server": null,
  "pending": null,
  "created": "2021-04-06T20:35:49.953710Z",
  "last_activity": "2021-04-06T20:50:15.541302Z",
  "servers": null
}
```

# Try it out in Docker

1. Build and run the Docker image locally

```bash
sudo docker build . -t service-fastapi
sudo docker run -it -p 8000:8000 service-fastapi
```

2. Visit http://127.0.0.1:8000/services/fastapi/docs.  When going through the OAuth flow or getting a token from the control panel, you can log in with `testuser` / `passwd`.

# PUBLIC_HOST

If you are running your service behind a proxy, or on a Docker / Kubernetes infrastructure, you might run into an error during OAuth that says `Mismatching redirect URI`.  In the Jupterhub logs, there will be a warning along the lines of: `[W 2021-04-06 23:40:06.707 JupyterHub provider:498] Redirect uri https://jupyterhub.my.cloud/services/fastapi/oauth_callback != /services/fastapi/oauth_callback`.  This happens because Swagger UI adds the host, as seen in the browser, to the Authorization URL.

To solve that problem, the `oauth_redirect_uri` value in the service initialization needs to match what Swagger will auto-generate and what the service will use when POST'ing to `/oauth2/token`.  In this example, setting the `PUBLIC_HOST` environment variable to your public-facing Hub domain (e.g. `https://jupyterhub.my.cloud`) should make it work.

# Notes on security.py

FastAPI has a concept of a [dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies) using a `Depends` object (and a subclass `Security`) that is automatically instantiated/executed when it is a parameter for your endpoint routes.  You can utilize a `Depends` object for re-useable common parameters or authentication mechanisms like the [`get_user`](https://fastapi.tiangolo.com/tutorial/security/get-current-user) pattern.

JupyterHub OAuth has three ways to authenticate: a `token` url parameter; a `Authorization: Bearer <token>` header; and a `jupyterhub-services` cookie.  FastAPI has helper functions that let us create `Security` (dependency injection) objects for each of those.  When you need to allow multiple / optional authentication dependencies (`Security` objects), then you can use the argument `auto_error=False` and it will return `None` instead of raising an `HTTPException`.

Endpoints that need authentication (`/me` and `/debug` in this example) can leverage the `get_user` pattern and effectively pull the user model from the Hub API when a request has authenticated with cookie / token / header all using the simple syntax,

```python
from .security import get_current_user

@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    "Authenticated function that returns the User model"
    return user
```

# Notes on client.py

FastAPI is designed to be an asyncronous web server, so the interactions with the Hub API should be made asyncronously as well.  Instead of using `requests` to get user information from a token/cookie, this example uses [`httpx`](https://www.python-httpx.org/).  `client.py` defines a small function that creates a `Client` (equivalent of `requests.Session`) with the Hub API url as it's `base_url` and adding the `JUPYTERHUB_API_TOKEN` to every header.

```python
import os

def get_client():
    base_url = os.environ["JUPYTERHUB_API_URL"]
    token = os.environ["JUPYTERHUB_API_TOKEN"]
    headers = {"Authorization": "Bearer %s" % token}
    return httpx.AsyncClient(base_url=base_url, headers=headers)

# use --
async with get_client() as client:
    resp = await client.get('/endpoint')
    ...
```

This example did not try to match the feature set in `jupyterhub.services.auth.HubAuth`, but it should be feasible to create an equivalent `HubAuth` class with async support.