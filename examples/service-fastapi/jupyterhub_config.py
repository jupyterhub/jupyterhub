import os
import warnings

# When Swagger performs OAuth2 in the browser, it will set
# the request host + relative path as the redirect uri, causing a
# uri mismatch if the oauth_redirect_uri is just the relative path
# is set in the c.JupyterHub.services entry (as per default).
# Therefore need to know the request host ahead of time.
if "PUBLIC_HOST" not in os.environ:
    msg = (
        "env PUBLIC_HOST is not set, defaulting to http://127.0.0.1:8000.  "
        "This can cause problems with OAuth.  "
        "Set PUBLIC_HOST to your public (browser accessible) host."
    )
    warnings.warn(msg)
    public_host = "http://127.0.0.1:8000"
else:
    public_host = os.environ["PUBLIC_HOST"].rstrip('/')
service_name = "fastapi"
oauth_redirect_uri = f"{public_host}/services/{service_name}/oauth_callback"

c.JupyterHub.services = [
    {
        "name": service_name,
        "url": "http://127.0.0.1:10202",
        "command": ["uvicorn", "app:app", "--port", "10202"],
        "oauth_redirect_uri": oauth_redirect_uri,
        "environment": {"PUBLIC_HOST": public_host},
    }
]

c.JupyterHub.load_roles = [
    {
        "name": "user",
        # grant all users access to services
        "scopes": ["self", "access:services"],
    },
]


# dummy for testing, create test-user
c.Authenticator.allowed_users = {"test-user"}
c.JupyterHub.authenticator_class = "dummy"
c.JupyterHub.spawner_class = "simple"
