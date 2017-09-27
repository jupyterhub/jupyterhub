import os
c.JupyterHub.cookie_secret = os.urandom(32)

DB = os.environ.get('DB')
if DB == 'mysql':
    c.JupyterHub.db_url = 'mysql+pymysql://root@127.0.0.1/jupyterhub_upgrade'
elif DB == 'postgres':
    c.JupyterHub.db_url = 'postgresql://postgres@127.0.0.1/jupyterhub_upgrade'

c.JupyterHub.authenticator_class = 'jupyterhub.auth.Authenticator'
c.Authenticator.whitelist = {'alpha', 'beta', 'gamma'}
