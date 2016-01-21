# A base docker image that includes juptyerhub and IPython master
#
# Build your own derivative images starting with
#
# FROM jupyter/jupyterhub:latest
#

FROM debian:jessie

MAINTAINER Jupyter Project <jupyter@googlegroups.com>

# install nodejs
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -y update && apt-get -y upgrade && apt-get -y install npm nodejs nodejs-legacy wget

# install Python with conda
RUN wget -q https://repo.continuum.io/miniconda/Miniconda3-3.9.1-Linux-x86_64.sh -O /tmp/miniconda.sh  && \
    bash /tmp/miniconda.sh -f -b -p /opt/conda && \
    /opt/conda/bin/conda install --yes python=3.5 sqlalchemy tornado jinja2 traitlets requests pip && \
    rm /tmp/miniconda.sh
ENV PATH=/opt/conda/bin:$PATH

# install any pip dependencies not already installed by conda
ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# install js dependencies
RUN npm install -g configurable-http-proxy

WORKDIR /srv/
ADD . /srv/jupyterhub
WORKDIR /srv/jupyterhub/

RUN pip install .

WORKDIR /srv/jupyterhub/

# Derivative containers should add jupyterhub config,
# which will be used when starting the application.

EXPOSE 8000

ONBUILD ADD jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
