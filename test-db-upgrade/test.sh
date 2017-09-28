#!/usr/bin/env bash
set -e

TMPDIR=$(mktemp -d)
ENVDIR="$TMPDIR/env"

# initialize the databases
bash "$(dirname $0)"/init-db.sh

# create virtualenv with jupyterhub 0.7
echo "creating virutalenv in $ENVDIR"
python -m venv "$ENVDIR"
$ENVDIR/bin/pip install -q -r old-requirements.txt

echo "env-jupyterhub: $($ENVDIR/bin/jupyterhub --version)"
echo "jupyterhub-$(jupyterhub --version)"

set -x
# launch jupyterhub-0.7 token entrypoint to ensure db is initialized
for DB in sqlite postgres mysql; do
  export DB
  echo -e "\n\n\nupgrade-db test: $DB"
  "$ENVDIR/bin/jupyterhub" token alpha

  # run upgrade-db
  jupyterhub upgrade-db
  # generate a token, for basic exercise
  jupyterhub token beta

  echo -e "\n\n$DB OK"
done

rm -rf $ENVDIR
