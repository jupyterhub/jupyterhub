#!/usr/bin/env bash
# This script initialize multiple databases for testing in a running database
# server, using either the mysql client or psql client with the root or postgres
# users.

set -eu

# These environment variables influence the mysql and psql clients
export MYSQL_HOST=${MYSQL_HOST:-127.0.0.1}
export MYSQL_TCP_PORT=${MYSQL_TCP_PORT:-13306}
export PGHOST=${PGHOST:-127.0.0.1}
export PGPORT=${PGPORT:-5432}

# Prepare env vars CLIENT_COMMAND and EXTRA_CREATE_DATABASE_ARGS
if [[ "$DB" == "mysql" ]]; then
    CLIENT_COMMAND="mysql --user root --execute "
    EXTRA_CREATE_DATABASE_ARGS='CHARACTER SET utf8 COLLATE utf8_general_ci'
elif [[ "$DB" == "postgres" ]]; then
    CLIENT_COMMAND="psql --user postgres --command "
else
    echo '$DB must be mysql or postgres'
    exit 1
fi

# Configure a set of databases in the database server for upgrade tests
set -x
for SUFFIX in '' _upgrade_072 _upgrade_081 _upgrade_094; do
    $CLIENT_COMMAND "DROP DATABASE jupyterhub${SUFFIX};" 2>/dev/null || true
    $CLIENT_COMMAND "CREATE DATABASE jupyterhub${SUFFIX} ${EXTRA_CREATE_DATABASE_ARGS:-};"
done
