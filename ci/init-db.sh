#!/usr/bin/env bash
# The goal of this script is to initialize a running database server with clean
# databases for use during tests.
#
# Required environment variables:
# - DB: The database server to start, either "postgres" or "mysql".

set -eu

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
