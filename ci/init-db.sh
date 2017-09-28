#!/usr/bin/env bash
# initialize jupyterhub databases for testing

set -e

MYSQL="mysql --user root -e "
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

$SQL 'DROP DATABASE jupyterhub;' 2>/dev/null || true
$SQL "CREATE DATABASE jupyterhub ${EXTRA_CREATE};"
$SQL 'DROP DATABASE jupyterhub_upgrade;' 2>/dev/null || true
$SQL "CREATE DATABASE jupyterhub_upgrade ${EXTRA_CREATE};"
