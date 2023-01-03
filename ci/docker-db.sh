#!/usr/bin/env bash
# The goal of this script is to start a database server as a docker container.
#
# Required environment variables:
# - DB: The database server to start, either "postgres" or "mysql".
#
# - PGUSER/PGPASSWORD: For the creation of a postgresql user with associated
#   password.

set -eu

# Stop and remove any existing database container
DOCKER_CONTAINER="hub-test-$DB"
docker rm -f "$DOCKER_CONTAINER" 2>/dev/null || true

# Prepare environment variables to startup and await readiness of either a mysql
# or postgresql server.
if [[ "$DB" == "mysql" ]]; then
    # Environment variables can influence both the mysql server in the docker
    # container and the mysql client.
    #
    # ref server: https://hub.docker.com/_/mysql/
    # ref client: https://dev.mysql.com/doc/refman/5.7/en/setting-environment-variables.html
    #
    DOCKER_RUN_ARGS="-p 3306:3306 --env MYSQL_ALLOW_EMPTY_PASSWORD=1 mysql:8.0"
    READINESS_CHECK="mysql --user root --execute \q"
elif [[ "$DB" == "postgres" ]]; then
    # Environment variables can influence both the postgresql server in the
    # docker container and the postgresql client (psql).
    #
    # ref server: https://hub.docker.com/_/postgres/
    # ref client: https://www.postgresql.org/docs/9.5/libpq-envars.html
    #
    # POSTGRES_USER / POSTGRES_PASSWORD will create a user on startup of the
    # postgres server, but PGUSER and PGPASSWORD are the environment variables
    # used by the postgresql client psql, so we configure the user based on how
    # we want to connect.
    #
    DOCKER_RUN_ARGS="-p 5432:5432 --env "POSTGRES_USER=${PGUSER}" --env "POSTGRES_PASSWORD=${PGPASSWORD}" postgres:15.1"
    READINESS_CHECK="psql --command \q"
else
    echo '$DB must be mysql or postgres'
    exit 1
fi

# Start the database server
docker run --detach --name "$DOCKER_CONTAINER" $DOCKER_RUN_ARGS

# Wait for the database server to start
echo -n "waiting for $DB "
for i in {1..60}; do
    if $READINESS_CHECK; then
        echo 'done'
        break
    else
        echo -n '.'
        sleep 1
    fi
done
$READINESS_CHECK
