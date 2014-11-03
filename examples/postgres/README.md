## Postgres Dockerfile

This example shows how you can connect Jupyterhub to a Postgres database
instead of the default SQLite backend.

### Running Postgres with Jupyterhub on the host.
0. Uncomment and replace `ENV JPY_PSQL_PASSWORD arglebargle` with your own
   password in the Dockerfile for `examples/postgres/db`. (Alternatively, pass
   -e `JPY_PSQL_PASSWORD=<password>` when you start the db container.)

1. `cd` to the root of your jupyterhub repo.

2. Build the postgres image with `docker build -t jupyterhub-postgres-db
   examples/postgres/db`.  This may take a minute or two the first time it's
   run.

3. Run the db image with `docker run -d -p 5433:5432 jupyterhub-postgres-db`.
   This will start a postgres daemon container in the background that's
   listening on your localhost port 5433.

4. Run jupyterhub with
   `jupyterhub --db=postgresql://jupyterhub:<password>@localhost:5433/jupyterhub`.

5. Log in as the user running jupyterhub on your host machine.

### Running Postgres with Containerized Jupyterhub.
0. Do steps 0-2 in from the above section, ensuring that the values set/passed
   for `JPY_PSQL_PASSWORD` match for the hub and db containers.

1. Build the hub image with `docker build -t jupyterhub-postgres-hub
   examples/postgres/hub`.  This may take a minute or two the first time it's
   run.

2. Run the db image with `docker run -d --name=jpy-db
   jupyterhub-postgres`. Note that, unlike when connecting to a host machine
   jupyterhub, we don't specify a port-forwarding scheme here, but we do need
   to specify a name for the container.

3. Run the containerized hub with `docker run -it --link jpy-db:postgres
   jupyterhub-postgres-hub`.  This instructs docker to run the hub container
   with a link to the already-running db container, which will forward
   environment and connection information from the DB to the hub.

4. Log in as one of the users defined in the `examples/postgres/hub/`
   Dockerfile.  By default `rhea` is the server's admin user, `io` and
   `ganymede` are non-admin users, and all users' passwords are their
   usernames.
