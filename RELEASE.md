# How to make a release

`jupyterhub` is a package available on [PyPI][] and [conda-forge][].
These are instructions on how to make a release.

## Pre-requisites

- Push rights to [jupyterhub/jupyterhub][]
- Push rights to [conda-forge/jupyterhub-feedstock][]

## Steps to make a release

1. Create a PR updating `docs/source/changelog.md` with [github-activity][] and
   continue only when its merged.

   ```shell
   pip install github-activity

   github-activity --heading-level=3 jupyterhub/jupyterhub
   ```

1. Checkout main and make sure it is up to date.

   ```shell
   git checkout main
   git fetch origin main
   git reset --hard origin/main
   ```

1. Update the version, make commits, and push a git tag with `tbump`.

   ```shell
   pip install tbump
   tbump --dry-run ${VERSION}

   tbump ${VERSION}
   ```

   Following this, the [CI system][] will build and publish a release.

1. Reset the version back to dev, e.g. `2.1.0.dev` after releasing `2.0.0`

   ```shell
   tbump --no-tag ${NEXT_VERSION}.dev
   ```

1. Following the release to PyPI, an automated PR should arrive to
   [conda-forge/jupyterhub-feedstock][] with instructions.

[pypi]: https://pypi.org/project/jupyterhub/
[conda-forge]: https://anaconda.org/conda-forge/jupyterhub
[jupyterhub/jupyterhub]: https://github.com/jupyterhub/jupyterhub
[conda-forge/jupyterhub-feedstock]: https://github.com/conda-forge/jupyterhub-feedstock
[github-activity]: https://github.com/executablebooks/github-activity
[ci system]: https://github.com/jupyterhub/jupyterhub/actions/workflows/release.yml
