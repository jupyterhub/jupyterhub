import os

from fastapi import HTTPException, Security, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.security.api_key import APIKeyCookie, APIKeyQuery

from .client import get_client

### For authenticated endpoints, we want to get auth from one of three ways
### 1. "token" in the url params
### 2. "jupyterhub-services" cookie (or config via env)
### 3. Authorization Bearer header (with oauth to Hub support)
auth_by_param = APIKeyQuery(name="token", auto_error=False)

COOKIE_NAME = os.getenv("JUPYTERHUB_COOKIE_NAME", "jupyterhub-services")
auth_by_cookie = APIKeyCookie(name=COOKIE_NAME, auto_error=False)

if "PUBLIC_HOST" in os.environ:
    ### When running in Docker or maybe other infrastructure,
    ### JUPYTERHUB_API_URL is "http://jupyterhub" but we need to give
    ### clients (swagger webpage) a link to the public url
    auth_url = os.environ["PUBLIC_HOST"] + "/hub/api/oauth2/authorize"
else:
    auth_url = os.environ["JUPYTERHUB_API_URL"] + "/oauth2/authorize"
auth_by_header = OAuth2AuthorizationCodeBearer(
    authorizationUrl=auth_url, tokenUrl="get_token", auto_error=False
)
### ^^ For Oauth in the Swagger webpage, we set the authorizationUrl
### to the Hub /oauth2/authorize endpoint, so browser does a GET there and
### receives a 'code' in return.  Then the browser does a POST to our
### internal /get_token endpoint with that code, and our server subsequently
### POSTs to Hub /oauth2/token to get/return an acecss_token.
### The reason for the double POST is that the client (swagger ui) doesn't have
### the client_secret (JUPYTERHUB_API_TOKEN), but our server does.

### For consideration: build a pydantic User model
### instead of just returning the dict from Hub api?
### Also: optimize performance with a cache instead of
### always hitting the Hub api?
async def get_current_user(
    auth_by_cookie: str = Security(auth_by_cookie),
    auth_by_param: str = Security(auth_by_param),
    auth_by_header: str = Security(auth_by_header),
):
    ### Note all three Security functions are auto_error=False,
    ### meaning if the scheme (header/cookie/param) isn't present
    ### then they return None.
    ### The cookie can be tricky.  Navigating to the Hub login
    ### page but not logging in still sets a cookie, but
    ### Hub API returns a 404 if you query that cookie
    user = None
    if auth_by_param is not None or auth_by_header is not None:
        token = auth_by_param or auth_by_header
        async with get_client() as client:
            endpoint = "/authorizations/token/%s" % token
            resp = await client.get(endpoint)
            if resp.is_error:
                raise HTTPException(
                    resp.status_code,
                    detail={
                        "msg": "Error getting user info from token",
                        "request_url": str(resp.request.url),
                        "token": token,
                        "hub_response": resp.json(),
                    },
                )
            else:
                user = resp.json()

    elif auth_by_cookie is not None:
        async with get_client() as client:
            endpoint = "/authorizations/cookie/%s/%s" % (COOKIE_NAME, auth_by_cookie)
            resp = await client.get(endpoint)
            if not resp.is_error:
                user = resp.json()

    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Must login with token parameter, cookie, or header",
        )
    else:
        return user
