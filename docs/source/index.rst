JupyterHub
==========

JupyterHub is a server that gives multiple users access to Jupyter notebooks,
running an independent Jupyter notebook server for each user.

To use JupyterHub, you need a Unix server (typically Linux) running
somewhere that is accessible to your team on the network. It might be on an
internal network at your organisation, or it can run on the public internet (in
which case, take care with `security <getting-started.html#security>`__). It
runs as an HTTP server. You can get users to go directly to the IP address of
the server in their browser, or provide it with a domain name.

There are different :doc:`authenticators <authenticators>` which control access
to JupyterHub. The default one (pam) uses the user accounts on the server where
JupyterHub is running. If you use this, you will need to create a user account
on the system for each user on your team. Using other authenticators, you can
allow users to sign in with e.g. a Github account, or with any single-sign-on
system your organisation has.

Then there are :doc:`spawners <spawners>`, which control how JupyterHub starts
the notebook servers for individual users. The default spawner will use their
system username to start a notebook server for that user. The other main option
is to start each server in a separate container, often using Docker.

JupyterHub runs as three separate parts:

* The multi-user Hub (Python & Tornado)
* A `configurable http proxy <https://github.com/jupyter/configurable-http-proxy>`_ (NodeJS)
* Multiple single-user Jupyter notebook servers (Python & Tornado)

Basic principles:

* Hub spawns proxy
* Proxy forwards ~all requests to hub by default
* Hub handles login, and spawns single-user servers on demand
* Hub configures proxy to forward url prefixes to single-user servers


Contents:

.. toctree::
   :maxdepth: 2
   :caption: User Documentation

   getting-started
   howitworks

.. toctree::
   :maxdepth: 2
   :caption: Configuration

   authenticators
   spawners
   troubleshooting

.. toctree::
   :maxdepth: 1
   :caption: Developer Documentation
   
   api/index


.. toctree::
   :maxdepth: 1
   :caption: Community documentation



.. toctree::
   :maxdepth: 2
   :caption: About JupyterHub

   changelog

.. toctree::
   :maxdepth: 1
   :caption: Questions? Suggestions?

   Jupyter mailing list <https://groups.google.com/forum/#!forum/jupyter>
   Jupyter website <https://jupyter.org>
   Stack Overflow - Jupyter <https://stackoverflow.com/questions/tagged/jupyter>
   Stack Overflow - Jupyter-notebook <https://stackoverflow.com/questions/tagged/jupyter-notebook>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

