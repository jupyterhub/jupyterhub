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

ARG BASE_IMAGE=ubuntu:22.04


######################################################################
# A base image for building wheels
FROM --platform=${TARGETPLATFORM:-linux/amd64} $BASE_IMAGE AS base-builder

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /src/jupyterhub

# Ubuntu 22.04 comes with Nodejs 12 which is too old for building JupyterHub JS
# It's fine at runtime though (used only by configurable-http-proxy)
RUN apt update -q \
 && apt install -yq --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    locales \
    python3-dev \
    python3-pip \
    python3-pycurl \
    python3-venv \
 && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
 && apt-get install -yq --no-install-recommends \
    nodejs \
 && apt clean \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --no-cache-dir --upgrade setuptools pip build wheel \
 && npm install --global yarn

# copy everything except whats in .dockerignore, its a
# compromise between needing to rebuild and maintaining
# what needs to be part of the build
COPY . .


######################################################################
# The JupyterHub wheel is pure Python so can be built once on any architecture
# TODO: re-enable BUILDPLATFORM instead of forcing to linux/amd64
#FROM --platform=${BUILDPLATFORM:-linux/amd64} base-builder AS jupyterhub-builder
FROM --platform=linux/amd64 base-builder AS jupyterhub-builder

RUN echo "BUILDPLATFORM=${BUILDPLATFORM} TARGETPLATFORM=${TARGETPLATFORM}"

ARG PIP_CACHE_DIR=/tmp/pip-cache
RUN --mount=type=cache,target=${PIP_CACHE_DIR} \
    python3 -m build --wheel


######################################################################
# All other wheels required by JupyterHub, some are platform specific
FROM --platform=${TARGETPLATFORM:-linux/amd64} base-builder AS builder

COPY --from=jupyterhub-builder /src/jupyterhub/dist/*.whl /src/jupyterhub/dist/
ARG PIP_CACHE_DIR=/tmp/pip-cache
RUN --mount=type=cache,target=${PIP_CACHE_DIR} \
    python3 -m build --wheel \
 && python3 -m pip wheel --wheel-dir wheelhouse dist/*.whl


######################################################################
# The final JupyterHub image, platform specific
FROM --platform=${TARGETPLATFORM:-linux/amd64} $BASE_IMAGE

ENV DEBIAN_FRONTEND=noninteractive \
    SHELL=/bin/bash \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

LABEL maintainer="Jupyter Project <jupyter@googlegroups.com>"
LABEL org.jupyter.service="jupyterhub"

WORKDIR /srv/jupyterhub

RUN apt update -q \
 && apt install -yq --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    locales \
    python-is-python3 \
    python3-pip \
    python3-pycurl \
    nodejs \
    npm \
 && locale-gen $LC_ALL \
 && npm install -g configurable-http-proxy@^4.2.0 \
 # clean cache and logs
 && rm -rf /var/lib/apt/lists/* /var/log/* /var/tmp/* ~/.npm
# install the wheels we built in the first stage
RUN --mount=type=cache,from=builder,source=/src/jupyterhub/wheelhouse,target=/tmp/wheelhouse \
    # always make sure pip is up to date!
    python3 -m pip install --no-compile --no-cache-dir --upgrade setuptools pip \
 && python3 -m pip install --no-compile --no-cache-dir /tmp/wheelhouse/*

CMD ["jupyterhub"]
