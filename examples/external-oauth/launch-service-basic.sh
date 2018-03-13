#!/usr/bin/env bash
# script to launch whoami-oauth-basic service
set -euo pipefail

# the service needs to know:
# 1. API token
if [[ -z "${JUPYTERHUB_API_TOKEN}" ]]; then
    echo 'set API token with export JUPYTERHUB_API_TOKEN=$(openssl rand -hex 32)'
fi

# 2. oauth client ID
export JUPYTERHUB_CLIENT_ID='whoami-oauth-client-test'
# 3. where the Hub is
export JUPYTERHUB_URL='http://127.0.0.1:8000'

# 4. where to run
export JUPYTERHUB_SERVICE_URL='http://127.0.0.1:5555'

# launch the service
exec python3 whoami-oauth-basic.py
