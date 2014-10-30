FROM postgres:9.3
RUN mkdir /docker-entrypoint-initdb.d
COPY initdb.sh /docker-entrypoint-initdb.d/init.sh
# Set your own password here.
ENV JPY_PSQL_PASSWORD arglebargle
