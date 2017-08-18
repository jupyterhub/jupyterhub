# Build as jupyterhub/singleuser
# Run with the DockerSpawner in JupyterHub

ARG BASE_IMAGE=jupyter/base-notebook
FROM $BASE_IMAGE
MAINTAINER Project Jupyter <jupyter@googlegroups.com>

ADD install_jupyterhub /tmp/install_jupyterhub
ARG JUPYTERHUB_VERSION=master
RUN python3 /tmp/install_jupyterhub
