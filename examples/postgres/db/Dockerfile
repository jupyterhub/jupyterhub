FROM postgres:9.3

RUN mkdir /docker-entrypoint-initdb.d

# initdb.sh will be run by the parent container's entrypoint on container
# startup, prior to the the database being started.
COPY initdb.sh /docker-entrypoint-initdb.d/init.sh

# Uncomment and replace this with your own password.
# ENV JPY_PSQL_PASSWORD arglebargle
