FROM jupyter/jupyterhub

MAINTAINER Jupyter Project <ipython-dev@scipy.org>

RUN apt-get install -y libpq-dev \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && pip3 install psycopg2

# Replace this with your own password.
ENV JPY_PSQL_PASSWORD arglebargle

RUN useradd -m -G shadow -p $(openssl passwd -1 rhea) rhea
RUN chown rhea .

RUN for name in io ganymede ; do useradd -m -p $(openssl passwd -1 $name) $name; done

USER rhea
