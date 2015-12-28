Getting started with JupyterHub
===============================

This document covers the basics of configuring JupyterHub to
do what you want. JupyterHub is highly customizable, and it may be
configured via the command line or a configuration file.

Prerequisite: Installation
--------------------------

See :ref:`Installation documentation <installation>` or the
`readme <https://github.com/jupyter/jupyterhub>`_
for help installing JupyterHub.

Overview
--------

JupyterHub is a set of processes that together provide a multiuser
Jupyter Notebook server. There are three main categories of processes
run by the ``jupyterhub`` command line program:

-  *Single User Server*: a dedicated, single-user, Jupyter Notebook is
   started for each user on the system when they log in. The object that
   starts these processes is called a *Spawner*.
-  *Proxy*: the public facing part of the server that uses a dynamic
   proxy to route HTTP requests to the *Hub* and *Single User Servers*.
-  *Hub*: manages user accounts and authentication and coordinates
   *Single Users Servers* using a *Spawner*.

JupyterHub's default configuration
----------------------------------

To start JupyterHub in its default configuration, type the following at
the command line:

::

    sudo jupyterhub

The default Authenticator that ships with JupyterHub authenticates users
with their system name and password (via
`PAM <http://en.wikipedia.org/wiki/Pluggable_authentication_module>`__).
Any user on the system with a password will be allowed to start a
single-user notebook server.

The default Spawner starts servers locally as each user, one dedicated
server per user. These servers listen on localhost, and start in the
given user's home directory.

By default, the *Proxy* listens on all public interfaces on port 8000.
Thus you can reach JupyterHub through:

::

    http://localhost:8000

or any other public IP or domain pointing to your system.

In their default configuration, the other services, the *Hub* and
*Single-User Servers*, all communicate with each other on localhost
only.

**NOTE:** In its default configuration, JupyterHub runs without SSL
encryption (HTTPS). You should not run JupyterHub without SSL encryption
on a public network. See `below <#Security>`__ for how to configure
JupyterHub to use SSL.

By default, starting JupyterHub will write two files to disk in the
current working directory:

-  ``jupyterhub.sqlite`` is the sqlite database containing all of the
   state of the *Hub*. This file allows the *Hub* to remember what users
   are running and where, as well as other information enabling you to
   restart parts of JupyterHub separately.
-  ``jupyterhub_cookie_secret`` is the encryption key used for securing
   cookies. This file needs to persist in order for restarting the Hub
   server to avoid invalidating cookies. Conversely, deleting this file
   and restarting the server effectively invalidates all login cookies.
   The cookie secret file is discussed `below <#Security>`__.

The location of these files can be specified via configuration,
discussed below.

How to configure JupyterHub
---------------------------

JupyterHub is configured in two ways:

1. Command-line arguments
2. Configuration files

Command-line arguments
^^^^^^^^^^^^^^^^^^^^^^
Type the following for brief information about the command line
arguments:

::

    jupyterhub -h

or:

::

    jupyterhub --help-all

for the full command line help.

Configuration files
^^^^^^^^^^^^^^^^^^^
By default, JupyterHub will look for a configuration file (can be
missing) named ``jupyterhub_config.py`` in the current working
directory. You can create an empty configuration file with

::

    jupyterhub --generate-config

This empty configuration file has descriptions of all configuration
variables and their default values. You can load a specific config file
with:

::

    jupyterhub -f /path/to/jupyterhub_config.py

See also: `general
docs <http://ipython.org/ipython-doc/dev/development/config.html>`__ on
the config system Jupyter uses.

