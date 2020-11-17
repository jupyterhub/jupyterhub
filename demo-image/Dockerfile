# Demo JupyterHub Docker image
#
# This should only be used for demo or testing and not as a base image to build on.
#
# It includes the notebook package and it uses the DummyAuthenticator and the SimpleLocalProcessSpawner.
ARG BASE_IMAGE=jupyterhub/jupyterhub-onbuild
FROM ${BASE_IMAGE}

# Install the notebook package
RUN python3 -m pip install notebook

# Create a demo user
RUN useradd --create-home demo
RUN chown demo .

USER demo
