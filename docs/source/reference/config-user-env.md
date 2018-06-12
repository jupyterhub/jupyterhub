# Configuring user environments

Deploying JupyterHub means you are providing Jupyter notebook environments for multiple users.
Often, this includes a desire to configure the user environment in some way.
Since the `jupyterhub-singleuser` server extends the standard Jupyter notebook server, most configuration and documentation that applies to Jupyter applies to the single-user environments.
Configuration of user environments typically does not occur through JupyterHub itself,
but rather through system-wide configuration of Jupyter,
which is inherited by `jupyterhub-singleuser`.

**Tip:** When searching for configuration tips for JupyterHub,
try removing JupyterHub from your search because there are a lot more people out there configuring Jupyter than JupyterHub and the configuration is the same.


## Installing packages

To make packages available to users,
This generally means installing packages system-wide or in a shared environment.
It should always be in the same environment that `jupyterhub-singleuser` itself is installed in,
and must be readable and executable by your users.
If you want users to be able to install additional packages,
it must also be *writable* by your users.

If you are using a standard system Python install,
this means using:

```bash
sudo python3 -m pip install numpy
```

to install numpy in the default system Python 3 environment (typically `/usr/local`).

You can also use conda to install packages, but you should make sure that the conda environment has appropriate permissions for users to be able to run Python code in the env.


## Configuring Jupyter and IPython

[Jupyter](https://jupyter-notebook.readthedocs.io/en/stable/config_overview.html)
and [IPython](https://ipython.readthedocs.io/en/stable/development/config.html)
have their own configuration systems.
As an administrator, it is a good idea to avoid creating files in users' home directories.
Jupyter and IPython support "system-wide" locations for configuration,
which is the logical place to put global configuration that you want to affect all users.

The typical locations for these config files are system-wide in `/etc/{jupyter|ipython}`
or env-wide in `{sys.prefix}/etc/{jupyter|ipython}`.

For example, to enable the `cython` IPython extension for all of your users,
create the file `/etc/ipython/ipython_config.py`:

```python
c.InteractiveShellApp.extensions.append("cython")
```

To enable Jupyter notebook's internal idle-shutdown behavior
(requires notebook ≥ 5.4),
in `/etc/jupyter/jupyter_notebook_config.py`:

```python
# shutdown the server after no activity for an hour
c.NotebookApp.shutdown_no_activity_timeout = 60 * 60
# shutdown kernels after no activity for 20 minutes
c.MappingKernelManager.cull_idle_timeout = 20 * 60
# check for idle kernels every two minutes
c.MappingKernelManager.cull_interval = 2 * 60
```


## Installing kernelspecs

You may have multiple Jupyter kernels installed and want to make sure that they are available to all of your users.
This means installing kernelspecs either system-wide (e.g. in /usr/local/)
or in the `sys.prefix` of JupyterHub itself.

Jupyter kernelspec installation is system wide by default,
but some kernels may default to installing kernelspecs in your home directory.
These will need to be moved system-wide to ensure that they are accessible.
You can see where your kernelspecs are with:

```bash
jupyter kernelspec list
```

Assuming I have a Python 2 and Python 3 environment that I want to make sure are available, I can install their specs system-wide (in /usr/local) with:

```bash
/path/to/python3 -m IPython kernel install --prefix=/usr/local
/path/to/python2 -m IPython kernel install --prefix=/usr/local
```


## Containers vs multi-user hosts

There are two broad categories of user environments that depend on what Spawner you choose,
and how you configure user environments can differ a bit depending on what you are using.
The first category is a shared system where each user has an account and a home directory and a real system user.
In this example, shared configuration and installation must be in a 'system-wide' location, such as `/etc/` or `/usr/local` or a custom prefix
such as `/opt/conda`.

In container-based Spawners (e.g. KubeSpawner or DockerSpawner),
the 'system-wide' environment is really the image you are using for users.

In both cases, you want to avoid putting configuration in user home directories
because users can change those,
and home directories typically persist once they are created,
so difficult for admins to update later.
