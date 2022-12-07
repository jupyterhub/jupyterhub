===============================
Layout of JupyterHub Repository
===============================

This page covers the layout and structure of the JupyterHub repository. It provides brief information on the purpose of the various files and directories in the repository. Please consult JupyterHub documentation for more details.


Directory Structure
===================

ci/
    This directory contains files for automating aspects of the continuous integration pipeline of the JupterHub project; some of which includes checking distribution packages to ensure they contain all expected files.

demo-image/
    This directory contains a Dockerfile for building a JupyterHub image meant for demo or testing purposes only. You can check out the `README` file in the directory for more details.

dockerfiles/
    This directory contains the Dockerfile for building the JupyterHub base image. You can check out the `README` in the directory for more details.

docs/
    This directory contains the documentation files for the JupyterHub project.

examples/
    This directory details several services provided by the JupyterHub project, alongside their configurations to enable you configure JupyterHub to use those services.

jsx/
    This directory contains javascript sources for the JupyterHub Admin Dashboard.

JupyterHub/
    This directory contains the core code files for the JupyterHub project. For developers contributing to the codebase, here is a layout of the directory:

    alembic/
        This is the alembic configuration for JupyterHub database migrations.

    apihandlers/
        This sub-directory contains all API handler modules. This includes the authorization handlers, group handlers, API handlers for JupyterHub adminstration, proxy handlers, services handlers and user handlers.

    event-schemas/server-actions/
        This sub-directory contains the schema used by JupyterHub in recording operations performed by JupyterHub on user servers.

    handlers/
        This sub-directory contains the HTTP handlers for the hub servers. It contains other handlers: basic HTML-rendering handlers, handlers for serving prometheus metrics, and static files handlers.

    oauth/
        This sub-directory contains the utilities for hooking up `oauth2` with the JupyterHub's database.

    services/
        This sub-directory contains the modules for authenticating and managing services.

    singleuser/
        This sub-directory contains the entrypoints for JupyterHub single-user server. It also contains default notebook-app subclass and mixins.

    tests/
        This sub-directory contains the tests for all modules in the JupyterHub directory.

    _init_.py
        A python package indicator.

    _main_.py
        The main entrypoint for the execution of python modules.

    _data.py   
        The module file for getting JupyterHub data and static files.

    _memoize.py 
        The utility module file for memoization.

    _version.py
        The module file for obtaining information on JupyterHub version.

    alembic.ini
        A generic, single database configuration file.

    app.py  
        The multi-user notebook application module.
        
    auth.py
        This module contains the authenticator classes: base Authenticator class, the (default) PAM Authenticator, Local Authenticator, Null Authenticator, and Dummy Authenticator.

    crypto.py
        The module on cryptography and encryption configuration.

    dbutil.py
        The database utility module for JupyterHub.

    emptyclass.py
        This module contains an empty class.

    log.py
        The logging utility module file for JupyterHub.

    metrics.py  
        The module used by JupyterHub for exporting Prometheus metrics.

    objects.py  
        This module contains generic objects(Server & Hub) used by JupyterHub.
        
    orm.py  
        This module contains the JupyterHub database-related code.

    proxy.py
        This module contains the API for JupyterHub's proxy.

    roles.py
        The roles (users, admins, server, & token) utility module for JupyterHub.

    scopes.py
        This module contains scope definitions and utilities.

    spawner.py
        This modules contains the base spawner class and its default implementation.

    traitlets.py
        This module contains traitlets used by JupyterHub.

    user.py
        The User object module.

    utils.py
        This module contains miscellaneous utilities.        

onbuild/
    This directory contains the Dockerfile for building a JupyterHub image. Specifically, it would include the configuration file(`JupyterHub_config.py`) in the image build.

share/jupyterHub/
    This directory contains JupyterHub data and static files.

singleuser/
    This directory contains the Dockerfile for building a JupyterHub image for a single user. You can check out the `README` in the directory for more details.

testing/
    This directory contains a sample JupyterHub configuration file for testing.

Executable files
================

setup.py
    The packaging file for the JupyterHub codebase. It is used in building the JupyterHub distribution package. It contains information on the name, version, data files, package files, python version requirement, entry points, and the dependencies of the JupyterHub codebase. 

Dockerfile
    The Dockerfile containing the base image for running JupyterHub.

bower-lite
    Another components file used in packaging JupyterHub. It stages the frontend dependencies of the JupyterHub repository from the node_modules directory into the components sub-directory. Check the static directory in the `share/jupyterHub` directory to find the components sub-directory.

package.json
    This file contains information on JupyterHub nodejs dependencies.

pytest.ini
    A configuration file for customizing Pytest behaviors to suit the usage of Pytest in the JupyterHub project. Pytest is a python tool for running tests.

pyproject.toml
    A file for configuring code formatting and release tools(tbump).

MANIFEST.in
    A file for instructing setuptools on the files to add or remove when building the JupyterHub distribution package (sdist).

requirements.txt
    This file lists the dependencies of the JupyterHub codebase.

dev-requirements.txt
    This file lists the testing/development dependencies of the JupyterHub codebase.


Informational Files
===================

README
    Read the README! Read it first.

    This file contains the minimum documentation to help you get started with the JupyterHub project. It covers installations, some notes on contribution, and a list of help and resources. It points to the main documentation of the project.

CODE_OF_CONDUCT.md
    This file links to Project Jupyter's code of conduct.

CONTRIBUTING.md
    This file points to the JupyterHub contribution guidelines and other resources such as setting up a developmental install to help new contributors get started making contribution to the project.

COPYING.md
    This file contains the JupyterHub license information. It explains the permission you have using source code from the repository.

RELEASE.md
    This file provides information on making releases of the JupyterHub project.

SECURITY.md
    This file provides information on how to report an identified security vulnerability in the JupyterHub project.


dotfiles
========

The dotfiles contained in the repository provide configuration details. They are as follows:

.coveragerc
    A configuration file for coverage testing.
    
.dockerignore
    A file containing files ignored by Docker from the build context.

.github
    A file containing the pull request template and workflows specific to the JupyterHub repository.

.gitignore
    A file containing JupyterHub project files ignored by Git.
        
.prettierignore
    A file containing files to be ignored by Prettier(a code formatting tool).
    
.pre-commit-config.yaml
    A pre-commit configuration file. Pre-commit is a tool to perform a predefined set of tasks manually and/or automatically before git commits are made.

.flake8
    A linting configuration file for Flake8.

.readthedocs.yaml
    The configuration file for JupyterHub documentation host(Read the Docs).
