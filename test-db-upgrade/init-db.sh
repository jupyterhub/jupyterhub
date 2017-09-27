set -e

MYSQL="mysql --user root -e "
PSQL="psql --user postgres -c "

set -x

# drop databases if they don't exist
$MYSQL 'DROP DATABASE jupyterhub_upgrade' 2>/dev/null || true
$PSQL 'DROP DATABASE jupyterhub_upgrade' 2>/dev/null || true

# create the databases
$MYSQL 'CREATE DATABASE jupyterhub_upgrade CHARACTER SET utf8 COLLATE utf8_general_ci;'
$PSQL 'CREATE DATABASE jupyterhub_upgrade;'
