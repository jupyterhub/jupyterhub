import os

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Form
from fastapi import Request

from .client import get_client
from .security import get_current_user

# APIRouter prefix cannot end in /
service_prefix = os.getenv("JUPYTERHUB_SERVICE_PREFIX", "").rstrip("/")
router = APIRouter(prefix=service_prefix)


@router.post("/get_token", include_in_schema=False)
async def get_token(code: str = Form(...)):
    "Callback function for OAuth2AuthorizationCodeBearer scheme"
    # The only thing we need in this form post is the code
    # Everything else we can hardcode / pull from env
    async with get_client() as client:
        redirect_uri = (
            os.getenv("PUBLIC_HOST", "") + os.environ["JUPYTERHUB_OAUTH_CALLBACK_URL"],
        )
        data = {
            "client_id": os.environ["JUPYTERHUB_CLIENT_ID"],
            "client_secret": os.environ["JUPYTERHUB_API_TOKEN"],
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        resp = await client.post("/oauth2/token", data=data)
    ### response is {'access_token': <token>, 'token_type': 'Bearer'}
    return resp.json()


@router.get("/")
async def index():
    "Non-authenticated function that returns {'Hello': 'World'}"
    return {"Hello": "World"}


# See security.py comment, consider a User model instead of dict?
@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    "Authenticated function that returns the User model"
    return user


@router.get("/debug")
async def index(request: Request, user: dict = Depends(get_current_user)):
    """
    Authenticated function that returns a few pieces of debug
     * Environ of the service process
     * Request headers
     * User model
    """
    return {
        "env": dict(os.environ),
        "headers": dict(request.headers),
        "user": user,
    }
