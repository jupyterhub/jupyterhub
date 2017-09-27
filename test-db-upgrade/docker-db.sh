#!/usr/bin/env bash
# source this file to setup postgres and mysql
# for local testing (as similar as possible to docker)

DOCKER="docker run --rm -d --name"

export MYSQL_HOST=127.0.0.1
export PGHOST=127.0.0.1

set -ex
docker rm -f hub-test-mysql hub-test-postgres 2>/dev/null || true

$DOCKER hub-test-mysql -e MYSQL_ALLOW_EMPTY_PASSWORD=1 -p 3306:3306 mysql:5.7
$DOCKER hub-test-postgres -p 5432:5432 postgres:9.5
set +x

echo -n 'waiting for postgres'
for i in {1..60}; do
  if psql --user postgres -c '\q' 2>/dev/null; then
    echo 'done'
    break
  else
    echo -n '.'
    sleep 1
  fi
done

echo -n 'waiting for mysql'
for i in {1..60}; do
  if mysql --user root -e '\q' 2>/dev/null; then
    echo 'done'
    break
  else
    echo -n '.'
    sleep 1
  fi
done

echo -e "
Set these environment variables:

    export MYSQL_HOST=127.0.0.1
    export PGHOST=127.0.0.1
"