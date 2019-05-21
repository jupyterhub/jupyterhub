.. _admin/upgrading:

====================
Upgrading JupyterHub
====================

JupyterHub offers easy upgrade pathways between minor versions. This
document describes how to do these upgrades.

If you are using :ref:`a JupyterHub distribution <index/distributions>`, you
should consult the distribution's documentation on how to upgrade. This
document is if you have set up your own JupyterHub without using a
distribution.

It is long because is pretty detailed! Most likely, upgrading
JupyterHub is painless, quick and with minimal user interruption.

Read the Changelog
==================

The `changelog <../changelog.html>`_ contains information on what has
changed with the new JupyterHub release, and any deprecation warnings.
Read these notes to familiarize yourself with the coming changes. There
might be new releases of authenticators & spawners you are using, so
read the changelogs for those too!

Notify your users
=================

If you are using the default configuration where ``configurable-http-proxy``
is managed by JupyterHub, your users will see service disruption during
the upgrade process. You should notify them, and pick a time to do the
upgrade where they will be least disrupted.

If you are using a different proxy, or running ``configurable-http-proxy``
independent of JupyterHub, your users will be able to continue using notebook
servers they had already launched, but will not be able to launch new servers
nor sign in.


Backup database & config
========================

Before doing an upgrade, it is critical to back up:

#. Your JupyterHub database (sqlite by default, or MySQL / Postgres
   if you used those). If you are using sqlite (the default), you
   should backup the ``jupyterhub.sqlite`` file.
#. Your ``jupyterhub_config.py`` file.
#. Your user's home directories. This is unlikely to be affected directly by
   a JupyterHub upgrade, but we recommend a backup since user data is very
   critical.


Shutdown JupyterHub
===================

Shutdown the JupyterHub process. This would vary depending on how you
have set up JupyterHub to run. Most likely, it is using a process
supervisor of some sort (``systemd`` or ``supervisord`` or even ``docker``).
Use the supervisor specific command to stop the JupyterHub process.

Upgrade JupyterHub packages
===========================

There are two environments where the ``jupyterhub`` package is installed:

#. The *hub environment*, which is where the JupyterHub server process
   runs. This is started with the ``jupyterhub`` command, and is what
   people generally think of as JupyterHub.

#. The *notebook user environments*. This is where the user notebook
   servers are launched from, and is probably custom to your own
   installation. This could be just one environment (different from the
   hub environment) that is shared by all users, one environment
   per user, or same environment as the hub environment. The hub
   launched the ``jupyterhub-singleuser`` command in this environment,
   which in turn starts the notebook server.

You need to make sure the version of the ``jupyterhub`` package matches
in both these environments. If you installed ``jupyterhub`` with pip,
you can upgrade it with:

.. code-block:: bash

   python3 -m pip install --upgrade jupyterhub==<version>

Where ``<version>`` is the version of JupyterHub you are upgrading to.

If you used ``conda`` to install ``jupyterhub``, you should upgrade it
with:

.. code-block:: bash

   conda install -c conda-forge jupyterhub==<version>

Where ``<version>`` is the version of JupyterHub you are upgrading to.

You should also check for new releases of the authenticator & spawner you
are using. You might wish to upgrade those packages too along with JupyterHub,
or upgrade them separately.

Upgrade JupyterHub database
===========================

Once new packages are installed, you need to upgrade the JupyterHub
database. From the hub environment, in the same directory as your
``jupyterhub_config.py`` file, you should run:

.. code-block:: bash

   jupyterhub upgrade-db

This should find the location of your database, and run necessary upgrades
for it.

SQLite database disadvantages
-----------------------------

SQLite has some disadvantages when it comes to upgrading JupyterHub. These
are:

-  ``upgrade-db`` may not work, and you may need delete your database
   and start with a fresh one.
-  ``downgrade-db`` **will not** work if you want to rollback to an
   earlier version, so backup the ``jupyterhub.sqlite`` file before
   upgrading

What happens if I delete my database?
-------------------------------------

Losing the Hub database is often not a big deal. Information that
resides only in the Hub database includes:

-  active login tokens (user cookies, service tokens)
-  users added via JupyterHub UI, instead of config files
-  info about running servers

If the following conditions are true, you should be fine clearing the
Hub database and starting over:

-  users specified in config file, or login using an external
   authentication provider (Google, GitHub, LDAP, etc)
-  user servers are stopped during upgrade
-  don't mind causing users to login again after upgrade

Start JupyterHub
================

Once the database upgrade is completed, start the ``jupyterhub``
process again.

#. Log-in and start the server to make sure things work as
   expected.
#. Check the logs for any errors or deprecation warnings. You
   might have to update your ``jupyterhub_config.py`` file to
   deal with any deprecated options.

Congratulations, your JupyterHub has been upgraded!
