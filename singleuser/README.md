# jupyterhub/singleuser

Built from the `jupyter/base-notebook` base image.

This image contains a single user notebook server for use with
[JupyterHub](https://github.com/jupyterhub/jupyterhub). In particular, it is meant
to be used with the
[DockerSpawner](https://github.com/jupyterhub/dockerspawner/blob/master/dockerspawner/dockerspawner.py)
class to launch user notebook servers within docker containers.

The only thing this image accomplishes is pinning the jupyterhub version on top of base-notebook.
In most cases, one of the Jupyter [docker-stacks](https://github.com/jupyter/docker-stacks) is a better choice.
You will just have to make sure that you have the right version of JupyterHub installed in your image,
which can usually be accomplished with one line:

```Dockerfile
FROM jupyter/base-notebook:5ded1de07260
RUN pip3 install jupyterhub==0.7.2
```

The dockerfile that builds this image exposes `BASE_IMAGE` and `JUPYTERHUB_VERSION` as build args, so you can do:

    docker build -t singleuser \
      --build-arg BASE_IMAGE=jupyter/scipy-notebook \
      --build-arg JUPYTERHUB_VERSION=0.8.0 \
      .

in this directory to get a new image `singleuser` that is based on `jupyter/scipy-notebook` with JupyterHub 0.8, for example.

This particular image runs as the `jovyan` user, with home directory at `/home/jovyan`.

## Note on persistence

This home directory, `/home/jovyan`, is *not* persistent by default,
so some configuration is required unless the directory is to be used
with temporary or demonstration JupyterHub deployments.
