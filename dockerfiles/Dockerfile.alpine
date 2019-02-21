FROM python:3.6.3-alpine3.6

ARG JUPYTERHUB_VERSION=0.8.1

RUN pip3 install --no-cache jupyterhub==${JUPYTERHUB_VERSION}
ENV LANG=en_US.UTF-8

USER nobody
CMD ["jupyterhub"]
