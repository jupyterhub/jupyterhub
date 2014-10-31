# Configuration file for jupyterhub (postgres example).

c = get_config()

# Add some users.
c.JupyterHubApp.admin_users = {'rhea'}
c.Authenticator.whitelist = {'ganymede', 'io', 'rhea'}

# Set up the database url.
import os;
pg_pass = os.getenv('JPY_PSQL_PASSWORD')
pg_host = os.getenv('POSTGRES_PORT_5432_TCP_ADDR')
c.JupyterHubApp.db_url = 'postgresql://jupyterhub:{}@{}:5432/jupyterhub'.format(
    pg_pass,
    pg_host,
)
