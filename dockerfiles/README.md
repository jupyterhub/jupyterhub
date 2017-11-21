## What is Dockerfile.base
Dockerfile.base contains base image for jupyterhub. It does not work independently. To make it work it needs

## How to use it?

1. A running configurable-http-proxy, whose API is accessible. 
2. A jupyterhub_config file.
3. Authentication and other libraries required by the specific jupyterhub_config file.

## Example
* An example of how to use this base image and add customizations is in Dockerfile.config.
* A complete example on how to use this base image and config image is in docker-compose.yaml. To test it you can run 
```
docker-compose up
```

## Reference
* Build an image from Dockerfile.base and push it to a docker registry (e.g https://hub.docker.com/r/ankitml/jupyterhub-base/)
* Build the config image from Dockerfile.config and push it to a docker registry (e.g https://hub.docker.com/r/ankitml/jupyterhub-config)
* Use this image in your cluster either from docker-compose example or kubernetes tutorial.


