import os

import httpx


# a minimal alternative to using HubOAuth class
def get_client():
    base_url = os.environ["JUPYTERHUB_API_URL"]
    token = os.environ["JUPYTERHUB_API_TOKEN"]
    headers = {"Authorization": "Bearer %s" % token}
    return httpx.AsyncClient(base_url=base_url, headers=headers)
