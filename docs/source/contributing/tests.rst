.. _contributing/tests:

==================
Testing JupyterHub
==================

Unit test help validate that JupyterHub works the way we think it does,
and continues to do so when changes occur. They also help communicate
precisely what we expect our code to do. 

JupyterHub uses `pytest <https://pytest.org>`_ for all our tests. You
can find them under ``jupyterhub/tests`` directory in the git repository.

Running the tests
==================

#. Make sure you have completed :ref:`contributing/setup`. You should be able
   to start ``jupyterhub`` from the commandline & access it from your
   web browser. This ensures that the dev environment is properly set
   up for tests to run.

#. You can run all tests in JupyterHub 

   .. code-block:: bash

      pytest --async-test-timeout 15 -v jupyterhub/tests

   This should display progress as it runs all the tests, printing
   information about any test failures as they occur.

   The ``--async-test-timeout`` parameter is used by `pytest-tornado
   <https://github.com/eugeniy/pytest-tornado#markers>`_ to set the
   asynchronous test timeout to 15 seconds rather than the default 5,
   since some of our tests take longer than 5s to execute.

#. You can also run tests in just a specific file:

   .. code-block:: bash

      pytest --async-test-timeout 15 -v jupyterhub/tests/<test-file-name>

#. To run a specific test only, you can do:

   .. code-block:: bash

      pytest --async-test-timeout 15 -v jupyterhub/tests/<test-file-name>::<test-name>

   This runs the test with function name ``<test-name>`` defined in
   ``<test-file-name>``. This is very useful when you are iteratively
   developing a single test.

   For example, to run the test ``test_shutdown`` in the file ``test_api.py``,
   you would run:

   .. code-block:: bash
      
      pytest -v jupyterhub/tests/test_api.py::test_shutdown


Troubleshooting Test Failures
=============================

All the tests are failing
-------------------------

Make sure you have completed all the steps in :ref:`contributing/setup` sucessfully, and
can launch ``jupyterhub`` from the terminal.

Tests are timing out
--------------------

The ``--async-test-timeout`` parameter to ``pytest`` is used by
`pytest-tornado <https://github.com/eugeniy/pytest-tornado#markers>`_ to set
the asynchronous test timeout to a higher value than the default of 5s,
since some of our tests take longer than 5s to execute. If the tests
are still timing out, try increasing that value even more. You can
also set an environment variable ``ASYNC_TEST_TIMEOUT`` instead of
passing ``--async-test-timeout`` to each invocation of pytest.