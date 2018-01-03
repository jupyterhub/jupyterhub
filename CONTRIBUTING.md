# Contributing

Welcome! As a [Jupyter](https://jupyter.org) project, we follow the [Jupyter contributor guide](https://jupyter.readthedocs.io/en/latest/contributor/content-contributor.html).

## Set up your development system

For a development install, clone the [repository](https://github.com/jupyterhub/jupyterhub)
and then install from source:

```bash
git clone https://github.com/jupyterhub/jupyterhub
cd jupyterhub
npm install -g configurable-http-proxy
pip3 install -r dev-requirements.txt -e .
```

### Troubleshooting a development install

If the `pip3 install` command fails and complains about `lessc` being
unavailable, you may need to explicitly install some additional JavaScript
dependencies:

    npm install

This will fetch client-side JavaScript dependencies necessary to compile CSS.

You may also need to manually update JavaScript and CSS after some development
updates, with:

```bash
python3 setup.py js    # fetch updated client-side js
python3 setup.py css   # recompile CSS from LESS sources
```

## Running the test suite

We use [pytest](http://doc.pytest.org/en/latest/) for running tests. Set up a
development install as described above. To run all the tests:

```bash
pytest jupyterhub/tests
```

To run an individual test file (i.e. `test_api.py`):

```bash
pytest jupyterhub/tests/test_api.py
```

### Troubleshooting tests

If you see test failures because of timeouts, you may wish to increase the
`ASYNC_TEST_TIMEOUT` used by the
[pytest-tornado-plugin](https://github.com/eugeniy/pytest-tornado/blob/c79f68de2222eb7cf84edcfe28650ebf309a4d0c/README.rst#markers)
from the default of 5 seconds:

```bash
export ASYNC_TEST_TIMEOUT=15
```

If you see many test errors and failures, double check that you have installed
`configurable-http-proxy`.

## Building the Docs locally

Install the dependencies:

```bash
python3 -m pip install -r docs/requirements.txt
```

Build the docs:

```bash
cd docs
make clean
make html
```
