# Build as jupyterhub/singleuser
# Run with the DockerSpawner in JupyterHub

ARG BASE_IMAGE=jupyter/base-notebook
FROM $BASE_IMAGE
MAINTAINER Project Jupyter <jupyter@googlegroups.com>

ADD install_jupyterhub /tmp/install_jupyterhub
ARG JUPYTERHUB_VERSION=master
# install pinned jupyterhub and ensure notebook is installed
RUN python3 /tmp/install_jupyterhub && \
    python3 -m pip install notebook
