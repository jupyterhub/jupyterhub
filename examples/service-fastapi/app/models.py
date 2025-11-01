from datetime import datetime
from typing import Any

from pydantic import BaseModel


# https://jupyterhub.readthedocs.io/en/stable/_static/rest-api/index.html
class Server(BaseModel):
    name: str
    ready: bool
    pending: str | None
    url: str
    progress_url: str
    started: datetime
    last_activity: datetime
    state: Any | None
    user_options: Any | None


class User(BaseModel):
    name: str
    admin: bool
    groups: list[str] | None
    server: str | None
    pending: str | None
    last_activity: datetime
    servers: dict[str, Server] | None
    scopes: list[str]


# https://stackoverflow.com/questions/64501193/fastapi-how-to-use-httpexception-in-responses
class AuthorizationError(BaseModel):
    detail: str


class HubResponse(BaseModel):
    msg: str
    request_url: str
    token: str
    response_code: int
    hub_response: dict


class HubApiError(BaseModel):
    detail: HubResponse
