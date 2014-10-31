FROM jupyter/jupyterhub

RUN apt-get install -y libpq-dev \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && pip3 install psycopg2

# Replace this with your own password.
ENV JPY_PSQL_PASSWORD arglebargle
