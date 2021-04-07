import os

service = {
    "name": "fastapi",
    "url": "http://127.0.0.1:10202",
    "command": ["uvicorn", "app:app", "--port", "10202"],
}
# If running behind a proxy, or in Docker / Kubernetes infrastructure,
# you probably need to set a different public Hub host than the
# internal JUPYTERHUB_API_URL host
if "PUBLIC_HOST" in os.environ:
    public_host = os.environ["PUBLIC_HOST"]
    service["oauth_redirect_uri"] = f"{public_host}/services/fastapi/oauth_callback"
    service["environment"] = {"PUBLIC_HOST": public_host}

c.JupyterHub.services = [service]
