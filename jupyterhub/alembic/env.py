import logging
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if 'jupyterhub' in sys.modules:
    from traitlets.config import MultipleInstanceError

    from jupyterhub.app import JupyterHub

    app = None
    if JupyterHub.initialized():
        try:
            app = JupyterHub.instance()
        except MultipleInstanceError:
            # could have been another Application
            pass
    if app is not None:
        alembic_logger = logging.getLogger('alembic')
        alembic_logger.propagate = True
        alembic_logger.parent = app.log
    else:
        fileConfig(config.config_file_name, disable_existing_loggers=False)
else:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
from jupyterhub import orm

target_metadata = orm.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# pass these to context.configure(**config_opts)
common_config_opts = dict(
    # target_metadata for autogenerate
    target_metadata=target_metadata,
    # transaction per migration to ensure
    # each migration is 'complete' before running the next one
    # (e.g. dropped tables)
    transaction_per_migration=True,
)


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    connectable = config.attributes.get('connection', None)
    config_opts = {}
    config_opts.update(common_config_opts)
    config_opts["literal_binds"] = True

    if connectable is None:
        config_opts["url"] = config.get_main_option("sqlalchemy.url")
    else:
        config_opts["connection"] = connectable
    context.configure(**config_opts)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = config.attributes.get('connection', None)
    config_opts = {}
    config_opts.update(common_config_opts)

    if connectable is None:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            **common_config_opts,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
