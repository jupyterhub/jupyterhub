(contributing:setup)=

# Setting up a development install

## System requirements

JupyterHub can only run on macOS or Linux operating systems. If you are
using Windows, we recommend using [VirtualBox](https://virtualbox.org)
or a similar system to run [Ubuntu Linux](https://ubuntu.com) for
development.

### Install Python

JupyterHub is written in the [Python](https://python.org) programming language and
requires you have at least version {{python_min}} installed locally. If you haven’t
installed Python before, the recommended way to install it is to use
[Miniforge](https://github.com/conda-forge/miniforge#download).

### Install nodejs

[NodeJS {{node_min}}+](https://nodejs.org/en/) is required for building some JavaScript components.
`configurable-http-proxy`, the default proxy implementation for JupyterHub, is written in Javascript.
If you have not installed NodeJS before, we recommend installing it in the `miniconda` environment you set up for Python.
You can do so with `conda install nodejs`.

Many in the Jupyter community use [`nvm`](https://github.com/nvm-sh/nvm) to
managing node dependencies.

### Install git

JupyterHub uses [Git](https://git-scm.com) & [GitHub](https://github.com)
for development & collaboration. You need to [install git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) to work on
JupyterHub. We also recommend getting a free account on GitHub.com.

## Setting up a development install

When developing JupyterHub, you would need to make changes and be able to instantly view the results of the changes. To achieve that, a developer install is required.

:::{note}
This guide does not attempt to dictate _how_ development
environments should be isolated since that is a personal preference and can
be achieved in many ways, for example, `tox`, `conda`, `docker`, etc. See this
[forum thread](https://discourse.jupyter.org/t/thoughts-on-using-tox/3497) for
a more detailed discussion.
:::

1. Clone the [JupyterHub git repository](https://github.com/jupyterhub/jupyterhub)
   to your computer.

   ```bash
   git clone https://github.com/jupyterhub/jupyterhub
   cd jupyterhub
   ```

2. Make sure the `python` you installed and the `npm` you installed
   are available to you on the command line.

   ```bash
   python -V
   ```

   This should return a version number greater than or equal to {{python_min}}.

   ```bash
   npm -v
   ```

   This should return a version number greater than or equal to 5.0.

3. Install `configurable-http-proxy` (required to run and test the default JupyterHub configuration):

   ```bash
   npm install -g configurable-http-proxy
   ```

   If you get an error that says `Error: EACCES: permission denied`, you might need to prefix the command with `sudo`.
   `sudo` may be required to perform a system-wide install.
   If you do not have access to sudo, you may instead run the following commands:

   ```bash
   npm install configurable-http-proxy
   export PATH=$PATH:$(pwd)/node_modules/.bin
   ```

   The second line needs to be run every time you open a new terminal.

   If you are using conda you can instead run:

   ```bash
   conda install configurable-http-proxy
   ```

4. Install an editable version of JupyterHub and its requirements for
   development and testing. This lets you edit JupyterHub code in a text editor
   & restart the JupyterHub process to see your code changes immediately.

   ```bash
   python3 -m pip install --editable ".[test]"
   ```

5. You are now ready to start JupyterHub!

   ```bash
   jupyterhub
   ```

6. You can access JupyterHub from your browser at
   `http://localhost:8000` now.

Happy developing!

## Using DummyAuthenticator & SimpleLocalProcessSpawner

To simplify testing of JupyterHub, it is helpful to use
{class}`~jupyterhub.auth.DummyAuthenticator` instead of the default JupyterHub
authenticator and SimpleLocalProcessSpawner instead of the default spawner.

There is a sample configuration file that does this in
`testing/jupyterhub_config.py`. To launch JupyterHub with this
configuration:

```bash
jupyterhub -f testing/jupyterhub_config.py
```

The test configuration enables a few things to make testing easier:

- use 'dummy' authentication and 'simple' spawner
- named servers are enabled
- listen only on localhost
- 'admin' is an admin user, if you want to test the admin page
- disable caching of static files

The default JupyterHub [authenticator](PAMAuthenticator)
& [spawner](LocalProcessSpawner)
require your system to have user accounts for each user you want to log in to
JupyterHub as.

DummyAuthenticator allows you to log in with any username & password,
while SimpleLocalProcessSpawner allows you to start servers without having to
create a Unix user for each JupyterHub user. Together, these make it
much easier to test JupyterHub.

Tip: If you are working on parts of JupyterHub that are common to all
authenticators & spawners, we recommend using both DummyAuthenticator &
SimpleLocalProcessSpawner. If you are working on just authenticator-related
parts, use only SimpleLocalProcessSpawner. Similarly, if you are working on
just spawner-related parts, use only DummyAuthenticator.

## Building frontend components

The testing configuration file also disables caching of static files,
which allows you to edit and rebuild these files without restarting JupyterHub.

If you are working on the admin react page, which is in the `jsx` directory, you can run:

```bash
cd jsx
npm install
npm run build:watch
```

to continuously rebuild the admin page, requiring only a refresh of the page.

If you are working on the frontend SCSS files, you can run the same `build:watch` command
in the _top level_ directory of the repo:

```bash
npm install
npm run build:watch
```

## Troubleshooting

This section lists common ways setting up your development environment may
fail, and how to fix them. Please add to the list if you encounter yet
another way it can fail!

### `lessc` not found

If the `python3 -m pip install --editable .` command fails and complains about
`lessc` being unavailable, you may need to explicitly install some
additional JavaScript dependencies:

```bash
npm install
```

This will fetch client-side JavaScript dependencies necessary to compile
CSS.

You may also need to manually update JavaScript and CSS after some
development updates, with:

```bash
python3 setup.py js    # fetch updated client-side js
python3 setup.py css   # recompile CSS from LESS sources
python3 setup.py jsx   # build React admin app
```

### Failed to bind XXX to `http://127.0.0.1:<port>/<path>`

This error can happen when there's already an application or a service using this
port.

Use the following command to find out which service is using this port.

```bash
lsof -P -i TCP:<port> -sTCP:LISTEN
```

If nothing shows up, it likely means there's a system service that uses it but
your current user cannot list it. Reuse the same command with sudo.

```bash
sudo lsof -P -i TCP:<port> -sTCP:LISTEN
```

Depending on the result of the above commands, the most simple solution is to
configure JupyterHub to use a different port for the service that is failing.

As an example, the following is a frequently seen issue:

`Failed to bind hub to http://127.0.0.1:8081/hub/`

Using the procedure described above, start with:

```bash
lsof -P -i TCP:8081 -sTCP:LISTEN
```

and if nothing shows up:

```bash
sudo lsof -P -i TCP:8081 -sTCP:LISTEN
```

Finally, depending on your findings, you can apply the following change and start JupyterHub again:

```python
c.JupyterHub.hub_port = 9081 # Or any other free port
```
