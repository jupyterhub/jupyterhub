# Configuration examples

This section provides configuration files and tips for the following
configurations:

- Example with GitHub OAuth
- Example with nginx reverse proxy


## Example with GitHub OAuth

In the following example, we show a configuration files for a fairly standard JupyterHub deployment with the following assumptions:

* JupyterHub is running on a single cloud server
* Using SSL on the standard HTTPS port 443
* You want to use GitHub OAuth (using oauthenticator) for login
* You need the users to exist locally on the server
* You want users' notebooks to be served from `~/assignments` to allow users to browse for notebooks within
  other users home directories
* You want the landing page for each user to be a Welcome.ipynb notebook in their assignments directory.
* All runtime files are put into `/srv/jupyterhub` and log files in `/var/log`.

Let's start out with `jupyterhub_config.py`:

```python
# jupyterhub_config.py
c = get_config()

import os
pjoin = os.path.join

runtime_dir = os.path.join('/srv/jupyterhub')
ssl_dir = pjoin(runtime_dir, 'ssl')
if not os.path.exists(ssl_dir):
    os.makedirs(ssl_dir)


# https on :443
c.JupyterHub.port = 443
c.JupyterHub.ssl_key = pjoin(ssl_dir, 'ssl.key')
c.JupyterHub.ssl_cert = pjoin(ssl_dir, 'ssl.cert')

# put the JupyterHub cookie secret and state db
# in /var/run/jupyterhub
c.JupyterHub.cookie_secret_file = pjoin(runtime_dir, 'cookie_secret')
c.JupyterHub.db_url = pjoin(runtime_dir, 'jupyterhub.sqlite')
# or `--db=/path/to/jupyterhub.sqlite` on the command-line

# put the log file in /var/log
c.JupyterHub.extra_log_file = '/var/log/jupyterhub.log'

# use GitHub OAuthenticator for local users

c.JupyterHub.authenticator_class = 'oauthenticator.LocalGitHubOAuthenticator'
c.GitHubOAuthenticator.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
# create system users that don't exist yet
c.LocalAuthenticator.create_system_users = True

# specify users and admin
c.Authenticator.whitelist = {'rgbkrk', 'minrk', 'jhamrick'}
c.Authenticator.admin_users = {'jhamrick', 'rgbkrk'}

# start single-user notebook servers in ~/assignments,
# with ~/assignments/Welcome.ipynb as the default landing page
# this config could also be put in
# /etc/ipython/ipython_notebook_config.py
c.Spawner.notebook_dir = '~/assignments'
c.Spawner.args = ['--NotebookApp.default_url=/notebooks/Welcome.ipynb']
```

Using the GitHub Authenticator [requires a few additional env variables][oauth-setup],
which we will need to set when we launch the server:

```bash
export GITHUB_CLIENT_ID=github_id
export GITHUB_CLIENT_SECRET=github_secret
export OAUTH_CALLBACK_URL=https://example.com/hub/oauth_callback
export CONFIGPROXY_AUTH_TOKEN=super-secret
jupyterhub -f /path/to/aboveconfig.py
```

## Example with nginx reverse proxy

In the following example, we show configuration files for a JupyterHub server running locally on port `8000` but accessible from the outside on the standard SSL port `443`. This could be useful if the JupyterHub server machine is also hosting other domains or content on `443`. The goal here is to have the following be true:

* JupyterHub is running on a server, accessed *only* via `HUB.DOMAIN.TLD:443`
* On the same machine, `NO_HUB.DOMAIN.TLD` strictly serves different content, also on port `443`
* `nginx` is used to manage the web servers / reverse proxy (which means that only nginx will be able to bind two servers to `443`)
* After testing, the server in question should be able to score an A+ on the Qualys SSL Labs [SSL Server Test](https://www.ssllabs.com/ssltest/)

Let's start out with `jupyterhub_config.py`:

```python
# Force the proxy to only listen to connections to 127.0.0.1
c.JupyterHub.ip = '127.0.0.1'
```

The `nginx` server config files are fairly standard fare except for the two `location` blocks within the `HUB.DOMAIN.TLD` config file:

```bash
# HTTP server to redirect all 80 traffic to SSL/HTTPS
server {
	listen 80;
	server_name HUB.DOMAIN.TLD;

	# Tell all requests to port 80 to be 302 redirected to HTTPS
	return 302 https://$host$request_uri;
}

# HTTPS server to handle JupyterHub
server {
	listen 443;
	ssl on;

	server_name HUB.DOMAIN.TLD;

	ssl_certificate /etc/letsencrypt/live/HUB.DOMAIN.TLD/fullchain.pem
	ssl_certificate_key /etc/letsencrypt/live/HUB.DOMAIN.TLD/privkey.pem

	ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_prefer_server_ciphers on;
    ssl_dhparam /etc/ssl/certs/dhparam.pem;
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header Strict-Transport-Security max-age=15768000;

	# Managing literal requests to the JupyterHub front end
	location / {
		proxy_pass https://127.0.0.1:8000;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header Host $host;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

	# Managing WebHook/Socket requests between hub user servers and external proxy
    location ~* /(api/kernels/[^/]+/(channels|iopub|shell|stdin)|terminals/websocket)/? {
		proxy_pass https://127.0.0.1:8000;

		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header Host $host;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		# WebSocket support
		proxy_http_version 1.1;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection $connection_upgrade;

    }

	# Managing requests to verify letsencrypt host
    location ~ /.well-known {
		allow all;
    }


}
```

`nginx` will now be the front facing element of JupyterHub on `443` which means it is also free to bind other servers, like `NO_HUB.DOMAIN.TLD` to the same port on the same machine and network interface. In fact, one can simply use the same server blocks as above for `NO_HUB` and simply add line for the root directory of the site as well as the applicable location call:

```bash
server {
	listen 80;
	server_name NO_HUB.DOMAIN.TLD;

	# Tell all requests to port 80 to be 302 redirected to HTTPS
	return 302 https://$host$request_uri;
}

server {
	listen 443;
	ssl on;

	# INSERT OTHER SSL PARAMETERS HERE AS ABOVE

	# Set the appropriate root directory
	root /var/www/html

	# Set URI handling
	location / {
		try_files $uri $uri/ =404;
	}

	# Managing requests to verify letsencrypt host
    location ~ /.well-known {
		allow all;
    }

}
```

Now just restart `nginx`, restart the JupyterHub, and enjoy accessing https://HUB.DOMAIN.TLD while serving other content securely on https://NO_HUB.DOMAIN.TLD.
