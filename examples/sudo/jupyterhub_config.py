# Configuration file for jupyterhub

c = get_config()

c.JupyterHub.admin_users = {'rhea'}
c.LocalProcessSpawner.set_user = 'sudo'
c.Authenticator.whitelist = {'ganymede', 'io', 'rhea'}
