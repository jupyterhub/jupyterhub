# Configuration file for jupyterhub (postgres example).

c = get_config()

# Add some users.
c.JupyterHub.admin_users = {'rhea'}
c.Authenticator.whitelist = {'ganymede', 'io', 'rhea'}

# These environment variables are automatically supplied by the linked postgres
# container.
import os

pg_pass = os.getenv('POSTGRES_ENV_JPY_PSQL_PASSWORD')
pg_host = os.getenv('POSTGRES_PORT_5432_TCP_ADDR')
c.JupyterHub.db_url = 'postgresql://jupyterhub:{}@{}:5432/jupyterhub'.format(
    pg_pass, pg_host
)
