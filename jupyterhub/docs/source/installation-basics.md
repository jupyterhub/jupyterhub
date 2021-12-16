# Installation Basics

## Platform support

JupyterHub is supported on Linux/Unix based systems. To use JupyterHub, you need
a Unix server (typically Linux) running somewhere that is accessible to your
team on the network. The JupyterHub server can be on an internal network at your
organization, or it can run on the public internet (in which case, take care
with the Hub's [security](./getting-started/security-basics)).

JupyterHub officially **does not** support Windows. You may be able to use
JupyterHub on Windows if you use a Spawner and Authenticator that work on
Windows, but the JupyterHub defaults will not. Bugs reported on Windows will not
be accepted, and the test suite will not run on Windows. Small patches that fix
minor Windows compatibility issues (such as basic installation) **may** be accepted,
however. For Windows-based systems, we would recommend running JupyterHub in a
docker container or Linux VM.

[Additional Reference:](http://www.tornadoweb.org/en/stable/#installation)
Tornado's documentation on Windows platform support

## Planning your installation

Prior to beginning installation, it's helpful to consider some of the following:

- deployment system (bare metal, Docker)
- Authentication (PAM, OAuth, etc.)
- Spawner of singleuser notebook servers (Docker, Batch, etc.)
- Services (nbgrader, etc.)
- JupyterHub database (default SQLite; traditional RDBMS such as PostgreSQL,)
  MySQL, or other databases supported by [SQLAlchemy](http://www.sqlalchemy.org))

## Folders and File Locations

It is recommended to put all of the files used by JupyterHub into standard
UNIX filesystem locations.

- `/srv/jupyterhub` for all security and runtime files
- `/etc/jupyterhub` for all configuration files
- `/var/log` for log files
