#!/usr/bin/env bash
set -e
NAME="hub-test-$DB"
docker rm -f $NAME 2>/dev/null || true

case $DB in
mysql)
  ARGS="-p 13306:3306 -e MYSQL_ROOT_PASSWORD=x -e MYSQL_DATABASE=jupyterhub mysql:5.7"
  ;;
postgres)
  ARGS="-p 15432:5432 -e POSTGRES_DB=jupyterhub postgres:9.5"
  ;;
*)
  echo "must be mysql or postgres"
  exit -1
esac

set -x
docker run --rm --name $NAME -d $ARGS
