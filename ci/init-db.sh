#!/usr/bin/env bash
# The goal of this script is to initialize a running database server with clean
# databases for use during tests.
#
# Required environment variables:
# - DB: The database server to start, either "postgres" or "mysql".

set -eu

# Prepare env vars SQL_CLIENT and EXTRA_CREATE_DATABASE_ARGS
if [[ "$DB" == "mysql" ]]; then
    SQL_CLIENT="mysql --user root --execute "
    EXTRA_CREATE_DATABASE_ARGS='CHARACTER SET utf8 COLLATE utf8_general_ci'
elif [[ "$DB" == "postgres" ]]; then
    SQL_CLIENT="psql --command "
else
    echo '$DB must be mysql or postgres'
    exit 1
fi

# Configure a set of databases in the database server for upgrade tests
set -x
for SUFFIX in '' _upgrade_100 _upgrade_122 _upgrade_130; do
    $SQL_CLIENT "DROP DATABASE jupyterhub${SUFFIX};" 2>/dev/null || true
    $SQL_CLIENT "CREATE DATABASE jupyterhub${SUFFIX} ${EXTRA_CREATE_DATABASE_ARGS:-};"
done
