# An incomplete base docker image for running JupyterHub
#
# Build your own derivative images starting with
#
# FROM jupyter/jupyterhub:latest
#
# And put your jupyterhub_config.py in /srv/jupyterhub/jupyterhub_config.py.
#
# Or you can create your jupyterhub config and database on the host machine, and mount it with:
#
# docker run -v $PWD:/srv/jupyterhub -t jupyter/jupyterhub
#
# If you base on jupyter/jupyterhub-onbuild
# your jupyterhub_config.py will be added automatically
# from your docker directory.

FROM debian:jessie
MAINTAINER Jupyter Project <jupyter@googlegroups.com>

# install nodejs, utf8 locale
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get -y install npm nodejs nodejs-legacy wget locales git &&\
    /usr/sbin/update-locale LANG=C.UTF-8 && \
    locale-gen C.UTF-8 && \
    apt-get remove -y locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
ENV LANG C.UTF-8

# install Python with conda
RUN wget -q https://repo.continuum.io/miniconda/Miniconda3-4.0.5-Linux-x86_64.sh -O /tmp/miniconda.sh  && \
    echo 'a7bcd0425d8b6688753946b59681572f63c2241aed77bf0ec6de4c5edc5ceeac */tmp/miniconda.sh' | shasum -a 256 -c - && \
    bash /tmp/miniconda.sh -f -b -p /opt/conda && \
    /opt/conda/bin/conda install --yes python=3.5 sqlalchemy tornado jinja2 traitlets requests pip && \
    /opt/conda/bin/pip install --upgrade pip && \
    rm /tmp/miniconda.sh
ENV PATH=/opt/conda/bin:$PATH

# install js dependencies
RUN npm install -g configurable-http-proxy && rm -rf ~/.npm

ADD . /src/jupyterhub
WORKDIR /src/jupyterhub

RUN python setup.py js && pip install . && \
    rm -rf $PWD ~/.cache ~/.npm

RUN mkdir -p /srv/jupyterhub/
WORKDIR /srv/jupyterhub/
EXPOSE 8000

LABEL org.jupyter.service="jupyterhub"

CMD ["jupyterhub"]
