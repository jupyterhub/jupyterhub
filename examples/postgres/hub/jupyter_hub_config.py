# Configuration file for jupyterhub.

c = get_config()

#------------------------------------------------------------------------------
# JupyterHubApp configuration
#------------------------------------------------------------------------------

# An Application for starting a Multi-User Jupyter Notebook server.

# JupyterHubApp will inherit config from: Application

# Path to SSL key file for the public facing interface of the proxy
# 
# Use with ssl_cert
# c.JupyterHubApp.ssl_key = ''

# The location of jupyter data files (e.g. /usr/local/share/jupyter)
# c.JupyterHubApp.data_files_path = '/home/ssanderson/quantopian/jupyterhub/share/jupyter'

# The ip for the proxy API handlers
# c.JupyterHubApp.proxy_api_ip = 'localhost'

# Supply extra arguments that will be passed to Jinja environment.
# c.JupyterHubApp.jinja_environment_options = {}

# The public facing ip of the proxy
# c.JupyterHubApp.ip = ''

# The cookie secret to use to encrypt cookies.
# 
# Loaded from the JPY_COOKIE_SECRET env variable by default.
# c.JupyterHubApp.cookie_secret = u''

# Generate default config file
# c.JupyterHubApp.generate_config = False

# The port for the proxy API handlers
# c.JupyterHubApp.proxy_api_port = 0

# The command to start the http proxy.
# 
# Only override if configurable-http-proxy is not on your PATH
# c.JupyterHubApp.proxy_cmd = 'configurable-http-proxy'

# The date format used by logging formatters for %(asctime)s
# c.JupyterHubApp.log_datefmt = '%Y-%m-%d %H:%M:%S'

# The public facing port of the proxy
# c.JupyterHubApp.port = 8000

# Set the log level by value or name.
# c.JupyterHubApp.log_level = 30

# The base URL of the entire application
# c.JupyterHubApp.base_url = '/'

# The Proxy Auth token.
# 
# Loaded from the CONFIGPROXY_AUTH_TOKEN env variable by default.
# c.JupyterHubApp.proxy_auth_token = u''

# 
# c.JupyterHubApp.tornado_settings = {}

# Purge and reset the database.
# c.JupyterHubApp.reset_db = False

# Include any kwargs to pass to the database connection. See
# sqlalchemy.create_engine for details.
# c.JupyterHubApp.db_kwargs = {}

# File to write PID Useful for daemonizing jupyterhub.
# c.JupyterHubApp.pid_file = ''

# The port for this process
# c.JupyterHubApp.hub_port = 8081

# The config file to load
# c.JupyterHubApp.config_file = 'jupyter_hub_config.py'

# Answer yes to any questions (e.g. confirm overwrite)
# c.JupyterHubApp.answer_yes = False

# The prefix for the hub server. Must not be '/'
# c.JupyterHubApp.hub_prefix = '/hub/'

# Class for authenticating users.
# 
# This should be a class with the following form:
# 
# - constructor takes one kwarg: `config`, the IPython config object.
# 
# - is a tornado.gen.coroutine
# - returns username on success, None on failure
# - takes two arguments: (handler, data),
#   where `handler` is the calling web.RequestHandler,
#   and `data` is the POST form data from the login page.
# c.JupyterHubApp.authenticator_class = <class 'jupyterhub.auth.PAMAuthenticator'>

# url for the database. e.g. `sqlite:///jupyterhub.sqlite`
import os;
pg_pass = os.getenv('JPY_PSQL_PASSWORD')
pg_host = os.getenv('POSTGRES_PORT_5432_TCP_ADDR')
c.JupyterHubApp.db_url = 'postgresql://jupyterhub:{}@{}:5432/jupyterhub'.format(
    pg_pass,
    pg_host,
)

# Interval (in seconds) at which to check if the proxy is running.
# c.JupyterHubApp.proxy_check_interval = 30

# The class to use for spawning single-user servers.
# 
# Should be a subclass of Spawner.
# c.JupyterHubApp.spawner_class = <class 'jupyterhub.spawner.LocalProcessSpawner'>

# Interval (in seconds) at which to update last-activity timestamps.
# c.JupyterHubApp.last_activity_interval = 600

# set of usernames of admin users
# 
# If unspecified, only the user that launches the server will be admin.
# c.JupyterHubApp.admin_users = set([])

# Path to SSL certificate file for the public facing interface of the proxy
# 
# Use with ssl_key
# c.JupyterHubApp.ssl_cert = ''

# The Logging format template
# c.JupyterHubApp.log_format = '[%(name)s]%(highlevel)s %(message)s'

# The ip for this process
# c.JupyterHubApp.hub_ip = 'localhost'

# log all database transactions. This has A LOT of output
# c.JupyterHubApp.debug_db = False

#------------------------------------------------------------------------------
# Spawner configuration
#------------------------------------------------------------------------------

# Base class for spawning single-user notebook servers.
# 
# Subclass this, and override the following methods:
# 
# - load_state - get_state - start - stop - poll

# The command used for starting notebooks.
# c.Spawner.cmd = ['jupyterhub-singleuser']

# Enable debug-logging of the single-user server
# c.Spawner.debug = False

# Whitelist of environment variables for the subprocess to inherit
# c.Spawner.env_keep = ['PATH', 'PYTHONPATH', 'CONDA_ROOT', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV', 'LANG', 'LC_ALL']

# Interval (in seconds) on which to poll the spawner.
# c.Spawner.poll_interval = 30

#------------------------------------------------------------------------------
# LocalProcessSpawner configuration
#------------------------------------------------------------------------------

# A Spawner that just uses Popen to start local processes.

# LocalProcessSpawner will inherit config from: Spawner

# Seconds to wait for process to halt after SIGTERM before proceeding to SIGKILL
# c.LocalProcessSpawner.TERM_TIMEOUT = 5

# Whitelist of environment variables for the subprocess to inherit
# c.LocalProcessSpawner.env_keep = ['PATH', 'PYTHONPATH', 'CONDA_ROOT', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV', 'LANG', 'LC_ALL']

# Seconds to wait for process to halt after SIGINT before proceeding to SIGTERM
# c.LocalProcessSpawner.INTERRUPT_TIMEOUT = 10

# Seconds to wait for process to halt after SIGKILL before giving up
# c.LocalProcessSpawner.KILL_TIMEOUT = 5

# The command used for starting notebooks.
# c.LocalProcessSpawner.cmd = ['jupyterhub-singleuser']

# Interval (in seconds) on which to poll the spawner.
# c.LocalProcessSpawner.poll_interval = 30

# scheme for setting the user of the spawned process
# 
# 'sudo' can be more prudently restricted, but 'setuid' is simpler for a server
# run as root
# c.LocalProcessSpawner.set_user = 'setuid'

# Enable debug-logging of the single-user server
# c.LocalProcessSpawner.debug = False

# arguments to be passed to sudo (in addition to -u [username])
# 
# only used if set_user = sudo
# c.LocalProcessSpawner.sudo_args = ['-n']

#------------------------------------------------------------------------------
# Authenticator configuration
#------------------------------------------------------------------------------

# A class for authentication.
# 
# The API is one method, `authenticate`, a tornado gen.coroutine.

# Username whitelist.
# 
# Use this to restrict which users can login. If empty, allow any user to
# attempt login.
# c.Authenticator.whitelist = set([])

#------------------------------------------------------------------------------
# PAMAuthenticator configuration
#------------------------------------------------------------------------------

# Authenticate local *ix users with PAM

# PAMAuthenticator will inherit config from: LocalAuthenticator, Authenticator

# If a user is added that doesn't exist on the system, should I try to create
# the system user?
# c.PAMAuthenticator.create_system_users = False

# Username whitelist.
# 
# Use this to restrict which users can login. If empty, allow any user to
# attempt login.
# c.PAMAuthenticator.whitelist = set([])

# The PAM service to use for authentication.
# c.PAMAuthenticator.service = 'login'

# The encoding to use for PAM
# c.PAMAuthenticator.encoding = 'utf8'
