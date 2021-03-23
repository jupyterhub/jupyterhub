FROM alpine:3.13
ENV LANG=en_US.UTF-8
RUN apk add --no-cache \
        python3 \
        py3-pip \
        py3-ruamel.yaml \
        py3-cryptography \
        py3-sqlalchemy

ARG JUPYTERHUB_VERSION=1.3.0
RUN pip3 install --no-cache jupyterhub==${JUPYTERHUB_VERSION}

USER nobody
CMD ["jupyterhub"]
