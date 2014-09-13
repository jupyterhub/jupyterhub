FROM node:0.10.31

RUN npm install -g jupyter/configurable-http-proxy
RUN npm install -g bower less

ADD . /srv/jupyterhub

WORKDIR /srv/jupyterhub

RUN apt-get update
RUN apt-get -y install python-dev python-pip

RUN pip install .

EXPOSE 8000

CMD ["jupyterhub"]
