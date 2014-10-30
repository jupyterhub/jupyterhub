#!/bin/bash

# Start a postgres daemon, ignoring log output.

gosu postgres pg_ctl start -w -l /dev/null

gosu postgres psql -c "CREATE DATABASE jupyterhub;"
gosu postgres psql -c "CREATE USER jupyterhub WITH ENCRYPTED PASSWORD '$JPY_PSQL_PASSWORD';"
gosu postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE jupyterhub TO jupyterhub;"

# Alter pg_hba.conf to actually require passwords.
# The default image exposes allows any user to connect without requiring a
# password.
sed -ri -e 's/(host all all 0.0.0.0\/0 )(trust)/\1md5/' "$PGDATA"/pg_hba.conf

gosu postgres pg_ctl stop -w
