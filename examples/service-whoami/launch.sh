# make some API tokens, one for the proxy, one for the service
export CONFIGPROXY_AUTH_TOKEN=`openssl rand -hex 32`

# start JupyterHub
jupyterhub --no-ssl --ip=127.0.0.1
