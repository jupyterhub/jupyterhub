.. _contributing/tests:

===================================
Testing JupyterHub and linting code
===================================

Unit testing helps to validate that JupyterHub works the way we think it does,
and continues to do so when changes occur. They also help communicate
precisely what we expect our code to do. 

JupyterHub uses `pytest <https://pytest.org>`_ for all the tests. You
can find them under the `jupyterhub/tests <https://github.com/jupyterhub/jupyterhub/tree/main/jupyterhub/tests>`_ directory in the git repository.

Running the tests
==================

#. Make sure you have completed :ref:`contributing/setup`. Once completed, you should be able
   to run ``jupyterhub`` on your command line and access JupyterHub from your browser at http://localhost:8000. Being able to run and access `jupyterhub` should mean that the dev environment is properly set
   up for tests to run.

#. You can run all tests in JupyterHub 

   .. code-block:: bash

      pytest -v jupyterhub/tests

   This should display progress as it runs all the tests, printing
   information about any test failures as they occur.
   
   If you wish to confirm test coverage the run tests with the `--cov` flag:

   .. code-block:: bash

      pytest -v --cov=jupyterhub jupyterhub/tests

#. You can also run tests in just a specific file:

   .. code-block:: bash

      pytest -v jupyterhub/tests/<test-file-name>

#. To run a specific test only, you can do:

   .. code-block:: bash

      pytest -v jupyterhub/tests/<test-file-name>::<test-name>

   This runs the test with function name ``<test-name>`` defined in
   ``<test-file-name>``. This is very useful when you are iteratively
   developing a single test.

   For example, to run the test ``test_shutdown`` in the file ``test_api.py``,
   you would run:

   .. code-block:: bash
      
      pytest -v jupyterhub/tests/test_api.py::test_shutdown

   For more information, refer to the `pytest usage documentation <https://pytest.readthedocs.io/en/latest/usage.html>`_.

Test organisation
=================

The tests live in ``jupyterhub/tests`` and are organized roughly into:

#. ``test_api.py`` tests the REST API
#. ``test_pages.py`` tests loading the HTML pages

and other collections of tests for different components.
When writing a new test, there should usually be a test of
similar functionality already written and related tests should
be added nearby.

The fixtures live in ``jupyterhub/tests/conftest.py``. There are
fixtures that can be used for JupyterHub components, such as:

- ``app``: an instance of JupyterHub with mocked parts
- ``auth_state_enabled``: enables persisting auth_state (like authentication tokens)
- ``db``: a sqlite in-memory DB session
- ``io_loop```: a Tornado event loop
- ``event_loop``: a new asyncio event loop
- ``user``: creates a new temporary user
- ``admin_user``: creates a new temporary admin user
- single user servers
  - ``cleanup_after``: allows cleanup of single user servers between tests
- mocked service
  - ``MockServiceSpawner``: a spawner that mocks services for testing with a short poll interval
  - ``mockservice```: mocked service with no external service url
  - ``mockservice_url``: mocked service with a url to test external services

And fixtures to add functionality or spawning behavior:

- ``admin_access``: grants admin access
- ``no_patience```: sets slow-spawning timeouts to zero
- ``slow_spawn``: enables the SlowSpawner (a spawner that takes a few seconds to start)
- ``never_spawn``: enables the NeverSpawner (a spawner that will never start)
- ``bad_spawn``: enables the BadSpawner (a spawner that fails immediately)
- ``slow_bad_spawn``: enables the SlowBadSpawner (a spawner that fails after a short delay)

For information on using the existing fixtures and creating new ones, refer to the `pytest fixtures documentation <https://pytest.readthedocs.io/en/latest/fixture.html>`_


Troubleshooting Test Failures
=============================

All the tests are failing
-------------------------

Make sure you have completed all the steps in :ref:`contributing/setup` successfully, and are able to access JupyterHub from your browser at http://localhost:8000 after starting ``jupyterhub`` in your command line.


Code formatting and linting
===========================

JupyterHub automatically enforces code formatting. This means that pull requests
with changes breaking this formatting will receive a commit from pre-commit.ci
automatically.

To automatically format code locally, you can install pre-commit and register a
*git hook* to automatically check with pre-commit before you make a commit if
the formatting is okay.

.. code:: bash

   pip install pre-commit
   pre-commit install --install-hooks

To run pre-commit manually you would do:

.. code:: bash

   # check for changes to code not yet committed
   pre-commit run

   # check for changes also in already committed code
   pre-commit run --all-files

You may also install `black integration <https://github.com/psf/black#editor-integration>`_
into your text editor to format code automatically.
