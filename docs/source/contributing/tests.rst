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


Troubleshooting Test Failures
=============================

All the tests are failing
-------------------------

Make sure you have completed all the steps in :ref:`contributing/setup` successfully, and
can launch ``jupyterhub`` from the terminal.
