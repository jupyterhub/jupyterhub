## Postgres Dockerfile

This example shows how you can connect Jupyterhub to a Postgres database
instead of the default SQLite backend.

### Running Postgres with Jupyterhub on the host.
0. Replace `ENV JPY_PSQL_PASSWORD arglebargle` with your own password in the
   Dockerfile for `examples/postgres/db`. (Alternatively you can pass -e
   `JPY_PSQL_PASSWORD=<password>` when you start the db container.)

1. `cd` to the root of your jupyterhub repo.

2. Build the postgres image with `docker build -t jupyterhub-postgres-db
   examples/postgres/db`.  This may take a minute or two the first time it's
   run.

3. Run the db image with `docker run -d -p 5433:5432 jupyterhub-postgres-db`.
   This will start a postgres daemon container in the background that's
   listening on your localhost port 5433.

4. Run jupyterhub with
   `jupyterhub --db=postgresql://jupyterhub:<password>@localhost:5433/jupyterhub`.

### Running Postgres with Containerized Jupyterhub.
0. Replace `ENV JPY_PSQL_PASSWORD arglebargle` with your own password in the
   Dockerfile for `examples/postgres/hub`. (Alternatively you can pass -e
   `JPY_PSQL_PASSWORD=<password>` when you start the hub container.)

1. Do steps 0-2 in from the above section, ensuring that the values set/passed
   for `JPY_PSQL_PASSWORD` match for the hub and db containers.

2. Build the hub image with `docker build -t jupyterhub-postgres-db
   examples/postgres/db`.  This may take a minute or two the first time it's run.

3. Run the db image with `docker run -d --name=jpy-db
   jupyterhub-postgres`. Note that, unlike when connecting to a host machine
   jupyterhub, we don't specify a port-forwarding scheme here, but we do need
   to specify a name for the container.

4. Run the containerized hub with `docker run -it --link jpy-db:postgres
   jupyterhub-postgres-hub`.
