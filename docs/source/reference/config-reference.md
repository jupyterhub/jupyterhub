# Configuration Reference

:::{important}
Make sure the version of JupyterHub for this documentation matches your
installation version, as the output of this command may change between versions.
:::

## JupyterHub configuration

As explained in the [Configuration Basics](generate-config-file)
section, the `jupyterhub_config.py` can be automatically generated via

> ```bash
> jupyterhub --generate-config
> ```

Most of this information is available in a nicer format in:

- [](./api/app.md)
- [](./api/auth.md)
- [](./api/spawner.md)

The following contains the output of that command for reference.

```{eval-rst}
.. jupyterhub-generate-config::
```

## JupyterHub help command output

This section contains the output of the command `jupyterhub --help-all`.

```{eval-rst}
.. jupyterhub-help-all::
```
