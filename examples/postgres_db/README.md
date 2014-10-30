## Postgres Dockerfile
This example shows a Dockerfile that can be used to connect Jupyterhub to a Postgres backend.

### Running the Container
0. Replace `ENV JPY_PSQL_PASSWORD arglebargle` with your own password in the Dockerfile.
1. `cd` to the root of your jupyterhub repo.
2. Build the postgres image with `docker build -t jupyterhub-postgres examples/postgres_db/`.  This may take some time the first time it's run.
3. Run the image with `docker run -d -p 5433:5432 jupyterhub-postgres`.  This will start a postgres daemon container in the background that's listening on your localhost port 5433.
4. Run jupyterhub with `jupyterhub--db=postgresql://jupyterhub:<password>@localhost:5433/jupyterhub`.
