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

1. Install the packages required to build the docs.

   ```bash
   python3 -m pip install -r docs/requirements.txt
   python3 -m pip install sphinx-autobuild
   ```

2. Build the HTML version of the docs. This is the most commonly used
   output format, so verifying it renders correctly is usually good
   enough.

   ```bash
   sphinx-autobuild docs/source/ docs/_build/html
   ```

   This step will display any syntax or formatting errors in the documentation,
   along with the filename / line number in which they occurred. Fix them,
   and the HTML will be re-render automatically.

3. View the rendered documentation by opening <http://127.0.0.1:8000> in
   a web browser.

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
