.. JupyterHub documentation master file, created by
   sphinx-quickstart on Mon Jan  4 16:31:09 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

JupyterHub
==========

.. note:: This is the official documentation for JupyterHub. This project is
          under active development.

JupyterHub is a multi-user server that manages and proxies multiple instances
of the single-user Jupyter notebook server.

Three actors:

* multi-user Hub (tornado process)
* `configurable http proxy <https://github.com/jupyter/configurable-http-proxy>`_ (node-http-proxy)
* multiple single-user IPython notebook servers (Python/IPython/tornado)

Basic principles:

* Hub spawns proxy
* Proxy forwards ~all requests to hub by default
* Hub handles login, and spawns single-user servers on demand
* Hub configures proxy to forward url prefixes to single-user servers


Contents:

.. toctree::
   :maxdepth: 1
   :caption: User Documentation

   getting-started
   howitworks

.. toctree::
   :maxdepth: 2
   :caption: Configuration

   authenticators
   spawners

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

