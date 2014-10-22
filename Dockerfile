# A base docker image that includes juptyerhub and IPython master
#
# Build your own derivative images starting with
#
# FROM jupyter/jupyterhub:latest
#

FROM ipython/ipython

MAINTAINER Jupyter Project <ipython-dev@scipy.org>

# install js dependencies
RUN npm install -g bower less
RUN npm install -g jupyter/configurable-http-proxy

RUN mkdir -p /srv/

# install jupyterhub
WORKDIR /srv/
ADD . /srv/jupyterhub
WORKDIR /srv/jupyterhub/

RUN pip3 install -r requirements.txt
RUN pip3 install .

WORKDIR /srv/jupyterhub/

# Derivative containers should add jupyterhub config,
# which will be used when starting the application.

EXPOSE 8000

ONBUILD ADD jupyter_hub_config.py /srv/jupyterhub/jupyter_hub_config.py
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyter_hub_config.py"]