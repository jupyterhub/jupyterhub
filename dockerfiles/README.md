Dockerfile.base contains base image for jupyterhub. It does not work independently. To make it work it needs

1. A running configurable-http-proxy, whose API is accessible. 
2. A jupyterhub_config file.
3. Authentication and other libraries required by the specific jupyterhub_config file.

An example on how to use this base image is in docker-compose.yaml. You can run it by doing
```
docker-compose up
```
to run it.
