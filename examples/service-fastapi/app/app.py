import os

from fastapi import FastAPI

from .service import router

### When managed by Jupyterhub, the actual endpoints
### will be served out prefixed by /services/:name.
### One way to handle this with FastAPI is to use an APIRouter.
### All routes are defined in service.py

app = FastAPI(
    title="Example FastAPI Service",
    version="0.1",
    ### Serve out Swagger from the service prefix (<hub>/services/:name/docs)
    openapi_url=router.prefix + "/openapi.json",
    docs_url=router.prefix + "/docs",
    redoc_url=router.prefix + "/redoc",
    ### Add our service client id to the /docs Authorize form automatically
    swagger_ui_init_oauth={"clientId": os.environ["JUPYTERHUB_CLIENT_ID"]},
    ### Default /docs/oauth2 redirect will cause Hub
    ### to raise oauth2 redirect uri mismatch errors
    swagger_ui_oauth2_redirect_url=os.environ["JUPYTERHUB_OAUTH_CALLBACK_URL"],
)
app.include_router(router)
