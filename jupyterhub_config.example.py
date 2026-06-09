import os

base_dir = os.path.dirname(os.path.abspath(__file__))

c.JupyterHub.template_paths = [os.path.join(base_dir, 'templates')]
c.Authenticator.allow_all = True
c.Authenticator.admin_users = {'celia'}
c.Spawner.cmd = [os.path.join(base_dir, 'venv/bin/jupyterhub-singleuser')]
