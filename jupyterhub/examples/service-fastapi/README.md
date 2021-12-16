# Fastapi

[FastAPI](https://fastapi.tiangolo.com/) is a popular new web framework attractive for its type hinting, async support, automatic doc generation (Swagger), and more. Their [Feature highlights](https://fastapi.tiangolo.com/features/) sum it up nicely.

# Swagger UI with OAuth demo

![Fastapi Service Example](./fastapi_example.gif)

# Try it out locally

1. Install `fastapi` and other dependencies, then launch Jupyterhub

```
pip install -r requirements.txt
jupyterhub --ip=127.0.0.1
```

2. Visit http://127.0.0.1:8000/services/fastapi or http://127.0.0.1:8000/services/fastapi/docs
   Login with username 'test-user' and any password.

3. Try interacting programmatically. If you create a new token in your control panel or pull out the `JUPYTERHUB_API_TOKEN` in the single user environment, you can skip the third step here.

```
$ curl -X GET http://127.0.0.1:8000/services/fastapi/
{"Hello":"World"}

$ curl -X GET http://127.0.0.1:8000/services/fastapi/me
{"detail":"Must login with token parameter, or Authorization bearer header"}

$ curl -X POST http://127.0.0.1:8000/hub/api/users/test-user/tokens \
       -d '{"auth": {"username": "test-user", "password": "mypasswd!"}}' \
       | jq '.token'
"3fee13ce6d2845da9bd5f2c2170d3428"

$ curl -X GET http://127.0.0.1:8000/services/fastapi/me \
       -H "Authorization: Bearer 3fee13ce6d2845da9bd5f2c2170d3428" \
       | jq .
{
  "name": "test-user",
  "admin": false,
  "groups": [],
  "server": null,
  "pending": null,
  "last_activity": "2021-05-21T09:13:00.514309+00:00",
  "servers": null,
  "scopes": [
    "access:services",
    "access:servers!user=test-user",
    "...",
  ]
}
```

# Try it out in Docker

1. Build and run the Docker image locally

```bash
sudo docker build . -t service-fastapi
sudo docker run -it -p 8000:8000 service-fastapi
```

2. Visit http://127.0.0.1:8000/services/fastapi/docs. When going through the OAuth flow or getting a token from the control panel, you can log in with `testuser` / `passwd`.

# PUBLIC_HOST

If you are running your service behind a proxy, or on a Docker / Kubernetes infrastructure, you might run into an error during OAuth that says `Mismatching redirect URI`. In the Jupterhub logs, there will be a warning along the lines of: `[W 2021-04-06 23:40:06.707 JupyterHub provider:498] Redirect uri https://jupyterhub.my.cloud/services/fastapi/oauth_callback != /services/fastapi/oauth_callback`. This happens because Swagger UI adds the request host, as seen in the browser, to the Authorization URL.

To solve that problem, the `oauth_redirect_uri` value in the service initialization needs to match what Swagger will auto-generate and what the service will use when POST'ing to `/oauth2/token`. In this example, setting the `PUBLIC_HOST` environment variable to your public-facing Hub domain (e.g. `https://jupyterhub.my.cloud`) should make it work.

# Notes on security.py

FastAPI has a concept of a [dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies) using a `Depends` object (and a subclass `Security`) that is automatically instantiated/executed when it is a parameter for your endpoint routes. You can utilize a `Depends` object for re-useable common parameters or authentication mechanisms like the [`get_user`](https://fastapi.tiangolo.com/tutorial/security/get-current-user) pattern.

JupyterHub OAuth has three ways to authenticate: a `token` url parameter; a `Authorization: Bearer <token>` header; and a (deprecated) `jupyterhub-services` cookie. FastAPI has helper functions that let us create `Security` (dependency injection) objects for each of those. When you need to allow multiple / optional authentication dependencies (`Security` objects), then you can use the argument `auto_error=False` and it will return `None` instead of raising an `HTTPException`.

Endpoints that need authentication (`/me` and `/debug` in this example) can leverage the `get_user` pattern and effectively pull the user model from the Hub API when a request has authenticated with cookie / token / header all using the simple syntax,

```python
from .security import get_current_user
from .models import User

@router.get("/new_endpoint")
async def new_endpoint(user: User = Depends(get_current_user)):
    "Function that needs to work with an authenticated user"
    return {"Hello": user.name}
```

# Notes on client.py

FastAPI is designed to be an asynchronous web server, so the interactions with the Hub API should be made asynchronously as well. Instead of using `requests` to get user information from a token/cookie, this example uses [`httpx`](https://www.python-httpx.org/). `client.py` defines a small function that creates a `Client` (equivalent of `requests.Session`) with the Hub API url as it's `base_url` and adding the `JUPYTERHUB_API_TOKEN` to every header.

Consider this a very minimal alternative to using `jupyterhub.services.auth.HubOAuth`

```python
# client.py
import os

def get_client():
    base_url = os.environ["JUPYTERHUB_API_URL"]
    token = os.environ["JUPYTERHUB_API_TOKEN"]
    headers = {"Authorization": "Bearer %s" % token}
    return httpx.AsyncClient(base_url=base_url, headers=headers)
```

```python
# other modules
from .client import get_client

async with get_client() as client:
    resp = await client.get('/endpoint')
    ...
```
