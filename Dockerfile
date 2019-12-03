# An incomplete base Docker image for running JupyterHub
#
# Add your configuration to create a complete derivative Docker image.
#
# Include your configuration settings by starting with one of two options:
#
# Option 1:
#
# FROM jupyterhub/jupyterhub:latest
#
# And put your configuration file jupyterhub_config.py in /srv/jupyterhub/jupyterhub_config.py.
#
# Option 2:
#
# Or you can create your jupyterhub config and database on the host machine, and mount it with:
#
# docker run -v $PWD:/srv/jupyterhub -t jupyterhub/jupyterhub
#
# NOTE
# If you base on jupyterhub/jupyterhub-onbuild
# your jupyterhub_config.py will be added automatically
# from your docker directory.

# https://github.com/tianon/docker-brew-ubuntu-core/commit/3c462555392cb188830b7c91e29311b5fad90cfe
ARG BASE_IMAGE=ubuntu:bionic-20190612@sha256:9b1702dcfe32c873a770a32cfd306dd7fc1c4fd134adfb783db68defc8894b3c
FROM $BASE_IMAGE

USER root

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update \
 && apt-get install -yq --no-install-recommends \
    ca-certificates \
    locales \
    python3-dev \
    python3-pip \
    python3-pycurl \
    nodejs \
    npm \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# copy only what we need to avoid unnecessary rebuilds
COPY README.md setup.py requirements.txt pyproject.toml package.json /src/jupyterhub/
COPY jupyterhub/ /src/jupyterhub/jupyterhub
COPY share/ /src/jupyterhub/share

WORKDIR /src/jupyterhub
RUN python3 -m pip install --upgrade setuptools pip wheel
RUN python3 -m pip wheel -v --wheel-dir wheelhouse .


FROM $BASE_IMAGE

USER root

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -yq --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    locales \
    python3-pip \
    python3-pycurl \
    nodejs \
    npm \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

ENV SHELL=/bin/bash \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8

RUN  locale-gen $LC_ALL

# always make sure pip is up to date!
RUN python3 -m pip install --no-cache --upgrade setuptools pip

RUN npm install -g configurable-http-proxy@^4.2.0 \
 && rm -rf ~/.npm

# install the wheels we built in the first stage
COPY --from=0 /src/jupyterhub/wheelhouse /tmp/wheelhouse
RUN python3 -m pip install --no-cache /tmp/wheelhouse/*

RUN mkdir -p /srv/jupyterhub/
WORKDIR /srv/jupyterhub/

EXPOSE 8000

LABEL maintainer="Jupyter Project <jupyter@googlegroups.com>"
LABEL org.jupyter.service="jupyterhub"

CMD ["jupyterhub"]
