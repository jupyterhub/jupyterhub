# Build as jupyterhub/singleuser
# Run with the DockerSpawner in JupyterHub

ARG BASE_IMAGE=jupyter/base-notebook
FROM $BASE_IMAGE
MAINTAINER Project Jupyter <jupyter@googlegroups.com>

ADD install_jupyterhub /tmp/install_jupyterhub
ARG JUPYTERHUB_VERSION=main
# install pinned jupyterhub and ensure jupyterlab is installed
RUN python3 /tmp/install_jupyterhub && \
    python3 -m pip install jupyterlab
