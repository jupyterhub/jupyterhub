# JupyterHub Dockerfile that loads your jupyterhub_config.py
#
# Adds ONBUILD step to jupyter/jupyterhub to load your juptyerhub_config.py into the image
#
# Derivative images must have jupyterhub_config.py next to the Dockerfile.

FROM jupyterhub/jupyterhub

ONBUILD ADD jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py

CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
