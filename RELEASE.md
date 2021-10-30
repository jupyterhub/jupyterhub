# How to make a release

`jupyterhub` is a package [available on
PyPI](https://pypi.org/project/jupyterhub/) and
[conda-forge](https://conda-forge.org/).
These are instructions on how to make a release on PyPI.
The PyPI release is done automatically by CI when a tag is pushed.

For you to follow along according to these instructions, you need:

- To have push rights to the [jupyterhub GitHub
  repository](https://github.com/jupyterhub/jupyterhub).

## Steps to make a release

1. Checkout main and make sure it is up to date.

   ```shell
   ORIGIN=${ORIGIN:-origin} # set to the canonical remote, e.g. 'upstream' if 'origin' is not the official repo
   git checkout main
   git fetch $ORIGIN main
   git reset --hard $ORIGIN/main
   ```

1. Make sure `docs/source/changelog.md` is up-to-date.
   [github-activity][] can help with this.

1. Update the version with `tbump`.
   You can see what will happen without making any changes with `tbump --dry-run ${VERSION}`

   ```shell
   tbump ${VERSION}
   ```

   This will tag and publish a release,
   which will be finished on CI.

1. Reset the version back to dev, e.g. `2.1.0.dev` after releasing `2.0.0`

   ```shell
   tbump --no-tag ${NEXT_VERSION}.dev
   ```

1. Following the release to PyPI, an automated PR should arrive to
   [conda-forge/jupyterhub-feedstock][],
   check for the tests to succeed on this PR and then merge it to successfully
   update the package for `conda` on the conda-forge channel.

[github-activity]: https://github.com/choldgraf/github-activity
[conda-forge/jupyterhub-feedstock]: https://github.com/conda-forge/jupyterhub-feedstock
