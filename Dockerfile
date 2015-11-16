# A base docker image that includes juptyerhub and IPython master
#
# Build your own derivative images starting with
#
# FROM jupyter/jupyterhub:latest
#

FROM jupyter/notebook

MAINTAINER Jupyter Project <jupyter@googlegroups.com>

ENV DEBIAN_FRONTEND noninteractive

# Update and upgrade apt-get for the latest packages and security updates	
RUN apt-get update && apt-get -y upgrade

RUN apt-get -y install npm nodejs
RUN ln -s /usr/bin/nodejs /usr/bin/node

# install js dependencies
RUN npm install -g configurable-http-proxy

RUN mkdir -p /srv/

# install jupyterhub
ADD requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /srv/
ADD . /srv/jupyterhub
WORKDIR /srv/jupyterhub/

RUN pip3 install .

WORKDIR /srv/jupyterhub/

# Derivative containers should add jupyterhub config,
# which will be used when starting the application.

EXPOSE 8000

ONBUILD ADD jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
