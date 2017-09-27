#!/usr/bin/env bash
set -e
TMPDIR=$(mktemp -d)
ENVDIR="$TMPDIR/env"

# start mysql and postgres (do this first, so they have time to startup)
for DB in postgres mysql; do
  export DB
  bash docker-db.sh
done

# create virtualenv with jupyterhub 0.7
echo "creating virutalenv in $ENVDIR"
python -m virtualenv "$ENVDIR"
$ENVDIR/bin/pip install -q -r old-requirements.txt

echo "env-jupyterhub: $($ENVDIR/bin/jupyterhub --version)"
echo "jupyterhub-$(jupyterhub --version)"

set -x
# launch jupyterhub-0.7 token entrypoint to ensure db is initialized
for DB in sqlite postgres mysql; do
  export $DB
  echo -e "\n\n\nupgrade-db test: $DB"
  for i in {1..60}; do
    if "$ENVDIR/bin/jupyterhub" token alpha; then
      break
    else
      echo "waiting for $DB"
      sleep 2
    fi
  done

  # run upgrade-db
  jupyterhub upgrade-db
  # generate a token, for basic exercise
  jupyterhub token beta

  echo -e "\n\n$DB OK"
done

docker rm -f hub-test-postgres hub-test-mysql
rm -rf $ENVDIR