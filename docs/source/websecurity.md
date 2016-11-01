# Web Security in JupyterHub

JupyterHub is designed to be a simple multi-user server for modestly sized
groups of semi-trusted users. While the design reflects serving semi-trusted
users, JupyterHub is not necessarily unsuitable for serving untrusted users.
Using JupyterHub with untrusted users does mean more work and much care is
required to secure a Hub against untrusted users, with extra caution on
protecting users from each other as the Hub is serving untrusted users.

One aspect of JupyterHub's design simplicity for semi-trusted users is that
the Hub and single-user servers are placed in a single domain, behind a
[proxy][configurable-http-proxy]. As a result, if the Hub is serving untrusted
users, many of the web's cross-site protections are not applied between
single-user servers and the Hub, or between single-user servers and each
other, since browsers see the whole thing (proxy, Hub, and single user
servers) as a single website.

To protect users from each other, a user must never be able to write arbitrary
HTML and serve it to another user on the Hub's domain. JupyterHub's
authentication setup prevents this because only the owner of a given
single-user server is allowed to view user-authored pages served by their
server. To protect all users from each other, JupyterHub administrators must
ensure that:

* A user does not have permission to modify their single-user server:
  - A user may not install new packages in the Python environment that runs
    their server.
  - If the PATH is used to resolve the single-user executable (instead of an
    absolute path), a user may not create new files in any PATH directory
    that precedes the directory containing jupyterhub-singleuser.
  - A user may not modify environment variables (e.g. PATH, PYTHONPATH) for
    their single-user server.
* A user may not modify the configuration of the notebook server
  (the ~/.jupyter or JUPYTER_CONFIG_DIR directory).

If any additional services are run on the same domain as the Hub, the services
must never display user-authored HTML that is neither sanitized nor sandboxed
(e.g. IFramed) to any user that lacks authentication as the author of a file.


## Mitigations

There are two main configuration options provided by JupyterHub to mitigate
these issues:

### Subdomains

JupyterHub 0.5 adds the ability to run single-user servers on their own
subdomains, which means the cross-origin protections between servers has the
desired effect, and user servers and the Hub are protected from each other. A
user's server will be at `username.jupyter.mydomain.com`, etc. This requires
all user subdomains to point to the same address, which is most easily
accomplished with wildcard DNS. Since this spreads the service across multiple
domains, you will need wildcard SSL, as well. Unfortunately, for many
institutional domains, wildcard DNS and SSL are not available, but if you do
plan to serve untrusted users, enabling subdomains is highly encouraged, as it
resolves all of the cross-site issues.

### Disabling user config

If subdomains are not available or not desirable, 0.5 also adds an option
`Spawner.disable_user_config`, which you can set to prevent the user-owned
configuration files from being loaded. This leaves only package installation
and PATHs as things the admin must enforce.

For most Spawners, PATH is not something users can influence, but care should
be taken to ensure that the Spawn does *not* evaluate shell configuration
files prior to launching the server.

Package isolation is most easily handled by running the single-user server in
a virtualenv with disabled system-site-packages.

## Extra notes

It is important to note that the control over the environment only affects the
single-user server, and not the environment(s) in which the user's kernel(s)
may run. Installing additional packages in the kernel environment does not
pose additional risk to the web application's security.

[configurable-http-proxy]: https://github.com/jupyterhub/configurable-http-proxy
