import sys

# To run the announcement service managed by the hub, add this.

c.JupyterHub.services = [
    {
        'name': 'announcement',
        'url': 'http://127.0.0.1:8888',
        'command': [sys.executable, "-m", "announcement"],
    }
]

# The announcements need to get on the templates somehow, see page.html
# for an example of how to do this.

c.JupyterHub.template_paths = ["templates"]
