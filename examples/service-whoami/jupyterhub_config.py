from getpass import getuser
import os

c.JupyterHub.api_tokens = {
    os.environ['WHOAMI_HUB_API_TOKEN']: getuser(),
}
