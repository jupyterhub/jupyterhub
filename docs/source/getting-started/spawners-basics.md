# Spawners and single-user notebook servers

Since the single-user server is an instance of `jupyter notebook`, an entire separate
multi-process application, there are many aspect of that server can configure, and a lot of ways
to express that configuration.

At the JupyterHub level, you can set some values on the Spawner. The simplest of these is
`Spawner.notebook_dir`, which lets you set the root directory for a user's server. This root
notebook directory is the highest level directory users will be able to access in the notebook
dashboard. In this example, the root notebook directory is set to `~/notebooks`, where `~` is
expanded to the user's home directory.

```python
c.Spawner.notebook_dir = '~/notebooks'
```

You can also specify extra command-line arguments to the notebook server with:

```python
c.Spawner.args = ['--debug', '--profile=PHYS131']
```

This could be used to set the users default page for the single user server:

```python
c.Spawner.args = ['--NotebookApp.default_url=/notebooks/Welcome.ipynb']
```

Since the single-user server extends the notebook server application,
it still loads configuration from the `jupyter_notebook_config.py` config file.
Each user may have one of these files in `$HOME/.jupyter/`.
Jupyter also supports loading system-wide config files from `/etc/jupyter/`,
which is the place to put configuration that you want to affect all of your users.
