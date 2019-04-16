#!/usr/bin/env bash
# initialize jupyterhub databases for testing

set -eu

MYSQL="mysql --user root --host $MYSQL_HOST --port $MYSQL_TCP_PORT -e "
PSQL="psql --user postgres -c "

case "$DB" in
"mysql")
  EXTRA_CREATE='CHARACTER SET utf8 COLLATE utf8_general_ci'
  SQL="$MYSQL"
  ;;
"postgres")
  SQL="$PSQL"
  ;;
*)
  echo '$DB must be mysql or postgres'
  exit 1
esac

set -x

for SUFFIX in '' _upgrade_072 _upgrade_081 _upgrade_094; do
    $SQL "DROP DATABASE jupyterhub${SUFFIX};" 2>/dev/null || true
    $SQL "CREATE DATABASE jupyterhub${SUFFIX} ${EXTRA_CREATE:-};"
done
