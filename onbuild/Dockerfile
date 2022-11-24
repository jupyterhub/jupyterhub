# JupyterHub Dockerfile that loads your jupyterhub_config.py
#
# Adds ONBUILD step to jupyter/jupyterhub to load your jupyterhub_config.py into the image
#
# Derivative images must have jupyterhub_config.py next to the Dockerfile.

ARG BASE_IMAGE=jupyterhub/jupyterhub:latest
FROM $BASE_IMAGE

ONBUILD COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py

CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
