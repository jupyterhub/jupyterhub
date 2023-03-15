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
FROM $BASE_IMAGE AS builder

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /src/jupyterhub

RUN apt-get update \
 && apt-get install -yq --no-install-recommends \
    build-essential \
    ca-certificates \
    locales \
    python3-dev \
    python3-pip \
    python3-pycurl \
    python3-venv \
    nodejs \
    npm \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --no-cache-dir --upgrade setuptools pip build wheel \
 && npm install --global yarn
# copy everything except whats in .dockerignore, its a
# compromise between needing to rebuild and maintaining
# what needs to be part of the build
COPY . .
 # Build client component packages (they will be copied into ./share and
 # packaged with the built wheel.)
RUN python3 -m build --wheel \
 && python3 -m pip wheel --wheel-dir wheelhouse dist/*.whl

FROM $BASE_IMAGE
ENV DEBIAN_FRONTEND=noninteractive \
    SHELL=/bin/bash \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8

EXPOSE 8000

LABEL maintainer="Jupyter Project <jupyter@googlegroups.com>"
LABEL org.jupyter.service="jupyterhub"

WORKDIR /srv/jupyterhub

COPY --from=builder /src/jupyterhub/wheelhouse /tmp/wheelhouse

RUN apt-get update \
 && apt-get install -yq --no-install-recommends \
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
 # always make sure pip is up to date!
 && python3 -m pip install --no-cache-dir --upgrade setuptools pip \
 && npm install -g configurable-http-proxy@^4.2.0 \
 # install the wheels we built in the first stage
 && python3 -m pip install --no-cache-dir /tmp/wheelhouse/* \
 # clean cache and logs
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/log/* /var/tmp/* ~/.npm \
 && find / -type d -name '*__pycache__' -prune -exec rm -rf {} \;

CMD ["jupyterhub"]
