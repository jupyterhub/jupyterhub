.. _installation:

Installation
============

Dependencies
------------

JupyterHub requires IPython >= 3.0 (current master) and Python >= 3.3.

You will need nodejs/npm, which you can get from your package manager::

    sudo apt-get install npm nodejs-legacy

(The `nodejs-legacy` package installs the `node` executable,
which is required for npm to work on Debian/Ubuntu at this point)

Then install javascript dependencies::

    sudo npm install -g configurable-http-proxy

Optional
^^^^^^^^

Notes on `pip` command used in the below installation sections:

    * ``sudo`` may be needed for ``pip install``, depending on filesystem
      permissions.

    * JupyterHub requires Python >= 3.3, so it may be required on some
      machines to use ``pip3`` instead of ``pip`` (especially when you have
      both Python 2 and Python 3 installed on your machine). If ``pip3`` is
      not found on your machine, you can get it by doing::

          sudo apt-get install python3-pip


Installation
------------

JupyterHub can be installed with pip::

    pip3 install jupyterhub


If the ``pip3 install .`` command fails and complains about ``lessc`` being
unavailable, you may need to explicitly install some additional javascript
dependencies::

    npm install

If you plan to run notebook servers locally, you may also need to install
the Jupyter notebook::

    pip3 install jupyter

This will fetch client-side javascript dependencies and compile CSS,
and install these files to ``{sys.prefix}/share/jupyter``, as well as
install any Python dependencies.


Development install
^^^^^^^^^^^^^^^^^^^

Documentation for :ref:`development installation <dev-installation>` and
building the project from
source is found in the development installation document in section
:ref:`Install - cloning source and building <install-clone>`.


Running the server
------------------

To start the server, run the command::

    jupyterhub

and then visit ``http://localhost:8000``, and sign in with your unix
credentials.

If you want multiple users to be able to sign into the server, you will need
to run the ``jupyterhub`` command as a privileged user, such as root.

The `wiki <https://github.com/jupyter/jupyterhub/wiki/Using-sudo-to-run-JupyterHub-without-root-privileges>`_
describes how to run the server as a less privileged user, which requires
more configuration of the system.
