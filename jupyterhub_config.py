c.JupyterHub.template_paths = ['/home/celia/SAIEP/ESTIN-SAIEP/templates']
c.Authenticator.allow_all = True
c.Authenticator.admin_users = {'celia'}
c.Spawner.cmd = ['/home/celia/SAIEP/ESTIN-SAIEP/venv/bin/jupyterhub-singleuser']
