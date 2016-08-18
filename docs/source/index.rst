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

**User Guide**

* :doc:`getting-started`
* :doc:`rest`
* :doc:`howitworks`
* :doc:`websecurity`

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: User Guide

   getting-started
   rest
   howitworks
   websecurity


**Configuration Guide**

* :doc:`authenticators`
* :doc:`spawners`
* :doc:`config-examples`
* :doc:`troubleshooting`

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Configuration Guide

   authenticators
   spawners
   config-examples
   troubleshooting


**API Reference**

* :doc:`api/index`

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: API Reference

   api/index


**About JupyterHub**

* :doc:`changelog`

.. toctree::
   :maxdepth: 2
   :hidden:
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


