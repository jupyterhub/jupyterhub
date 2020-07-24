.. _contributing/setup:

================================
Setting up a development install
================================

System requirements
===================

JupyterHub can only run on MacOS or Linux operating systems. If you are
using Windows, we recommend using `VirtualBox <https://virtualbox.org>`_
or a similar system to run `Ubuntu Linux <https://ubuntu.com>`_ for
development.

Install Python
--------------

JupyterHub is written in the `Python <https://python.org>`_ programming language, and
requires you have at least version 3.5 installed locally. If you haven’t
installed Python before, the recommended way to install it is to use
`miniconda <https://conda.io/miniconda.html>`_. Remember to get the ‘Python 3’ version,
and **not** the ‘Python 2’ version!

Install nodejs
--------------

``configurable-http-proxy``, the default proxy implementation for
JupyterHub, is written in Javascript to run on `NodeJS
<https://nodejs.org/en/>`_. If you have not installed nodejs before, we
recommend installing it in the ``miniconda`` environment you set up for
Python. You can do so with ``conda install nodejs``.

Install git
-----------

JupyterHub uses `git <https://git-scm.com>`_ & `GitHub <https://github.com>`_
for development & collaboration. You need to `install git
<https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`_ to work on
JupyterHub. We also recommend getting a free account on GitHub.com.

Setting up a development install
================================

When developing JupyterHub, you need to make changes to the code & see
their effects quickly. You need to do a developer install to make that
happen.

.. note:: This guide does not attempt to dictate *how* development
   environements should be isolated since that is a personal preference and can
   be achieved in many ways, for example `tox`, `conda`, `docker`, etc. See this
   `forum thread <https://discourse.jupyter.org/t/thoughts-on-using-tox/3497>`_ for
   a more detailed discussion.

1. Clone the `JupyterHub git repository <https://github.com/jupyterhub/jupyterhub>`_
   to your computer.

   .. code:: bash

      git clone https://github.com/jupyterhub/jupyterhub
      cd jupyterhub

2. Make sure the ``python`` you installed and the ``npm`` you installed
   are available to you on the command line.

   .. code:: bash

      python -V

   This should return a version number greater than or equal to 3.5.

   .. code:: bash

      npm -v

   This should return a version number greater than or equal to 5.0.

3. Install ``configurable-http-proxy``. This is required to run
   JupyterHub.

   .. code:: bash

      npm install -g configurable-http-proxy

   If you get an error that says ``Error: EACCES: permission denied``,
   you might need to prefix the command with ``sudo``. If you do not
   have access to sudo, you may instead run the following commands:

   .. code:: bash

      npm install configurable-http-proxy
      export PATH=$PATH:$(pwd)/node_modules/.bin

   The second line needs to be run every time you open a new terminal.

4. Install the python packages required for JupyterHub development.

   .. code:: bash

      python3 -m pip install -r dev-requirements.txt
      python3 -m pip install -r requirements.txt

5. Setup a database.

   The default database engine is ``sqlite`` so if you are just trying
   to get up and running quickly for local development that should be
   available via `python <https://docs.python.org/3.5/library/sqlite3.html>`__.
   See :doc:`/reference/database` for details on other supported databases.

6. Install the development version of JupyterHub. This lets you edit
   JupyterHub code in a text editor & restart the JupyterHub process to
   see your code changes immediately.

   .. code:: bash

      python3 -m pip install --editable .

7. You are now ready to start JupyterHub!

   .. code:: bash

      jupyterhub

8. You can access JupyterHub from your browser at
   ``http://localhost:8000`` now.

Happy developing!

Using DummyAuthenticator & SimpleLocalProcessSpawner
====================================================

To simplify testing of JupyterHub, it’s helpful to use
:class:`~jupyterhub.auth.DummyAuthenticator` instead of the default JupyterHub
authenticator and SimpleLocalProcessSpawner instead of the default spawner.

There is a sample configuration file that does this in
``testing/jupyterhub_config.py``. To launch jupyterhub with this
configuration:

.. code:: bash

   jupyterhub -f testing/jupyterhub_config.py

The default JupyterHub `authenticator
<https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html#the-default-pam-authenticator>`_
& `spawner
<https://jupyterhub.readthedocs.io/en/stable/api/spawner.html#localprocessspawner>`_
require your system to have user accounts for each user you want to log in to
JupyterHub as.

DummyAuthenticator allows you to log in with any username & password,
while SimpleLocalProcessSpawner allows you to start servers without having to
create a unix user for each JupyterHub user. Together, these make it
much easier to test JupyterHub.

Tip: If you are working on parts of JupyterHub that are common to all
authenticators & spawners, we recommend using both DummyAuthenticator &
SimpleLocalProcessSpawner. If you are working on just authenticator related
parts, use only SimpleLocalProcessSpawner. Similarly, if you are working on
just spawner related parts, use only DummyAuthenticator.

Troubleshooting
===============

This section lists common ways setting up your development environment may
fail, and how to fix them. Please add to the list if you encounter yet
another way it can fail!

``lessc`` not found
-------------------

If the ``python3 -m pip install --editable .`` command fails and complains about
``lessc`` being unavailable, you may need to explicitly install some
additional JavaScript dependencies:

.. code:: bash

   npm install

This will fetch client-side JavaScript dependencies necessary to compile
CSS.

You may also need to manually update JavaScript and CSS after some
development updates, with:

.. code:: bash

   python3 setup.py js    # fetch updated client-side js
   python3 setup.py css   # recompile CSS from LESS sources
