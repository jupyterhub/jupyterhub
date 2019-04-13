JupyterHub
==========

`JupyterHub`_ is the best way to serve `Jupyter notebook`_ for multiple users. 
It can be used in a classes of students, a corporate data science group or scientific 
research group. It is a multi-user **Hub** that spawns, manages, and proxies multiple
instances of the single-user `Jupyter notebook`_ server.

To make life easier, JupyterHub have distributions. Be sure to 
take a look at them before continuing with the configuration of the broad 
original system of `JupyterHub`_. Today, you can find two main cases: 

1. If you need a simple case for a small amount of users (0-100) and single server 
   take a look at 
   `The Littlest JupyterHub <https://github.com/jupyterhub/the-littlest-jupyterhub>`__ distribution. 
2. If you need to allow for even more users, a dynamic amount of servers can be used on a cloud,
   take a look at the `Zero to JupyterHub with Kubernetes <https://github.com/jupyterhub/zero-to-jupyterhub-k8s>`__ .


Four subsystems make up JupyterHub:

* a **Hub** (tornado process) that is the heart of JupyterHub
* a **configurable http proxy** (node-http-proxy) that receives the requests from the client's browser
* multiple **single-user Jupyter notebook servers** (Python/IPython/tornado) that are monitored by Spawners
* an **authentication class** that manages how users can access the system


Besides these central pieces, you can add optional configurations through a `config.py` file and manage users kernels on an admin panel. A simplification of the whole system can be seen in the figure below:

.. image:: images/jhub-fluxogram.jpeg
   :alt: JupyterHub subsystems
   :width: 80%
   :align: center


JupyterHub performs the following functions:

- The Hub launches a proxy
- The proxy forwards all requests to the Hub by default
- The Hub handles user login and spawns single-user servers on demand
- The Hub configures the proxy to forward URL prefixes to the single-user
  notebook servers

For convenient administration of the Hub, its users, and services,
JupyterHub also provides a `REST API`_.

The JupyterHub team and Project Jupyter value our community, and JupyterHub
follows the Jupyter [Community Guides](https://jupyter.readthedocs.io/en/latest/community/content-community.html).

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
* :doc:`reference/templates`
* :doc:`reference/config-user-env`
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
