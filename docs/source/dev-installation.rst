.. _dev-installation:

Development Installation
========================

These installation instructions have been created for individuals that wish
develop for JupyterHub or build the project from source.

Dependencies
------------

JupyterHub requires IPython >= 3.0 (current master) and Python >= 3.3.

You will need nodejs/npm, which you can get from your package manager:

    sudo apt-get install npm nodejs-legacy

(The `nodejs-legacy` package installs the `node` executable,
which is required for npm to work on Debian/Ubuntu at this point)

Then install javascript dependencies:

    sudo npm install -g configurable-http-proxy

Optional
~~~~~~~~

* Notes on `pip` command used in the below installation sections:

    - `sudo` may be needed for `pip install`, depending on filesystem permissions.
    - JupyterHub requires Python >= 3.3, so it may be required on some machines to
      use `pip3` instead of `pip` (especially when you have both Python 2 and
      Python 3 installed on your machine).

      If `pip3` is not found on your machine, you can get it by doing:

          sudo apt-get install python3-pip

.. _install-clone:

Install - Cloning source and building
-------------------------------------

For a development install, clone the repository and then install from source::

    git clone https://github.com/jupyter/jupyterhub
    cd jupyterhub
    pip3 install -r dev-requirements.txt -e .

In which case you may need to manually update javascript and css after some updates, with::

    python3 setup.py js    # fetch updated client-side js (changes rarely)
    python3 setup.py css   # recompile CSS from LESS sources


Running the server
------------------

To start the server, run the command:

    jupyterhub

and then visit `http://localhost:8000`, and sign in with your unix credentials.

If you want multiple users to be able to sign into the server, you will need to run the
`jupyterhub` command as a privileged user, such as root.

The [wiki](https://github.com/jupyter/jupyterhub/wiki/Using-sudo-to-run-JupyterHub-without-root-privileges)
describes how to run the server
as a less privileged user, which requires more configuration of the system.
