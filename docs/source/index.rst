==========
JupyterHub
==========
`JupyterHub`_ is the best way to serve `Jupyter notebook`_ for multiple users.
It is a multi-user **Hub** that spawns, manages, and proxies multiple instances 
of the single-user `Jupyter notebook`_ server. Therefore, with JupyterHub, 
users can log in to the server, and write Python code in a web browser, 
without having to install software on their local machine. 

JupyterHub supports web browsers, tablets and smartphones and can be used by 
multiple users at the same time such as; a class of students, a corporate data 
science group or scientific research group. 
JupyterHub makes life easier by enabling collaboration between both small (0-100 users) and 
large teams (more than 100 users). It has distributions which are developed to serve the needs
of each of these teams respectively. 

JupyterHub is made up of four subsystems:

* A **Hub** (tornado process) that is the heart of JupyterHub
* A **configurable http proxy** (node-http-proxy) that receives the requests from the client's browser
* Multiple **single-user Jupyter notebook servers** (Python/IPython/tornado) that are monitored by Spawners
* An **authentication class** that manages how users can access the system

Additionally, optional configurations can be added through a `config.py` file and manage users 
kernels on an admin panel. A simplification of the whole system is displayed in the figure below:

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
JupyterHub also provides a :doc:`REST API <reference/rest-api>`.

The JupyterHub team and Project Jupyter value our community, and JupyterHub
follows the Jupyter `Community Guides <https://jupyter.readthedocs.io/en/latest/community/content-community.html>`_.

Contents
========

.. _index/distributions:

Distributions
-------------

As earlier mentioned, a JupyterHub **distribution** is tailored 
towards a particular set of use cases. These are generally easier 
to set up than setting up JupyterHub from scratch, assuming they fit your use case.

Today, you can find two main use cases:

1. If you need a simple case for a small amount of users (0-100) and single server
   take a look at
   `The Littlest JupyterHub <https://github.com/jupyterhub/the-littlest-jupyterhub>`__ distribution.
2. If you need to allow for a larger number of machines and users, 
   a dynamic amount of servers can be used on a cloud,
   take a look at the `Zero to JupyterHub with Kubernetes <https://github.com/jupyterhub/zero-to-jupyterhub-k8s>`__ distribution.
   This distribution runs JupyterHub on top of  `Kubernetes <https://k8s.io>`_.

*It is important to evaluate these distributions before you can continue with the 
configuration of the broad original system of* **JupyterHub**.


Installation Guide
------------------

.. toctree::
   :maxdepth: 2

   installation-guide

Getting Started
---------------

.. toctree::
   :maxdepth: 2

   getting-started/index

Technical Reference
-------------------

.. toctree::
   :maxdepth: 2

   reference/index

Administrators guide
--------------------

.. toctree::
   :maxdepth: 2

   index-admin

API Reference
-------------

.. toctree::
   :maxdepth: 2

   api/index

RBAC Reference
--------------

.. toctree::
   :maxdepth: 2

   rbac/index

Contributing
------------

We want you to contribute to JupyterHub in ways that are most exciting
& useful to you. We value documentation, testing, bug reporting & code equally,
and are glad to have your contributions in whatever form you wish :)

Our `Code of Conduct <https://github.com/jupyter/governance/blob/HEAD/conduct/code_of_conduct.md>`_ and `reporting guidelines <https://github.com/jupyter/governance/blob/HEAD/conduct/reporting_online.md>`_
help keep our community welcoming to as many people as possible.

.. toctree::
   :maxdepth: 2

   contributing/index

About JupyterHub
----------------

.. toctree::
   :maxdepth: 2

   index-about

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`


Questions? Suggestions?
=======================
All questions and suggestions are welcome. Please feel free to use our `Jupyter mailing list <https://groups.google.com/forum/#!forum/jupyter>`_ and `Jupyter website <https://jupyter.org>`_ to contact our team.

Looking forward to hearing from you!

.. _JupyterHub: https://github.com/jupyterhub/jupyterhub
.. _Jupyter notebook: https://jupyter-notebook.readthedocs.io/en/latest/
