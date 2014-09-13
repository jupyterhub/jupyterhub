FROM node:0.10.31

MAINTAINER IPython Project <ipython-dev@scipy.org>

# System pre-requisites
RUN apt-get update
RUN apt-get -y install python-dev python-pip
RUN npm install -g bower less

# Add sources for jupyterhub
ADD . /srv/jupyterhub
WORKDIR /srv/jupyterhub

# Install the configurable http proxy, used by Jupyter Hub
RUN npm install -g jupyter/configurable-http-proxy

# Install JupyterHub!
RUN pip install .

# Default port for JupyterHub
EXPOSE 8000

CMD ["jupyterhub"]
