#!/bin/bash -l
set -e

# these must match the values in jupyterhub_config.py
export JUPYTERHUB_API_TOKEN=c3a29e5d386fd7c9aa1e8fe9d41c282ec8b
export JUPYTERHUB_SERVICE_URL=http://127.0.0.1:9999
export JUPYTERHUB_SERVICE_NAME=shared-notebook
export JUPYTERHUB_SERVICE_PREFIX="/services/${JUPYTERHUB_SERVICE_NAME}/"
export JUPYTERHUB_CLIENT_ID="service-${JUPYTERHUB_SERVICE_NAME}"

jupyterhub-singleuser
