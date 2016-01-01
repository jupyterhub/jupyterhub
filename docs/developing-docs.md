# Developing Documentation

## Goals of JupyterHub Documentation

Our goal when creating documentation is to give the developers and the
users of JupyterHub straightforward, accurate, and timely information. To be clear,
we define:

* straightforward as "enough text to be helpful but not so much as to
overwhelm the reader";
* accurate as "the information reflects the actual functioning of the project
components"
* timely as "up to date information for developers and early adopters on new
functionality and changes"

If you see typos, missing content, errors, or want to share content that you
created that may help the next user or developer, please share it with us by
opening an issue on GitHub or leaving a message in the Jupyter mailing list
and Google Group. We're doing our best to keep up with the exciting pace of the
project. With these changes, we're counting on you to tell us when we're missing
important items or even better to pay it forward and contribute to the
documentation and help future users.

Thanks and happy creating!

## Reading the documentation on the web

You have two options to read the docs on the web:

* read the files in the ``docs`` directory of the JupyterHub
repo on GitHub, or
* read the docs on "Read The Docs"

## Building documentation locally

1. Install python3
2. Clone JupyterHub repo from GitHub
3. pip (or conda) install packages listed in ``doc-requirements.txt``. For pip,
use ``pip install -r doc-requirements.txt`` from the ``jupyterhub`` directory.
4. Change directory to the root of the `docs` directory.
5. Run ``make clean``
6. Run ``make html``
7. View the Documentation
   - a) Run ``open/_build/html/index.html`` from the command line in ``docs``
   directory and the documentation should open to the table of contents in your
   browser
   - b) Run ``python -m http.server`` from the command line in ``docs`` directory
   and type ``http://_build/html/index.html`` into the browser.
