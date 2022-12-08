(contributing-docs)=

# Contributing Documentation

Documentation is often more important than code. This page helps
you get set up on how to contribute to JupyterHub's documentation.

## Building documentation locally

We use [sphinx](https://www.sphinx-doc.org) to build our documentation. It takes
our documentation source files (written in [markdown](https://daringfireball.net/projects/markdown/) or [reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html) &
stored under the `docs/source` directory) and converts it into various
formats for people to read. To make sure the documentation you write or
change renders correctly, it is good practice to test it locally.

1. Make sure you have successfully completed {ref}`contributing/setup`.

2. Install the packages required to build the docs.

   ```bash
   python3 -m pip install -r docs/requirements.txt
   ```

3. Build the html version of the docs. This is the most commonly used
   output format, so verifying it renders correctly is usually good
   enough.

   ```bash
   cd docs
   make html
   ```

   This step will display any syntax or formatting errors in the documentation,
   along with the filename / line number in which they occurred. Fix them,
   and re-run the `make html` command to re-render the documentation.

4. View the rendered documentation by opening `_build/html/index.html` in
   a web browser.

   :::{tip}
   **On Windows**, you can open a file from the terminal with `start <path-to-file>`.

   **On macOS**, you can do the same with `open <path-to-file>`.

   **On Linux**, you can do the same with `xdg-open <path-to-file>`.

   After opening index.html in your browser you can just refresh the page whenever
   you rebuild the docs via `make html`
   :::

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

This invokes pip explicitly using the python3 binary that you are
currently using. This is the **recommended way** to invoke pip
in our documentation, since it is least likely to cause problems
with python3 and pip being from different environments.

For more information on how to invoke `pip` commands, see
[the pip documentation](https://pip.pypa.io/en/stable/).
