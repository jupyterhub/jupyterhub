==========
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

The JupyterHub team and Project Jupyter value our community, and JupyterHub
follows the Jupyter [Community Guides](https://jupyter.readthedocs.io/en/latest/community/content-community.html).

Contents
========

Installation Guide
------------------

.. toctree::
   :maxdepth: 1

   installation-guide
   quickstart
   quickstart-docker
   installation-basics

Getting Started
---------------

.. toctree::
   :maxdepth: 1

   getting-started/index
   getting-started/config-basics
   getting-started/networking-basics
   getting-started/security-basics
   getting-started/authenticators-users-basics
   getting-started/spawners-basics
   getting-started/services-basics

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   reference/index
   reference/technical-overview
   reference/websecurity
   reference/authenticators
   reference/spawners
   reference/services
   reference/rest
   reference/upgrading
   reference/templates
   reference/config-user-env
   reference/config-examples
   reference/config-ghoauth
   reference/config-proxy
   reference/config-sudo

Contributing
------------

We want you to contribute to JupyterHub in ways that are most exciting
& useful to you. We value documentation, testing, bug reporting & code equally,
and are glad to have your contributions in whatever form you wish :)

Our `Code of Conduct <https://github.com/jupyter/governance/blob/master/conduct/code_of_conduct.md>`_
(`reporting guidelines <https://github.com/jupyter/governance/blob/master/conduct/reporting_online.md>`_)
helps keep our community welcoming to as many people as possible.

.. toctree::
   :maxdepth: 1

   contributing/community
   contributing/setup
   contributing/docs
   contributing/tests


API Reference
-------------

.. toctree::
   :maxdepth: 1

   api/index

Tutorials
---------

.. toctree::
   :maxdepth: 1

   tutorials/index
   tutorials/upgrade-dot-eight

Distributions
-------------

A JupyterHub **distribution** is tailored towards a particular set of
use cases. These are generally easier to set up than setting up
JupyterHub from scratch, assuming they fit your use case.

The two popular ones are:

* `Zero to JupyterHub on Kubernetes <http://z2jh.jupyter.org>`_, for
  running JupyterHub on top of `Kubernetes <https://k8s.io>`_. This
  can scale to large number of machines & users.
* `The Littlest JupyterHub <http://tljh.jupyter.org>`_, for an easy
  to set up & run JupyterHub supporting 1-100 users on a single machine.

Troubleshooting
---------------

.. toctree::
   :maxdepth: 1

   troubleshooting

About JupyterHub
----------------

.. toctree::
   :maxdepth: 1

   contributor-list
   changelog
   gallery-jhub-deployments

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`


Questions? Suggestions?
=======================

- `Jupyter mailing list <https://groups.google.com/forum/#!forum/jupyter>`_
- `Jupyter website <https://jupyter.org>`_

.. _contents:

Full Table of Contents
======================

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
