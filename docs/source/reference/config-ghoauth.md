# Configure GitHub OAuth

In this example, we show a configuration file for a fairly standard JupyterHub
deployment with the following assumptions:

* Running JupyterHub on a single cloud server
* Using SSL on the standard HTTPS port 443
* Using GitHub OAuth (using oauthenticator) for login
* Using the default spawner (to configure other spawners, uncomment and edit
  `spawner_class` as well as follow the instructions for your desired spawner)
* Users exist locally on the server
* Users' notebooks to be served from `~/assignments` to allow users to browse
  for notebooks within other users' home directories
* You want the landing page for each user to be a `Welcome.ipynb` notebook in
  their assignments directory.
* All runtime files are put into `/srv/jupyterhub` and log files in `/var/log`.


The `jupyterhub_config.py` file would have these settings:

```python
# jupyterhub_config.py file
c = get_config()

import os
pjoin = os.path.join

runtime_dir = os.path.join('/srv/jupyterhub')
ssl_dir = pjoin(runtime_dir, 'ssl')
if not os.path.exists(ssl_dir):
    os.makedirs(ssl_dir)

# Allows multiple single-server per user
c.JupyterHub.allow_named_servers = True

# https on :443
c.JupyterHub.port = 443
c.JupyterHub.ssl_key = pjoin(ssl_dir, 'ssl.key')
c.JupyterHub.ssl_cert = pjoin(ssl_dir, 'ssl.cert')

# put the JupyterHub cookie secret and state db
# in /var/run/jupyterhub
c.JupyterHub.cookie_secret_file = pjoin(runtime_dir, 'cookie_secret')
c.JupyterHub.db_url = pjoin(runtime_dir, 'jupyterhub.sqlite')
# or `--db=/path/to/jupyterhub.sqlite` on the command-line

# use GitHub OAuthenticator for local users
c.JupyterHub.authenticator_class = 'oauthenticator.LocalGitHubOAuthenticator'
c.GitHubOAuthenticator.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']

# create system users that don't exist yet
c.LocalAuthenticator.create_system_users = True

# specify users and admin
c.Authenticator.allowed_users = {'rgbkrk', 'minrk', 'jhamrick'}
c.Authenticator.admin_users = {'jhamrick', 'rgbkrk'}

# uses the default spawner
# To use a different spawner, uncomment `spawner_class` and set to desired
# spawner (e.g. SudoSpawner). Follow instructions for desired spawner
# configuration.
# c.JupyterHub.spawner_class = 'sudospawner.SudoSpawner'

# start single-user notebook servers in ~/assignments,
# with ~/assignments/Welcome.ipynb as the default landing page
# this config could also be put in
# /etc/jupyter/jupyter_notebook_config.py
c.Spawner.notebook_dir = '~/assignments'
c.Spawner.args = ['--NotebookApp.default_url=/notebooks/Welcome.ipynb']
```

Using the GitHub Authenticator requires a few additional
environment variable to be set prior to launching JupyterHub:

```bash
export GITHUB_CLIENT_ID=github_id
export GITHUB_CLIENT_SECRET=github_secret
export OAUTH_CALLBACK_URL=https://example.com/hub/oauth_callback
export CONFIGPROXY_AUTH_TOKEN=super-secret
# append log output to log file /var/log/jupyterhub.log
jupyterhub -f /etc/jupyterhub/jupyterhub_config.py &>> /var/log/jupyterhub.log
```
