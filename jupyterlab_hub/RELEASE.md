# Making a jupyterlab_hub release

This document guides an extension maintainer through creating and publishing a release of jupyterlab_hub. This process creates a Python source package and a Python universal wheel and uploads them to PyPI.

## Update version number

Update the version number in `setup.py` and in `package.json`.

## Remove generated files

Remove old Javascript bundle builds and delete the `dist/` folder to remove old Python package builds:

```bash
npm run clean
rm -rf dist/
```

## Build the package

Build the Javascript extension bundle, then build the Python package and wheel:

```bash
npm run build
python setup.py sdist
python setup.py bdist_wheel --universal
```

## Upload the package

Upload the Python package and wheel with [twine](https://github.com/pypa/twine). See the Python documentation on [package uploading](https://packaging.python.org/distributing/#uploading-your-project-to-pypi)
for [twine](https://github.com/pypa/twine) setup instructions and for why twine is the recommended uploading method.

```bash
twine upload dist/*
```
