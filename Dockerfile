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

######################################################################
# This Dockerfile uses multi-stage builds with optimisations to build
# the JupyterHub wheel on the native architecture only
# https://www.docker.com/blog/faster-multi-platform-builds-dockerfile-cross-compilation-guide/

ARG BASE_IMAGE=ubuntu:22.04


######################################################################
# The JupyterHub wheel is pure Python so can be built for any platform
# on the native architecture (avoiding QEMU emulation)
FROM --platform=${BUILDPLATFORM:-linux/amd64} $BASE_IMAGE AS jupyterhub-builder

ENV DEBIAN_FRONTEND=noninteractive

# Don't clear apt cache, and don't combine RUN commands, so that cached layers can
# be reused in other stages

RUN apt-get update -qq \
 && apt-get install -yqq --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    locales \
    python3-dev \
    python3-pip \
    python3-pycurl \
    python3-venv \
 && python3 -m pip install --no-cache-dir --upgrade setuptools pip build wheel
# Ubuntu 22.04 comes with Nodejs 12 which is too old for building JupyterHub JS
# It's fine at runtime though (used only by configurable-http-proxy)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
 && apt-get install -yqq --no-install-recommends \
    nodejs \
 && npm install --global yarn

WORKDIR /src/jupyterhub
# copy everything except whats in .dockerignore, its a
# compromise between needing to rebuild and maintaining
# what needs to be part of the build
COPY . .

ARG PIP_CACHE_DIR=/tmp/pip-cache
RUN --mount=type=cache,target=${PIP_CACHE_DIR} \
    python3 -m build --wheel


######################################################################
# All other wheels required by JupyterHub, some are platform specific
FROM $BASE_IMAGE AS wheel-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq \
 && apt-get install -yqq --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    locales \
    python3-dev \
    python3-pip \
    python3-pycurl \
    python3-venv \
 && python3 -m pip install --no-cache-dir --upgrade setuptools pip build wheel

WORKDIR /src/jupyterhub

COPY --from=jupyterhub-builder /src/jupyterhub/dist/*.whl /src/jupyterhub/dist/
ARG PIP_CACHE_DIR=/tmp/pip-cache
RUN --mount=type=cache,target=${PIP_CACHE_DIR} \
    python3 -m pip wheel --wheel-dir wheelhouse dist/*.whl


######################################################################
# The final JupyterHub image, platform specific
FROM $BASE_IMAGE AS jupyterhub

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

RUN apt-get update -qq \
 && apt-get install -yqq --no-install-recommends \
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
# install the wheels we built in the previous stage
RUN --mount=type=cache,from=wheel-builder,source=/src/jupyterhub/wheelhouse,target=/tmp/wheelhouse \
    # always make sure pip is up to date!
    python3 -m pip install --no-compile --no-cache-dir --upgrade setuptools pip \
 && python3 -m pip install --no-compile --no-cache-dir /tmp/wheelhouse/*

CMD ["jupyterhub"]
