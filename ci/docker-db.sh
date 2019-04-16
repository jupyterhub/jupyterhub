#!/usr/bin/env bash
# source this file to setup postgres and mysql
# for local testing (as similar as possible to docker)

set -eu

export MYSQL_HOST=127.0.0.1
export MYSQL_TCP_PORT=${MYSQL_TCP_PORT:-13306}
export PGHOST=127.0.0.1
NAME="hub-test-$DB"
DOCKER_RUN="docker run -d --name $NAME"

docker rm -f "$NAME" 2>/dev/null || true

case "$DB" in
"mysql")
  RUN_ARGS="-e MYSQL_ALLOW_EMPTY_PASSWORD=1 -p $MYSQL_TCP_PORT:3306 mysql:5.7"
  CHECK="mysql --host $MYSQL_HOST --port $MYSQL_TCP_PORT --user root -e \q"
  ;;
"postgres")
  RUN_ARGS="-p 5432:5432 postgres:9.5"
  CHECK="psql --user postgres -c \q"
  ;;
*)
  echo '$DB must be mysql or postgres'
  exit 1
esac

$DOCKER_RUN $RUN_ARGS

echo -n "waiting for $DB "
for i in {1..60}; do
  if $CHECK; then
    echo 'done'
    break
  else
    echo -n '.'
    sleep 1
  fi
done
$CHECK

case "$DB" in
"mysql")
  ;;
"postgres")
  # create the user
  psql --user postgres -c "CREATE USER $PGUSER WITH PASSWORD '$PGPASSWORD';"
  ;;
*)
esac

echo -e "
Set these environment variables:

    export MYSQL_HOST=127.0.0.1
    export MYSQL_TCP_PORT=$MYSQL_TCP_PORT
    export PGHOST=127.0.0.1
"
