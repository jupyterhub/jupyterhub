JupyterHub
==========

`JupyterHub`_, a multi-user **Hub**, spawns, manages, and proxies multiple
instances of the single-user `Jupyter notebook`_ server.
JupyterHub can be used to serve notebooks to a class of students, a corporate
data science group, or a scientific research group.

.. image:: images/jhub-parts.png
   :alt: JupyterHub subsystems
   :width: 40%
   :align: right

Three subsystems make up JupyterHub:

* a multi-user **Hub** (tornado process)
* a **configurable http proxy** (node-http-proxy)
* multiple **single-user Jupyter notebook servers** (Python/IPython/tornado)

JupyterHub performs the following functions:

- The Hub spawns a proxy
- The proxy forwards all requests to the Hub by default
- The Hub handles user login and spawns single-user servers on demand
- The Hub configures the proxy to forward URL prefixes to the single-user
  notebook servers

For convenient administration of the Hub, its users, and :doc:`services`,
JupyterHub also provides a
`REST API`_.

Contents
--------

**Installation Guide**

* :doc:`quickstart`
* :doc:`getting-started`


**Configuration Reference**

* :doc:`howitworks`
* :doc:`websecurity`
* :doc:`rest`
* :doc:`authenticators`
* :doc:`spawners`
* :doc:`services`
* :doc:`upgrading`
* :doc:`config-examples`

**API Reference**

* :doc:`api/index`


**Troubleshooting**

* :doc:`troubleshooting`


**Changelog**

* :doc:`changelog`


**About JupyterHub**

* :doc:`contributor-list`
* :doc:`gallery-jhub-deployments`


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`


Questions? Suggestions?
-----------------------

- `Jupyter mailing list <https://groups.google.com/forum/#!forum/jupyter>`_
- `Jupyter website <https://jupyter.org>`_

.. _contents:

Full Table of Contents
----------------------

.. toctree::
   :maxdepth: 2

   user-guide
   configuration-guide
   api/index
   troubleshooting
   changelog
   contributor-list
   gallery-jhub-deployments


.. _JupyterHub: https://github.com/jupyterhub/jupyterhub
.. _Jupyter notebook: https://jupyter-notebook.readthedocs.io/en/latest/
.. _REST API: http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyterhub/jupyterhub/master/docs/rest-api.yml#!/default
