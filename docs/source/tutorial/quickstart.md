# Quickstart

## Prerequisites

Before installing JupyterHub, you will need:

- a Linux/Unix-based system
- [Python {{python_min}}](https://www.python.org/downloads/) or greater. An understanding
  of using [`pip`](https://pip.pypa.io) or
  [`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html) for
  installing Python packages is helpful.
- [Node.js {{node_min}}](https://www.npmjs.com/) or greater, along with npm. [Install Node.js/npm](https://docs.npmjs.com/getting-started/installing-node),
  using your operating system's package manager.
  - If you are using **`conda`**, the nodejs and npm dependencies will be installed for
    you by conda.

  - If you are using **`pip`**, install a recent version of
    [nodejs/npm](https://docs.npmjs.com/getting-started/installing-node).
    For example, install it on Linux (Debian/Ubuntu) using:

    ```
    sudo apt-get install nodejs npm
    ```

    [nodesource][] is a great resource to get more recent versions of the nodejs runtime,
    if your system package manager only has an old version of Node.js.

- A [pluggable authentication module (PAM)](https://en.wikipedia.org/wiki/Pluggable_authentication_module)
  to use the [default Authenticator](authenticators).
  PAM is often available by default on most distributions, if this is not the case it can be installed by
  using the operating system's package manager.
- TLS certificate and key for HTTPS communication
- Domain name

[nodesource]: https://github.com/nodesource/distributions#table-of-contents

Before running the single-user notebook servers (which may be on the same
system as the Hub or not), you will need:

- [JupyterLab][] version 3 or greater,
  or [Jupyter Notebook][]
  4 or greater.

[jupyterlab]: https://jupyterlab.readthedocs.io
[jupyter notebook]: https://jupyter.readthedocs.io/en/latest/install.html

## Installation

JupyterHub can be installed with `pip` (and the proxy with `npm`) or `conda`:

**pip, npm:**

```bash
python3 -m pip install jupyterhub
npm install -g configurable-http-proxy
python3 -m pip install jupyterlab notebook  # needed if running the notebook servers in the same environment
```

**conda** (one command installs jupyterhub and proxy):

```bash
conda install -c conda-forge jupyterhub  # installs jupyterhub and proxy
conda install jupyterlab notebook  # needed if running the notebook servers in the same environment
```

Test your installation. If installed, these commands should return the packages'
help contents:

```bash
jupyterhub -h
configurable-http-proxy -h
```

## Configuration

At this point, we could start jupyterhub, but nobody would be able to use it!
Only users who are explicitly **allowed** can use JupyterHub.
To allow users, we need to create a configuration file.
JupyterHub uses a configuration file called `jupyterhub_config.py`,
which is a regular Python script with one function `get_config()` pre-defined, returning the "config object".
Assigning attributes to this object is how we configure JupyterHub.

At this point, we have two choices:

1. allow any user who can successfully login with our Authenticator (often a good choice for local machines with PAM)
2. allow one or more users by name.

We'll start with the first one.
Create the file `jupyerhub_config.py` with the content:

```python
c = get_config()  # noqa
c.Authenticator.allow_all = True
# alternative: c.Authenticator.allowed_users = {"yourusername"}
```

This configuration means that anyone who can login with PAM (any existing user on the system) should have access to JupyterHub.

:::{seealso}
[](authenticators)
:::

## Start the Hub server

To start the Hub server, run the command:

```bash
jupyterhub
```

Visit `http://localhost:8000` in your browser, and sign in with your Unix
credentials.

To **allow multiple users to sign in** to the Hub server, you must start
`jupyterhub` as a _privileged user_, such as root:

```bash
sudo jupyterhub
```

[](howto:config:no-sudo)
describes how to run the server as a _less privileged user_. This requires
additional configuration of the system.
