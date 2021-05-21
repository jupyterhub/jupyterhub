from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel


# https://jupyterhub.readthedocs.io/en/stable/_static/rest-api/index.html
class Server(BaseModel):
    name: str
    ready: bool
    pending: Optional[str]
    url: str
    progress_url: str
    started: datetime
    last_activity: datetime
    state: Optional[Any]
    user_options: Optional[Any]


class User(BaseModel):
    name: str
    admin: bool
    groups: Optional[List[str]]
    server: Optional[str]
    pending: Optional[str]
    last_activity: datetime
    servers: Optional[Dict[str, Server]]
    scopes: List[str]


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
