JupyterHub
==========

With JupyterHub you can create a **multi-user Hub** which spawns, manages,
and proxies multiple instances of the single-user
`Jupyter notebook <https://jupyter-notebook.readthedocs.io>`_ server. For
example, JupyterHub can be used to serve notebooks to a class of students, a
corporate data science group, or a science research group.

Three main actors make up JupyterHub:

- multi-user **Hub** (tornado process)
- configurable http **proxy** (node-http-proxy)
- multiple **single-user Jupyter notebook servers** (Python/IPython/tornado)

JupyterHub's basic principles for operation are:

- Hub spawns a proxy
- Proxy forwards all requests to Hub by default
- Hub handles login, and spawns single-user servers on demand
- Hub configures proxy to forward url prefixes to the single-user servers

JupyterHub also provides a
`REST API <http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyter/jupyterhub/master/docs/rest-api.yml#/default>`_
for administration of the Hub and users.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Documentation

   getting-started
   howitworks
   websecurity

.. toctree::
   :maxdepth: 2
   :caption: Configuration

   config-examples
   authenticators
   spawners
   troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation

   api/rest
   api/index

.. toctree::
   :maxdepth: 2
   :caption: About JupyterHub

   changelog

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Questions? Suggestions?
-----------------------

- `Jupyter mailing list <https://groups.google.com/forum/#!forum/jupyter>`_
- `Jupyter website <https://jupyter.org>`_
- `Stack Overflow - Jupyter <https://stackoverflow.com/questions/tagged/jupyter>`_
- `Stack Overflow - Jupyter-notebook <https://stackoverflow.com/questions/tagged/jupyter-notebook>`_

