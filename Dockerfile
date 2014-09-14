FROM node:0.10.31

MAINTAINER IPython Project <ipython-dev@scipy.org>

# System pre-requisites
RUN apt-get update
RUN apt-get -y install python3-dev python3-pip python3
RUN npm install -g bower less

# Add sources for jupyterhub
ADD . /srv/jupyterhub
WORKDIR /srv/jupyterhub

# Install the configurable http proxy, used by Jupyter Hub
RUN npm install -g jupyter/configurable-http-proxy

# Install JupyterHub!
RUN bower install --allow-root
RUN pip3 install .

# Default port for JupyterHub
EXPOSE 8000

CMD ["python", "-m", "jupyterhub"]

