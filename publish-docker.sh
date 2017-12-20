#!/bin/bash
VERSION=`cat .version`
docker build --squash -t "xalgorithms/jupyterhub:latest" -t "xalgorithms/jupyterhub:$VERSION" -f "Dockerfile" .
docker push "xalgorithms/jupyterhub:latest"
docker push "xalgorithms/jupyterhub:$VERSION"

