#!/usr/bin/env bash
# This scripts starts a postgres or mysql database server, waits for it, and
# setup setups users to be used for local testing.

set -eu

# These environment variables influence the mysql and psql clients
export MYSQL_HOST=${MYSQL_HOST:-127.0.0.1}
export MYSQL_TCP_PORT=${MYSQL_TCP_PORT:-13306}
export PGHOST=${PGHOST:-127.0.0.1}
export PGPORT=${PGPORT:-5432}

# Define a name for a database container to start
DOCKER_CONTAINER="hub-test-$DB"

# Stop and remove any existing database container
docker rm -f "$DOCKER_CONTAINER" 2>/dev/null || true

# Prepare env vars DOCKER_RUN_ARGS and READINESS_CHECK
if [[ "$DB" == "mysql" ]]; then
    # Environment variables are considered by the Docker image, and the mysql
    # client respectively.
    # ref, docker: https://hub.docker.com/_/mysql/
    # ref, client: https://dev.mysql.com/doc/refman/5.7/en/setting-environment-variables.html
    #
    DOCKER_RUN_ARGS="-p $MYSQL_TCP_PORT:3306 --env MYSQL_ALLOW_EMPTY_PASSWORD=1 mysql:5.7"
    READINESS_CHECK="mysql --user root --execute \q"
elif [[ "$DB" == "postgres" ]]; then
    # Environment variables are considered by the Docker image, and the psql
    # client respectively.
    # ref, docker: https://hub.docker.com/_/postgres/
    # ref, client: https://www.postgresql.org/docs/9.5/libpq-envars.html
    #
    DOCKER_RUN_ARGS="-p $PGPORT:5432 postgres:9.5"
    READINESS_CHECK="psql --user postgres --command \q"
else
    echo '$DB must be mysql or postgres'
    exit 1
fi

# Start a new container
docker run --detach --name "$DOCKER_CONTAINER" $DOCKER_RUN_ARGS

# Wait for the new container to start
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

# Setup additional users to mysql's root and postgresql's postgres users
if [[ "$DB" == "mysql" ]]; then
    echo "A dedicated user for mysql isn't created."
elif [[ "$DB" == "postgres" ]]; then
    psql --user postgres --command "CREATE USER $PGUSER WITH PASSWORD '$PGPASSWORD';"
fi

# Print message for humans running the script
if [[ "$DB" == "mysql" ]]; then
    echo -e "
Set these environment variables:
    export MYSQL_HOST=$MYSQL_HOST
    export MYSQL_TCP_PORT=$MYSQL_TCP_PORT
"
elif [[ "$DB" == "postgres" ]]; then
    echo -e "
Set these environment variables:
    export PGHOST=$PGHOST
"
fi
