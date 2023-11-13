# JupyterHub onbuild image

If you base a Dockerfile on this image:

    FROM quay.io/jupyterhub/jupyterhub-onbuild:4.0.2
    ...

then your `jupyterhub_config.py` adjacent to your Dockerfile will be loaded into the image and used by JupyterHub.

> [!NOTE]
> Inherit from a tag that corresponds to the version of JupyterHub you want to use.
> See our [Quay.io page](https://quay.io/repository/jupyterhub/jupyterhub?tab=tags) for the list of
> available tags.

> [!WARNING]
> Automatically loading the `jupyterhub_config.py` file was the default behavior of the `quay.io/jupyterhub/jupyterhub`
> image prior to `0.6`.
