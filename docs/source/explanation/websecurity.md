(explanation:security)=

# Security Overview

The **Security Overview** section helps you learn about:

- the design of JupyterHub with respect to web security
- the semi-trusted user
- the available mitigations to protect untrusted users from each other
- the value of periodic security audits

This overview also helps you obtain a deeper understanding of how JupyterHub
works.

## Semi-trusted and untrusted users

JupyterHub is designed to be a _simple multi-user server for modestly sized
groups_ of **semi-trusted** users. While the design reflects serving
semi-trusted users, JupyterHub can also be suitable for serving **untrusted** users,
but **is not suitable for untrusted users** in its default configuration.

As a result, using JupyterHub with **untrusted** users means more work by the
administrator, since much care is required to secure a Hub, with extra caution on
protecting users from each other.

One aspect of JupyterHub's _design simplicity_ for **semi-trusted** users is that
the Hub and single-user servers are placed in a _single domain_, behind a
[_proxy_][configurable-http-proxy]. If the Hub is serving untrusted
users, many of the web's cross-site protections are not applied between
single-user servers and the Hub, or between single-user servers and each
other, since browsers see the whole thing (proxy, Hub, and single user
servers) as a single website (i.e. single domain).

## Protect users from each other

To protect users from each other, a user must **never** be able to write arbitrary
HTML and serve it to another user on the Hub's domain. This is prevented by JupyterHub's
authentication setup because only the owner of a given single-user notebook server is
allowed to view user-authored pages served by the given single-user notebook
server.

To protect all users from each other, JupyterHub administrators must
ensure that:

- A user **does not have permission** to modify their single-user notebook server,
  including:
  - the installation of new packages in the Python environment that runs
    their single-user server;
  - the creation of new files in any `PATH` directory that precedes the
    directory containing `jupyterhub-singleuser` (if the `PATH` is used
    to resolve the single-user executable instead of using an absolute path);
  - the modification of environment variables (e.g. PATH, PYTHONPATH) for
    their single-user server;
  - the modification of the configuration of the notebook server
    (the `~/.jupyter` or `JUPYTER_CONFIG_DIR` directory).
  - unrestricted selection of the base environment (e.g. the image used in container-based Spawners)

If any additional services are run on the same domain as the Hub, the services
**must never** display user-authored HTML that is neither _sanitized_ nor _sandboxed_
to any user that lacks authentication as the author of a file.

### Sharing access to servers

Because sharing access to servers (via `access:servers` scopes or the sharing feature in JupyterHub 5) by definition means users can serve each other files, enabling sharing is not suitable for untrusted users without also enabling per-user domains.

JupyterHub does not enable any sharing by default.

## Mitigate security issues

The several approaches to mitigating security issues with configuration
options provided by JupyterHub include:

(subdomains)=

### Enable user subdomains

JupyterHub provides the ability to run single-user servers on their own
domains. This means the cross-origin protections between servers has the
desired effect, and user servers and the Hub are protected from each other.

**Subdomains are the only way to reliably isolate user servers from each other.**

To enable subdomains, set:

```python
c.JupyterHub.subdomain_host = "https://jupyter.example.org"
```

When subdomains are enabled, each user's single-user server will be at e.g. `https://username.jupyter.example.org`.
This also requires all user subdomains to point to the same address,
which is most easily accomplished with wildcard DNS, where a single A record points to your server and a wildcard CNAME record points to your A record:

```
A        jupyter.example.org  192.168.1.123
CNAME  *.jupyter.example.org  jupyter.example.org
```

Since this spreads the service across multiple domains, you will likely need wildcard SSL as well,
matching `*.jupyter.example.org`.

Unfortunately, for many institutional domains, wildcard DNS and SSL may not be available.

We also **strongly encourage** serving JupyterHub and user content on a domain that is _not_ a subdomain of any sensitive content.
For reasoning, see [GitHub's discussion of moving user content to github.io from \*.github.com](https://github.blog/2013-04-09-yummy-cookies-across-domains/).

**If you do plan to serve untrusted users, enabling subdomains is highly encouraged**,
as it resolves many security issues, which are difficult to unavoidable when JupyterHub is on a single-domain.

:::{important}
JupyterHub makes no guarantees about protecting users from each other unless subdomains are enabled.

If you want to protect users from each other, you **_must_** enable per-user domains.
:::

### Disable user config

If subdomains are unavailable or undesirable, JupyterHub provides a
configuration option `Spawner.disable_user_config = True`, which can be set to prevent
the user-owned configuration files from being loaded. After implementing this
option, `PATH`s and package installation are the other things that the
admin must enforce.

### Prevent spawners from evaluating shell configuration files

For most Spawners, `PATH` is not something users can influence, but it's important that
the Spawner should _not_ evaluate shell configuration files prior to launching the server.

### Isolate packages in a read-only environment

The user must not have permission to install packages into the environment where the singleuser-server runs.
On a shared system, package isolation is most easily handled by running the single-user server in
a root-owned virtualenv with disabled system-site-packages.
The user must not have permission to install packages into this environment.
The same principle extends to the images used by container-based deployments.
If users can select the images in which their servers run, they can disable all security for their own servers.

It is important to note that the control over the environment is only required for the
single-user server, and not the environment(s) in which the users' kernel(s)
may run. Installing additional packages in the kernel environment does not
pose additional risk to the web application's security.

### Encrypt internal connections with SSL/TLS

By default, all communications within JupyterHub—between the proxy, hub, and single
-user notebooks—are performed unencrypted. Setting the `internal_ssl` flag in
`jupyterhub_config.py` secures the aforementioned routes. Turning this
feature on does require that the enabled `Spawner` can use the certificates
generated by the `Hub` (the default `LocalProcessSpawner` can, for instance).

It is also important to note that this encryption **does not** cover the
`zmq tcp` sockets between the Notebook client and kernel yet. While users cannot
submit arbitrary commands to another user's kernel, they can bind to these
sockets and listen. When serving untrusted users, this eavesdropping can be
mitigated by setting `KernelManager.transport` to `ipc`. This applies standard
Unix permissions to the communication sockets thereby restricting
communication to the socket owner. The `internal_ssl` option will eventually
extend to securing the `tcp` sockets as well.

### Mitigating same-origin deployments

While per-user domains are **required** for robust protection of users from each other,
you can mitigate many (but not all) cross-user issues.
First, it is critical that users cannot modify their server environments, as described above.
Second, it is important that users do not have `access:servers` permission to any server other than their own.

If users can access each others' servers, additional security measures must be enabled, some of which come with distinct user-experience costs.

Without the [Same-Origin Policy] (SOP) protecting user servers from each other,
each user server is considered a trusted origin for requests to each other user server (and the Hub itself).
Servers _cannot_ meaningfully distinguish requests originating from other user servers,
because SOP implies a great deal of trust, losing many restrictions applied to cross-origin requests.

That means pages served from each user server can:

1. arbitrarily modify the path in the Referer
2. make fully authorized requests with cookies
3. access full page contents served from the hub or other servers via popups

JupyterHub uses distinct xsrf tokens stored in cookies on each server path to attempt to limit requests across.
This has limitations because not all requests are protected by these XSRF tokens,
and unless additional measures are taken, the XSRF tokens from other user prefixes may be retrieved.

[Same-Origin Policy]: https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy

For example:

- `Content-Security-Policy` header must prohibit popups and iframes from the same origin.
  The following Content-Security-Policy rules are _insecure_ and readily enable users to access each others' servers:

  - `frame-ancestors: 'self'`
  - `frame-ancestors: '*'`
  - `sandbox allow-popups`

- Ideally, pages should use the strictest `Content-Security-Policy: sandbox` available,
  but this is not feasible in general for JupyterLab pages, which need at least `sandbox allow-same-origin allow-scripts` to work.

The default Content-Security-Policy for single-user servers is

```
frame-ancestors: 'none'
```

which prohibits iframe embedding, but not pop-ups.

A more secure Content-Security-Policy that has some costs to user experience is:

```
frame-ancestors: 'none'; sandbox allow-same-origin allow-scripts
```

`allow-popups` is not disabled by default because disabling it breaks legitimate functionality, like "Open this in a new tab", and the "JupyterHub Control Panel" menu item.
To reiterate, the right way to avoid these issues is to enable per-user domains, where none of these concerns come up.

Note: even this level of protection requires administrators maintaining full control over the user server environment.
If users can modify their server environment, these methods are ineffective, as users can readily disable them.

### Cookie tossing

Cookie tossing is a technique where another server on a subdomain or peer subdomain can set a cookie
which will be read on another domain.
This is not relevant unless there are other user-controlled servers on a peer domain.

"Domain-locked" cookies avoid this issue, but have their own restrictions:

- JupyterHub must be served over HTTPS
- All secure cookies must be set on `/`, not on sub-paths, which means they are shared by all JupyterHub components in a single-domain deployment.

As a result, this option is only recommended when per-user subdomains are enabled,
to prevent sending all jupyterhub cookies to all user servers.

To enable domain-locked cookies, set:

```python
c.JupyterHub.cookie_host_prefix_enabled = True
```

```{versionadded} 4.1

```

### Forced-login

Jupyter servers can share links with `?token=...`.
JupyterHub prior to 5.0 will accept this request and persist the token for future requests.
This is useful for enabling admins to create 'fully authenticated' links bypassing login.
However, it also means users can share their own links that will log other users into their own servers,
enabling them to serve each other notebooks and other arbitrary HTML, depending on server configuration.

```{versionadded} 4.1
Setting environment variable `JUPYTERHUB_ALLOW_TOKEN_IN_URL=0` in the single-user environment can opt out of accepting token auth in URL parameters.
```

```{versionadded} 5.0
Accepting tokens in URLs is disabled by default, and `JUPYTERHUB_ALLOW_TOKEN_IN_URL=1` environment variable must be set to _allow_ token auth in URL parameters.
```

## Security audits

We recommend that you do periodic reviews of your deployment's security. It's
good practice to keep [JupyterHub](https://readthedocs.org/projects/jupyterhub/), [configurable-http-proxy][], and [nodejs
versions](https://github.com/nodejs/Release) up to date.

A handy website for testing your deployment is
[Qualsys' SSL analyzer tool](https://www.ssllabs.com/ssltest/analyze.html).

[configurable-http-proxy]: https://github.com/jupyterhub/configurable-http-proxy

## Vulnerability reporting

If you believe you have found a security vulnerability in JupyterHub, or any
Jupyter project, please report it to
[security@ipython.org](mailto:security@ipython.org). If you prefer to encrypt
your security reports, you can use [this PGP public
key](https://jupyter.org/assets/ipython_security.asc).
