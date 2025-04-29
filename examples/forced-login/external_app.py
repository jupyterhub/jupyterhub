"""An external app for laucnhing JupyuterHub with specified usernames

This one serves a form with a single username input field

After entering the username, generate a token and redirect to hub login with that token,
which is then exchanged for a username.

Users cannot login to JupyterHub directly, only via this app.
"""

import hashlib
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from yarl import URL

from jupyterhub.utils import url_path_join

app_dir = Path(__file__).parent.resolve()
index_html = app_dir / "index.html"
app = FastAPI()

log = logging.getLogger("uvicorn.error")

_tokens_to_username = {}

jupyterhub_url = URL(os.environ.get("JUPYTERHUB_URL", "http://127.0.0.1:8000/"))

# how many seconds do they have to complete the exchange before the token expires?
token_lifetime = 30


def _hash(token):
    """Hash a token for storage"""
    return hashlib.sha256(token.encode("utf8", "replace")).hexdigest()


@app.get("/")
async def get():
    with index_html.open() as f:
        return HTMLResponse(f.read())


@app.post("/")
async def launch(username: Annotated[str, Form()], path: Annotated[str, Form()]):
    """Begin login

    1. issue token for login
    2. associate token with username
    3. redirect to /hub/login?login_token=...
    """
    token = secrets.token_urlsafe(32)
    hashed_token = _hash(token)
    log.info(f"Creating token for {username}, redirecting to {path}")
    _tokens_to_username[hashed_token] = (username, time.monotonic() + token_lifetime)
    login_url = (jupyterhub_url / "hub/login").extend_query(
        login_token=token, next=url_path_join("/hub/user-redirect", path)
    )
    log.info(login_url)

    return RedirectResponse(login_url, status_code=status.HTTP_303_SEE_OTHER)


@app.post("/login", response_class=JSONResponse)
async def login(token: Annotated[str, Body(embed=True)]):
    """
    Callback to exchange a token for a username

    token is consumed, can only be used once
    """
    now = time.monotonic()
    hashed_token = _hash(token)
    if hashed_token not in _tokens_to_username:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"message": "invalid token"}
        )
    username, expires_at = _tokens_to_username.pop(hashed_token)
    if expires_at < now:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "token expired"},
        )
    return {"name": username}


def main():
    """Launches the application on port 5000 with uvicorn"""
    import uvicorn

    uvicorn.run(app, port=9000)


if __name__ == "__main__":
    main()
