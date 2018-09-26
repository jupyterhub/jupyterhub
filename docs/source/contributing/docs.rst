.. _contributing/docs:

==========================
Contributing Documentation
==========================

Documentation is often more important than code. This page helps
you get set up on how to contribute documentation to JupyterHub.

Building documentation locally
==============================


We use `sphinx <http://sphinx-doc.org>`_ to build our documentation. It takes
our documentation source files (written in `markdown
<https://daringfireball.net/projects/markdown/>`_ or `reStructuredText
<http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_ &
stored under the ``docs/source`` directory) and converts it into various
formats for people to read. To make sure the documentation you write or
change renders correctly, it is good practice to test it locally.

#. Make sure you have successfuly completed :ref:`contributing/setup`.

#. Install the packages required to build the docs.

   .. code-block:: bash

      pip install -r docs/requirements.txt

#. Build the html version of the docs. This is the most commonly used
   output format, so verifying it renders as you should is usually good
   enough.

   .. code-block:: bash

      cd docs
      make html

   This step will display any syntax or formatting errors in the documentation,
   along with the filename / line number in which they occurred. Fix them,
   and re-run the ``make html`` command to re-render the documentation.

#. View the rendered documentation by opening ``build/html/index.html`` in 
   a web browser. 

   .. tip::

      On macOS, you can open a file from the terminal with ``open <path-to-file>``.
      On Linux, you can do the same with ``xdg-open <path-to-file>``.