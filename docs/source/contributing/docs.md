(contributing:docs)=

# Contributing Documentation

Documentation is often more important than code. This page helps
you get set up on how to contribute to JupyterHub's documentation.

We use [Sphinx](https://www.sphinx-doc.org) to build our documentation. It takes
our documentation source files (written in [Markedly Structured Text (MyST)](https://mystmd.org/) and
stored under the `docs/source` directory) and converts it into various
formats for people to read.

## Building documentation locally

To make sure the documentation you write or
change renders correctly, it is good practice to test it locally.

```{note}
You will need Python and Git installed. Installation details are avaiable at {ref}`contributing:setup`.
```

### Building with `nox`

We use [the `nox` command line tool](https://nox.thea.codes/en/stable/) to automate the build documentation locally across all JupyterHub projects.

**To install the requirements for documentation, build them locally, and have a live preview**, run

```bash
nox -s docs -- live
```

For other use cases, visit [Building with nox](https://compass.hub.jupyter.org/contribute/documentation/#building-with-nox) from [JupyterHub Team Compass].

### Building without `nox`

First, install the packages required to build the documentation:

```bash
python3 -m pip install --editable .
python3 -m pip install -r docs/requirements.txt
```

Visit [Building with `Makefile`s](https://compass.hub.jupyter.org/contribute/documentation/#building-with-makefiles) and [Building with `sphinx-build`](https://compass.hub.jupyter.org/contribute/documentation/#building-with-sphinx-build) from [JupyterHub Team Compass].

(contributing-docs-conventions)=

## Documentation conventions

This section lists various conventions we use in our documentation. This is a
living document that grows over time, so feel free to add to it / change it!

Our entire documentation does not yet fully conform to these conventions yet,
so help in making it so would be appreciated!

### `pip` invocation

There are many ways to invoke a `pip` command, we recommend the following
approach:

```bash
python3 -m pip
```

This invokes `pip` explicitly using the `python3` binary that you are
currently using. This is the **recommended way** to invoke pip
in our documentation, since it is least likely to cause problems
with `python3` and `pip` being from different environments.

For more information on how to invoke `pip` commands, see
[the `pip` documentation](https://pip.pypa.io/en/stable/).

[JupyterHub Team Compass]: https://compass.hub.jupyter.org/contribute/documentation/
