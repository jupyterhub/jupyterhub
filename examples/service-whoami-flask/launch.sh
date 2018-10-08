export CONFIGPROXY_AUTH_TOKEN=$(openssl rand -hex 32)

# start JupyterHub
jupyterhub --ip=127.0.0.1
