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
    # Environment variables can influence the Docker container
    # ref: https://hub.docker.com/_/mysql/
    DOCKER_RUN_ARGS="-p 3306 --env MYSQL_ALLOW_EMPTY_PASSWORD=1 mysql:5.7"
    READINESS_CHECK="mysql --user root --execute \q"
elif [[ "$DB" == "postgres" ]]; then
    # Environment variables can influence the Docker container
    # ref: https://hub.docker.com/_/postgres/
    DOCKER_RUN_ARGS="-p 5432 postgres:9.5"
    READINESS_CHECK="psql --user postgres --command \q"
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

# Setup an additional user to mysql's root or postgresql's postgres user
if [[ "$DB" == "mysql" ]]; then
    echo "A dedicated user for the mysql server isn't created."
elif [[ "$DB" == "postgres" ]]; then
    psql --user postgres --command "CREATE USER $PGUSER WITH PASSWORD '$PGPASSWORD';"
fi
