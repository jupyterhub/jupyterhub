.. _upgrade-dot-eight:

Upgrading to JupyterHub version 0.8
===================================

This document will assist you in upgrading an existing JupyterHub deployment
from version 0.7 to version 0.8.

Upgrade checklist
-----------------

0. Review the release notes. Review any deprecated features and pay attention
   to any backwards incompatible changes
1. Backup JupyterHub database:
    - ``jupyterhub.sqlite`` when using the default sqlite database
    - Your JupyterHub database when using an RDBMS
2. Backup the existing JupyterHub configuration file: ``jupyterhub_config.py``
3. Shutdown the Hub
4. Upgrade JupyterHub
    - ``pip install -U jupyterhub`` when using ``pip``
    - ``conda upgrade jupyterhub`` when using ``conda``
5. Upgrade the database using run ```jupyterhub upgrade-db``
6. Update the JupyterHub configuration file ``jupyterhub_config.py``

Backup JupyterHub database
--------------------------

To prevent unintended loss of data or configuration information, you should
back up the JupyterHub database (the default SQLite database or a RDBMS
database using PostgreSQL, MySQL, or others supported by SQLAlchemy):

- If using the default SQLite database, back up the ``jupyterhub.sqlite``
  database.
- If using an RDBMS database such as PostgreSQL, MySQL, or other supported by
  SQLAlchemy, back up the JupyterHub database.

.. note::

    Losing the Hub database is often not a big deal. Information that resides only
    in the Hub database includes:

    - active login tokens (user cookies, service tokens)
    - users added via GitHub UI, instead of config files
    - info about running servers

    If the following conditions are true, you should be fine clearing the Hub
    database and starting over:

    - users specified in config file
    - user servers are stopped during upgrade
    - don't mind causing users to login again after upgrade

Backup JupyterHub configuration file
------------------------------------

Backup up your configuration file, ``jupyterhub_config.py``, to a secure
location.

Shutdown JupyterHub
-------------------

- Prior to shutting down JupyterHub, you should notify the Hub users of the
  scheduled downtime.
- Shutdown the JupyterHub service.

Upgrade JupyterHub
------------------

Follow directions that correspond to your package manager, ``pip`` or ``conda``,
for the new JupyterHub release:

- ``pip install -U jupyterhub`` for ``pip``
- ``conda upgrade jupyterhub`` for ``conda``

Upgrade the proxy, authenticator, or spawner if needed.

Upgrade JupyterHub database
---------------------------

To run the upgrade process for JupyterHub databases, enter::

    jupyterhub upgrade-db

Update the JupyterHub configuration file
----------------------------------------

Create a new JupyterHub configuration file or edit a copy of the existing
file ``jupyterhub_config.py``.

Start JupyterHub
----------------

Start JupyterHub with the same command that you used before the upgrade.