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

- The Hub launches a proxy
- The proxy forwards all requests to the Hub by default
- The Hub handles user login and spawns single-user servers on demand
- The Hub configures the proxy to forward URL prefixes to the single-user
  notebook servers

For convenient administration of the Hub, its users, and services,
JupyterHub also provides a `REST API`_.

Contents
--------

**Installation Guide**

* :doc:`installation-guide`
* :doc:`quickstart`
* :doc:`quickstart-docker`
* :doc:`installation-basics`

**Getting Started**

* :doc:`getting-started/index`
* :doc:`getting-started/config-basics`
* :doc:`getting-started/networking-basics`
* :doc:`getting-started/security-basics`
* :doc:`getting-started/authenticators-users-basics`
* :doc:`getting-started/spawners-basics`
* :doc:`getting-started/services-basics`

**Technical Reference**

* :doc:`reference/index`
* :doc:`reference/technical-overview`
* :doc:`reference/websecurity`
* :doc:`reference/authenticators`
* :doc:`reference/spawners`
* :doc:`reference/services`
* :doc:`reference/rest`
* :doc:`reference/upgrading`
* :doc:`reference/config-examples`
* :doc:`reference/config-ghoauth`
* :doc:`reference/config-proxy`
* :doc:`reference/config-sudo`

**API Reference**

* :doc:`api/index`

**Tutorials**

* :doc:`tutorials/index`
* :doc:`tutorials/upgrade-dot-eight`
* `Zero to JupyterHub with Kubernetes <https://zero-to-jupyterhub.readthedocs.io/en/latest/>`_

**Troubleshooting**

* :doc:`troubleshooting`

**About JupyterHub**

* :doc:`contributor-list`
* :doc:`gallery-jhub-deployments`

**Changelog**

* :doc:`changelog`

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

   installation-guide
   getting-started/index
   reference/index
   api/index
   tutorials/index
   troubleshooting
   contributor-list
   gallery-jhub-deployments
   changelog


.. _JupyterHub: https://github.com/jupyterhub/jupyterhub
.. _Jupyter notebook: https://jupyter-notebook.readthedocs.io/en/latest/
.. _REST API: http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyterhub/jupyterhub/master/docs/rest-api.yml#!/default
