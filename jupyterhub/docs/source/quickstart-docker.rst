Using Docker
============

.. important::

   We highly recommend following the `Zero to JupyterHub`_ tutorial for
   installing JupyterHub.

Alternate installation using Docker
-----------------------------------

A ready to go `docker image <https://hub.docker.com/r/jupyterhub/jupyterhub/>`_
gives a straightforward deployment of JupyterHub.

.. note::

    This ``jupyterhub/jupyterhub`` docker image is only an image for running
    the Hub service itself. It does not provide the other Jupyter components,
    such as Notebook installation, which are needed by the single-user servers.
    To run the single-user servers, which may be on the same system as the Hub or
    not, Jupyter Notebook version 4 or greater must be installed.

Starting JupyterHub with docker
-------------------------------

The JupyterHub docker image can be started with the following command::

    docker run -d -p 8000:8000 --name jupyterhub jupyterhub/jupyterhub jupyterhub

This command will create a container named ``jupyterhub`` that you can
**stop and resume** with ``docker stop/start``.

The Hub service will be listening on all interfaces at port 8000, which makes
this a good choice for **testing JupyterHub on your desktop or laptop**.

If you want to run docker on a computer that has a public IP then you should
(as in MUST) **secure it with ssl** by adding ssl options to your docker
configuration or using a ssl enabled proxy.

`Mounting volumes <https://docs.docker.com/engine/admin/volumes/volumes/>`_
will allow you to store data outside the docker image (host system) so it will
be persistent, even when you start a new image.

The command ``docker exec -it jupyterhub bash`` will spawn a root shell in your
docker container. You can use the root shell to **create system users in the container**.
These accounts will be used for authentication in JupyterHub's default
configuration.

.. _Zero to JupyterHub: https://zero-to-jupyterhub.readthedocs.io/en/latest/
