
c.JupyterHub.services = [
        {
            'name': 'announcement',
            'url': 'http://127.0.0.1:8888',
            'command': ["python", "-m", "announcement"],
        }
]

c.JupyterHub.template_paths = ["templates"]
