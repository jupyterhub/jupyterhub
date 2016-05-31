# make some API tokens, one for the proxy, one for the service
export CONFIGPROXY_AUTH_TOKEN=`openssl rand -hex 32`
export WHOAMI_HUB_API_TOKEN=`openssl rand -hex 32`

# start JupyterHub
jupyterhub --no-ssl --ip=127.0.0.1 &

# give JupyterHub a moment to start
sleep 2

# start the whoami service as /hub/whoami
python whoami.py
