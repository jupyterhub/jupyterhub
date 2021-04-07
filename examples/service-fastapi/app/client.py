import os

import httpx


### For consideration: turn this into a class with
### feature parity for HubAuth, or even subclass HubAuth?
### See jupyterhub.services.auth.HubAuth for details
def get_client():
    base_url = os.environ["JUPYTERHUB_API_URL"]
    token = os.environ["JUPYTERHUB_API_TOKEN"]
    headers = {"Authorization": "Bearer %s" % token}
    return httpx.AsyncClient(base_url=base_url, headers=headers)
