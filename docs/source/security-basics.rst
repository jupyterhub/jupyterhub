Security settings
=================

.. important::

   You should not run JupyterHub without SSL encryption on a public network.

Security is the most important aspect of configuring Jupyter. Three
configuration settings are the main aspects of security configuration:

1. :ref:`SSL encryption <ssl-encryption>` (to enable HTTPS)
2. :ref:`Cookie secret <cookie-secret>` (a key for encrypting browser cookies)
3. Proxy :ref:`authentication token <authentication-token>` (used for the Hub and
   other services to authenticate to the Proxy)

The Hub hashes all secrets (e.g., auth tokens) before storing them in its
database. A loss of control over read-access to the database should have
minimal impact on your deployment; if your database has been compromised, it
is still a good idea to revoke existing tokens.

.. _ssl-encryption:

Enabling SSL encryption
-----------------------

Since JupyterHub includes authentication and allows arbitrary code execution,
you should not run it without SSL (HTTPS).

Using an SSL certificate
~~~~~~~~~~~~~~~~~~~~~~~~

This will require you to obtain an official, trusted SSL certificate or create a
self-signed certificate. Once you have obtained and installed a key and
certificate you need to specify their locations in the ``jupyterhub_config.py``
configuration file as follows:

.. code-block:: python

    c.JupyterHub.ssl_key = '/path/to/my.key'
    c.JupyterHub.ssl_cert = '/path/to/my.cert'


Some cert files also contain the key, in which case only the cert is needed. It
is important that these files be put in a secure location on your server, where
they are not readable by regular users.

If you are using a **chain certificate**, see also chained certificate for SSL
in the JupyterHub `troubleshooting FAQ <troubleshooting>`_.

Using letsencrypt
~~~~~~~~~~~~~~~~~

It is also possible to use `letsencrypt <https://letsencrypt.org/>`_ to obtain
a free, trusted SSL certificate. If you run letsencrypt using the default
options, the needed configuration is (replace ``mydomain.tld`` by your fully
qualified domain name):

.. code-block:: python

    c.JupyterHub.ssl_key = '/etc/letsencrypt/live/{mydomain.tld}/privkey.pem'
    c.JupyterHub.ssl_cert = '/etc/letsencrypt/live/{mydomain.tld}/fullchain.pem'

If the fully qualified domain name (FQDN) is ``example.com``, the following
would be the needed configuration:

.. code-block:: python

    c.JupyterHub.ssl_key = '/etc/letsencrypt/live/example.com/privkey.pem'
    c.JupyterHub.ssl_cert = '/etc/letsencrypt/live/example.com/fullchain.pem'


If SSL termination happens outside of the Hub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In certain cases, e.g. behind `SSL termination in NGINX <https://www.nginx.com/resources/admin-guide/nginx-ssl-termination/>`_,
allowing no SSL running on the hub may be the desired configuration option.

.. _cookie-secret:

Cookie secret
-------------

The cookie secret is an encryption key, used to encrypt the browser cookies
which are used for authentication. Three common methods are described for
generating and configuring the cookie secret.

Generating and storing as a cookie secret file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The cookie secret should be 32 random bytes, encoded as hex, and is typically
stored in a ``jupyterhub_cookie_secret`` file. An example command to generate the
``jupyterhub_cookie_secret`` file is:

.. code-block:: bash

    openssl rand -hex 32 > /srv/jupyterhub/jupyterhub_cookie_secret

In most deployments of JupyterHub, you should point this to a secure location on
the file system, such as ``/srv/jupyterhub/jupyterhub_cookie_secret``.

The location of the ``jupyterhub_cookie_secret`` file can be specified in the
``jupyterhub_config.py`` file as follows:

.. code-block:: python

    c.JupyterHub.cookie_secret_file = '/srv/jupyterhub/jupyterhub_cookie_secret'

If the cookie secret file doesn't exist when the Hub starts, a new cookie
secret is generated and stored in the file. The file must not be readable by
``group`` or ``other`` or the server won't start. The recommended permissions
for the cookie secret file are ``600`` (owner-only rw).

Generating and storing as an environment variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you would like to avoid the need for files, the value can be loaded in the
Hub process from the ``JPY_COOKIE_SECRET`` environment variable, which is a
hex-encoded string. You can set it this way:

.. code-block:: bash

    export JPY_COOKIE_SECRET=`openssl rand -hex 32`

For security reasons, this environment variable should only be visible to the
Hub. If you set it dynamically as above, all users will be logged out each time
the Hub starts.

Generating and storing as a binary string
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also set the cookie secret in the configuration file
itself, ``jupyterhub_config.py``, as a binary string:

.. code-block:: python

    c.JupyterHub.cookie_secret = bytes.fromhex('64 CHAR HEX STRING')


.. important::

   If the cookie secret value changes for the Hub, all single-user notebook
   servers must also be restarted.


.. _authentication-token:

Proxy authentication token
--------------------------

The Hub authenticates its requests to the Proxy using a secret token that
the Hub and Proxy agree upon. The value of this string should be a random
string (for example, generated by ``openssl rand -hex 32``).

Generating and storing token in the configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Or you can set the value in the configuration file, ``jupyterhub_config.py``:

.. code-block:: python

    c.JupyterHub.proxy_auth_token = '0bc02bede919e99a26de1e2a7a5aadfaf6228de836ec39a05a6c6942831d8fe5'

Generating and storing as an environment variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can pass this value of the proxy authentication token to the Hub and Proxy
using the ``CONFIGPROXY_AUTH_TOKEN`` environment variable:

.. code-block:: bash

    export CONFIGPROXY_AUTH_TOKEN='openssl rand -hex 32'

This environment variable needs to be visible to the Hub and Proxy.

Default if token is not set
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you don't set the Proxy authentication token, the Hub will generate a random
key itself, which means that any time you restart the Hub you **must also
restart the Proxy**. If the proxy is a subprocess of the Hub, this should happen
automatically (this is the default configuration).
