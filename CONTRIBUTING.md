# Contributing

Welcome! As a [Jupyter](https://jupyter.org) project, we follow the [Jupyter contributor guide](https://jupyter.readthedocs.io/en/latest/contributor/content-contributor.html).
JupyterHub also follows the Jupyter [Community Guides](https://jupyter.readthedocs.io/en/latest/community/content-community.html).


## Set up your development system

### System requirements

JupyterHub can only run on MacOS or Linux operating systems. If you
are using Windows, we recommend using [VirtualBox](https://www.virtualbox.org/)
or a similar system to run [Ubuntu Linux](https://www.ubuntu.com/)
for development.

### Install Python

JupyterHub is written in the [Python](https://python3.org) programming
language, and requires you have at least version 3.5 installed locally.
If you haven't installed Python before, the recommended way to install
it is to use [miniconda](https://conda.io/miniconda.html). Remember
to get the 'Python 3' version, and **not** the 'Python 2' version!

### Install nodejs

`configurable-http-proxy`, the default proxy implementation for JupyterHub,
is written in Javascript to run on [NodeJS](https://nodejs.org/en/). If
you have not installed nodejs before, we recommend installing it in the
`miniconda` environment you set up for Python. You can do so with
`conda install nodejs`.

### Install git

JupyterHub uses [git](https://git-scm.com) & [GitHub](https://github.com)
for development & collaboration. You need to [install git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
to work on JupyterHub. We also recommend getting a free account
on GitHub.com.

## Set up a development install

When developing JupyterHub, you need to make changes to the code
& see their effects quickly. You need to do a developer install
to make that happen.

1. Clone the [JupyterHub git repository](https://github.com/jupyterhub/jupyterhub)
   on to your computer.

   ```bash
   git clone https://github.com/jupyterhub/jupyterhub
   cd jupyterhub
   ```

2. Make sure the `python` you installed and the `npm` you installed
   are available to you on the commandline.

   ```bash
   python -V
   ```

   This should return a version number greater than or equal to 3.5.

   ```bash
   npm -v
   ```

   This should return a version number greater than or equal to 5.0.

3. Install `configurable-http-proxy`. This is required to run JupyterHub.

   ```bash
   npm install -g configurable-http-proxy
   ```

   If you get an error that says `Error: EACCES: permission denied`,
   you might need to prefix the command with `sudo`. If you do not have
   access to sudo, you may instead run the following commands:

   ```bash
   npm install configurable-http-proxy
   export PATH=$PATH:$(pwd)/node_modules/.bin
   ```

   The second line needs to be run every time you open a new terminal.

4. Install the python packages required for JupyterHub development.

   ```bash
   pip3 install -r dev-requirements.txt
   pip3 install -r requirements.txt
   ```

5. Install the development version of JupyterHub. This lets you edit
   JupyterHub code in a text editor & restart the JupyterHub process
   to see your code changes immediately.

   ```bash
   pip3 install --editable .
   ```

6. You are now ready to start JupyterHub!

   ```bash
   jupyterhub
   ```

7. You can access JupyterHub from your browser at `http://localhost:8000`
   now.

Happy developing!

### Using DummyAuthenticator & SimpleSpawner

The default JupyterHub [authenticator](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html#the-default-pam-authenticator)
& [spawner](https://jupyterhub.readthedocs.io/en/stable/api/spawner.html#localprocessspawner)
require your system to have user accounts for each user you want to log in to
JupyterHub as.

[DummyAuthenticator](https://github.com/jupyterhub/dummyauthenticator) allows
you to log in with any username & password.
[SimpleSpawner](https://github.com/jupyterhub/simplespawner) lets you start
servers without having to create unix users for each JupyterHub user.
Together, these make it much easier to test JupyterHub.

If you are working on parts of JupyterHub that are common to all
authenticators & spawners, we recommend using both DummyAuthenticator &
SimpleSpawner. If you are working on just authenticator related parts, use
only SimpleSpawner. Similarly, if you are working on just spawner
related parts, use only DummyAuthenticator.

## Troubleshooting a development install

### `lessc` not found

If the `pip3 install --editable .` command fails and complains about `lessc`
being unavailable, you may need to explicitly install some additional
JavaScript dependencies:

```bash
npm install
```

This will fetch client-side JavaScript dependencies necessary to compile CSS.

You may also need to manually update JavaScript and CSS after some development
updates, with:

```bash
python3 setup.py js    # fetch updated client-side js
python3 setup.py css   # recompile CSS from LESS sources
```

## Running the test suite

We use [pytest](http://doc.pytest.org/en/latest/) for running tests. 

1. Set up a development install as described above. 

2. Set environment variable for `ASYNC_TEST_TIMEOUT` to 15 seconds:

```bash
export ASYNC_TEST_TIMEOUT=15
```

3. Run tests.

To run all the tests:

```bash
pytest -v jupyterhub/tests
```

To run an individual test file (i.e. `test_api.py`):

```bash
pytest -v jupyterhub/tests/test_api.py
```

### Troubleshooting tests

If you see test failures because of timeouts, you may wish to increase the
`ASYNC_TEST_TIMEOUT` used by the
[pytest-tornado-plugin](https://github.com/eugeniy/pytest-tornado/blob/c79f68de2222eb7cf84edcfe28650ebf309a4d0c/README.rst#markers)
from the default of 5 seconds:

```bash
export ASYNC_TEST_TIMEOUT=15
```

If you see many test errors and failures, double check that you have installed
`configurable-http-proxy`.

## Building the Docs locally

1. Install the development system as described above.

2. Install the dependencies for documentation:

```bash
pip3 install -r docs/requirements.txt
```

3. Build the docs:

```bash
cd docs
make clean
make html
```

4. View the docs:

```bash
open build/html/index.html
```
