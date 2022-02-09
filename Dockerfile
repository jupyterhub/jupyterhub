# QABE Docker image for running JupyterHub
#
# Note that we should install CUDA and CuDNN images from cuda/cudnn

#========================================================#
#          Base Builder installation (Client)            #
#========================================================#
ARG BASE_IMAGE=nvidia/cuda:11.0.3-devel-ubuntu20.04
FROM $BASE_IMAGE AS builder

USER root

ENV CUDNN_VERSION 8.0.5.39

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcudnn8=$CUDNN_VERSION-1+cuda11.0 \
    libcudnn8-dev=$CUDNN_VERSION-1+cuda11.0 \
    && apt-mark hold libcudnn8 && \
    rm -rf /var/lib/apt/lists/*

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -yq --no-install-recommends \
    build-essential \
    ca-certificates \
    locales \
    python3-dev \
    python3-pip \
    python3-pycurl \
    nodejs \
    npm \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade setuptools pip wheel

# copy everything except whats in .dockerignore, its a
# compromise between needing to rebuild and maintaining
# what needs to be part of the build
COPY . /src/jupyterhub/
WORKDIR /src/jupyterhub

# Build client component packages (they will be copied into ./share and
# packaged with the built wheel.)
RUN python3 setup.py bdist_wheel
RUN python3 -m pip wheel --wheel-dir wheelhouse dist/*.whl

#========================================================#
#         Final Image (JupyterHub) Installation          #
#========================================================#
FROM $BASE_IMAGE

USER root

ENV DEBIAN_FRONTEND=noninteractive

ENV CUDNN_VERSION 8.0.5.39

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcudnn8=$CUDNN_VERSION-1+cuda11.0 \
    libcudnn8-dev=$CUDNN_VERSION-1+cuda11.0 \
    && apt-mark hold libcudnn8 && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update \
 && apt-get install -yq --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    gnupg \
    locales \
    python3-pip \
    python3-pycurl \
    nodejs \
    npm \
    sudo \
    vim \
    r-base \
    libzmq3-dev libcurl4-openssl-dev libssl-dev jupyter-core jupyter-client \
    zlib1g-dev \
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
COPY --from=builder /src/jupyterhub/wheelhouse /tmp/wheelhouse
RUN python3 -m pip install --no-cache /tmp/wheelhouse/*

# To use Jupyter Lab, we should install jupyterlab
RUN python3 -m pip install jupyterlab

RUN mkdir -p /srv/jupyterhub/
WORKDIR /srv/jupyterhub/
RUN mkdir /workspace

# Install R kernel
COPY IRkernel.r IRkernel.r
COPY requirements.txt requirements.txt
COPY package_listup.csv package_listup.csv

# RUN Rscript IRkernel.r
RUN Rscript IRkernel.r

# Preserve Configuration
COPY jupyterhub_config.py jupyterhub_config.py

EXPOSE 8000

CMD ["jupyterhub"]
