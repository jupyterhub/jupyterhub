# Security Overview

The **Security Overview** section helps you learn about:

- the design of JupyterHub with respect to web security
- the semi-trusted user
- the available mitigations to protect untrusted users from each other
- the value of periodic security audits.

This overview also helps you obtain a deeper understanding of how JupyterHub
works.

## Semi-trusted and untrusted users

JupyterHub is designed to be a *simple multi-user server for modestly sized
groups* of **semi-trusted** users. While the design reflects serving semi-trusted
users, JupyterHub is not necessarily unsuitable for serving **untrusted** users.

Using JupyterHub with **untrusted** users does mean more work by the
administrator. Much care is required to secure a Hub, with extra caution on
protecting users from each other as the Hub is serving untrusted users.

One aspect of JupyterHub's *design simplicity* for **semi-trusted** users is that
the Hub and single-user servers are placed in a *single domain*, behind a
[*proxy*][configurable-http-proxy]. If the Hub is serving untrusted
users, many of the web's cross-site protections are not applied between
single-user servers and the Hub, or between single-user servers and each
other, since browsers see the whole thing (proxy, Hub, and single user
servers) as a single website (i.e. single domain).

## Protect users from each other

To protect users from each other, a user must **never** be able to write arbitrary
HTML and serve it to another user on the Hub's domain. JupyterHub's
authentication setup prevents a user writing arbitrary HTML and serving it to
another user because only the owner of a given single-user notebook server is
allowed to view user-authored pages served by the given single-user notebook
server.

To protect all users from each other, JupyterHub administrators must
ensure that:

* A user **does not have permission** to modify their single-user notebook server,
  including:
  - A user **may not** install new packages in the Python environment that runs
    their single-user server.
  - If the `PATH` is used to resolve the single-user executable (instead of
    using an absolute path), a user **may not** create new files in any `PATH`
    directory that precedes the directory containing `jupyterhub-singleuser`.
  - A user may not modify environment variables (e.g. PATH, PYTHONPATH) for
    their single-user server.
* A user **may not** modify the configuration of the notebook server
  (the `~/.jupyter` or `JUPYTER_CONFIG_DIR` directory).

If any additional services are run on the same domain as the Hub, the services
**must never** display user-authored HTML that is neither *sanitized* nor *sandboxed*
(e.g. IFramed) to any user that lacks authentication as the author of a file.

## Mitigate security issues

Several approaches to mitigating these issues with configuration
options provided by JupyterHub include:

### Enable subdomains

JupyterHub provides the ability to run single-user servers on their own
subdomains. This means the cross-origin protections between servers has the
desired effect, and user servers and the Hub are protected from each other. A
user's single-user server will be at `username.jupyter.mydomain.com`. This also
requires all user subdomains to point to the same address, which is most easily
accomplished with wildcard DNS. Since this spreads the service across multiple
domains, you will need wildcard SSL, as well. Unfortunately, for many
institutional domains, wildcard DNS and SSL are not available. **If you do plan
to serve untrusted users, enabling subdomains is highly encouraged**, as it
resolves the cross-site issues.

### Disable user config

If subdomains are not available or not desirable, JupyterHub provides a
configuration option `Spawner.disable_user_config`, which can be set to prevent
the user-owned configuration files from being loaded. After implementing this
option, PATHs and package installation and PATHs are the other things that the
admin must enforce.

### Prevent spawners from evaluating shell configuration files

For most Spawners, `PATH` is not something users can influence, but care should
be taken to ensure that the Spawner does *not* evaluate shell configuration
files prior to launching the server.

### Isolate packages using virtualenv

Package isolation is most easily handled by running the single-user server in
a virtualenv with disabled system-site-packages. The user should not have
permission to install packages into this environment.

It is important to note that the control over the environment only affects the
single-user server, and not the environment(s) in which the user's kernel(s)
may run. Installing additional packages in the kernel environment does not
pose additional risk to the web application's security.

### Encrypt internal connections with SSL/TLS

By default, all communication on the server, between the proxy, hub, and single
-user notebooks is performed unencrypted. Setting the `internal_ssl` flag in
`jupyterhub_config.py` secures the aforementioned routes. Turning this
feature on does require that the enabled `Spawner` can use the certificates
generated by the `Hub` (the default `LocalProcessSpawner` can, for instance).

It is also important to note that this encryption **does not** (yet) cover the
`zmq tcp` sockets between the Notebook client and kernel. While users cannot
submit arbitrary commands to another user's kernel, they can bind to these
sockets and listen. When serving untrusted users, this eavesdropping can be
mitigated by setting `KernelManager.transport` to `ipc`. This applies standard
Unix permissions to the communication sockets thereby restricting
communication to the socket owner. The `internal_ssl` option will eventually
extend to securing the `tcp` sockets as well.

## Security audits

We recommend that you do periodic reviews of your deployment's security. It's
good practice to keep JupyterHub, configurable-http-proxy, and nodejs
versions up to date.

A handy website for testing your deployment is
[Qualsys' SSL analyzer tool](https://www.ssllabs.com/ssltest/analyze.html).


[configurable-http-proxy]: https://github.com/jupyterhub/configurable-http-proxy

## Vulnerability reporting

If you believe you’ve found a security vulnerability in JupyterHub, or any
Jupyter project, please report it to
[security@ipython.org](mailto:security@iypthon.org). If you prefer to encrypt
your security reports, you can use [this PGP public
key](https://jupyter-notebook.readthedocs.io/en/stable/_downloads/ipython_security.asc).
