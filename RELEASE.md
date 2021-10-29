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

1. Update [CHANGELOG.md](CHANGELOG.md). Doing this can be made easier with the
   help of [github-activity](https://github.com/choldgraf/github-activity).

1. Set the `version_info` variable in [\_version.py](jupyterhub/_version.py)
   appropriately, update `docs/source/_static/rest-api.yml` to match and make a commit.

   ```shell
   git add jupyterhub/_version.py
   git add docs/source/_static/rest-api.yml
   VERSION=...  # e.g. 1.2.3
   git commit -m "release $VERSION"
   ```

1. Reset the `version_info` variable in
   [\_version.py](jupyterhub/_version.py) appropriately with an incremented
   patch version and a `dev` element, then make a commit.

   ```shell
   git add jupyterhub/_version.py
   git add docs/source/_static/rest-api.yml
   git commit -m "back to dev"
   ```

1. Push your two commits to main.

   ```shell
   # first push commits without a tags to ensure the
   # commits comes through, because a tag can otherwise
   # be pushed all alone without company of rejected
   # commits, and we want have our tagged release coupled
   # with a specific commit in main
   git push $ORIGIN main
   ```

1. Create a git tag for the pushed release commit and push it.

   ```shell
   git tag -a $VERSION -m $VERSION HEAD~1

   # then verify you tagged the right commit
   git log

   # then push it
   git push $ORIGIN $VERSION
   ```

1. Following the release to PyPI, an automated PR should arrive to
   [conda-forge/jupyterhub-feedstock](https://github.com/conda-forge/jupyterhub-feedstock),
   check for the tests to succeed on this PR and then merge it to successfully
   update the package for `conda` on the conda-forge channel.
