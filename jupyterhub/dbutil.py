"""Database utilities for JupyterHub"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
# Based on pgcontents.utils.migrate, used under the Apache license.
import argparse
import os
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime
from subprocess import check_call
from tempfile import TemporaryDirectory
from textwrap import dedent
from urllib.parse import urlparse

from sqlalchemy import create_engine
from traitlets.config import Application

from . import orm

_here = os.path.abspath(os.path.dirname(__file__))

ALEMBIC_INI_TEMPLATE_PATH = os.path.join(_here, 'alembic.ini')
ALEMBIC_DIR = os.path.join(_here, 'alembic')

# injected variables, populated for `script` entrypoint
db = None
db_url: str = None
session_factory = None


def write_alembic_ini(alembic_ini='alembic.ini', db_url='sqlite:///jupyterhub.sqlite'):
    """Write a complete alembic.ini from our template.

    Parameters
    ----------
    alembic_ini : str
        path to the alembic.ini file that should be written.
    db_url : str
        The SQLAlchemy database url, e.g. `sqlite:///jupyterhub.sqlite`.
    """
    with open(ALEMBIC_INI_TEMPLATE_PATH) as f:
        alembic_ini_tpl = f.read()

    with open(alembic_ini, 'w') as f:
        f.write(
            alembic_ini_tpl.format(
                alembic_dir=ALEMBIC_DIR,
                # If there are any %s in the URL, they should be replaced with %%, since ConfigParser
                # by default uses %() for substitution. You'll get %s in your URL when you have usernames
                # with special chars (such as '@') that need to be URL encoded. URL Encoding is done with %s.
                # YAY for nested templates?
                db_url=str(db_url).replace('%', '%%'),
            )
        )


@contextmanager
def _temp_alembic_ini(db_url):
    """Context manager for temporary JupyterHub alembic directory

    Temporarily write an alembic.ini file for use with alembic migration scripts.

    Context manager yields alembic.ini path.

    Parameters
    ----------
    db_url : str
        The SQLAlchemy database url, e.g. `sqlite:///jupyterhub.sqlite`.

    Returns
    -------
    alembic_ini: str
        The path to the temporary alembic.ini that we have created.
        This file will be cleaned up on exit from the context manager.
    """
    with TemporaryDirectory() as td:
        alembic_ini = os.path.join(td, 'alembic.ini')
        write_alembic_ini(alembic_ini, db_url)
        yield alembic_ini


def upgrade(db_url, revision='head'):
    """Upgrade the given database to revision.

    db_url: str
        The SQLAlchemy database url, e.g. `sqlite:///jupyterhub.sqlite`.
    revision: str [default: head]
        The alembic revision to upgrade to.
    """
    with _temp_alembic_ini(db_url) as alembic_ini:
        check_call(['alembic', '-c', alembic_ini, 'upgrade', revision])


def downgrade(db_url, revision):
    """Downgrade the given database to revision.

    db_url: str
        The SQLAlchemy database url, e.g. `sqlite:///jupyterhub.sqlite`.
    revision: str
        The alembic revision to upgrade to.

    .. versionadded:: 6.2
    """
    with _temp_alembic_ini(db_url) as alembic_ini:
        check_call(['alembic', '-c', alembic_ini, 'downgrade', revision])


def backup_db_file(db_file, log=None):
    """Backup a database file if it exists"""
    timestamp = datetime.now().strftime('.%Y-%m-%d-%H%M%S')
    backup_db_file = db_file + timestamp
    for i in range(1, 10):
        if not os.path.exists(backup_db_file):
            break
        backup_db_file = f'{db_file}.{timestamp}.{i}'
    #
    if os.path.exists(backup_db_file):
        raise OSError(f"backup db file already exists: {backup_db_file}")
    if log:
        log.info("Backing up %s => %s", db_file, backup_db_file)
    shutil.copy(db_file, backup_db_file)


def rollback(db_url, *, revision, backup=True, log=None):
    """Downgrade a database if needed

    If the database is sqlite, a backup file will be created with a timestamp.
    Other database systems should perform their own backups prior to calling this.

    .. versionadded:: 6.2
    """
    urlinfo = urlparse(db_url)
    if urlinfo.password:
        # avoid logging the database password
        urlinfo = urlinfo._replace(
            netloc=f'{urlinfo.username}:[redacted]@{urlinfo.hostname}:{urlinfo.port}'
        )
        db_log_url = urlinfo.geturl()
    else:
        db_log_url = db_url
    if log:
        log.info("Downgrading %s to %s", db_log_url, revision)
    # we need to downgrade, backup the database
    if backup and db_url.startswith('sqlite:///'):
        db_file = db_url.split(':///', 1)[1]
        backup_db_file(db_file, log=log)
    downgrade(db_url, revision)


def upgrade_if_needed(db_url, *, db_kwargs=None, backup=True, log=None):
    """Upgrade a database if needed

    If the database is sqlite, a backup file will be created with a timestamp.
    Other database systems should perform their own backups prior to calling this.
    """
    # run check-db-revision first
    engine = create_engine(db_url, **db_kwargs or {})
    try:
        orm.check_db_revision(engine)
    except orm.DatabaseSchemaMismatch:
        # ignore mismatch error because that's what we are here for!
        pass
    else:
        # nothing to do
        return
    urlinfo = urlparse(db_url)
    if urlinfo.password:
        # avoid logging the database password
        urlinfo = urlinfo._replace(
            netloc=f'{urlinfo.username}:[redacted]@{urlinfo.hostname}:{urlinfo.port}'
        )
        db_log_url = urlinfo.geturl()
    else:
        db_log_url = db_url
    log.info("Upgrading %s", db_log_url)
    # we need to upgrade, backup the database
    if backup and db_url.startswith('sqlite:///'):
        db_file = db_url.split(':///', 1)[1]
        backup_db_file(db_file, log=log)
    upgrade(db_url)


_banner = """
JupyterHub database utility shell

Interpreter: {interpreter_name}

Available variables:

  db_url: {db_url!r}
  db: open database session
  session_factory: factory function for database sessions
  orm: imported `jupyterhub.orm` module
"""


def _load_hub(args=None):
    """Instantiate JupyterHub and load config

    Minimal initialization to get to db_url and db_kwargs
    """
    from .app import JupyterHub

    hub = JupyterHub.instance()
    if args:
        hub.parse_command_line(args)
    hub.load_config_file(hub.config_file)
    return hub


def _load_ns(args=None):
    """Load the JupyterHub db utility namespace

    Defines `db`, `db_url`, `session_factory`
    """
    hub = _load_hub(args)
    db_url = hub.db_url
    session_factory = orm.new_session_factory(db_url, **hub.db_kwargs)
    db = session_factory()
    ns = {'db': db, 'db_url': db_url, 'orm': orm, 'session_factory': session_factory}
    return ns


def shell(args=None, *, hub_args=None):
    """Start an IPython shell hooked up to the jupyterhub database"""
    ns = _load_ns(hub_args)

    try:
        import IPython
    except ImportError:
        # fallback on stdlib
        if args:
            print(f"ignoring args: {args}", file=sys.stderr)
        from code import interact

        interact(
            banner=_banner.format(
                interpreter_name="stdlib (install IPython for a nicer shell)",
                **ns,
            ),
            local=ns,
        )
    else:
        from .app import JupyterHub

        # avoid clash on Application.instance
        # allow setting IPython config in jupyterhub config
        config = JupyterHub.instance().config
        Application._instance = None
        config.InteractiveShell.banner1 = _banner.format(
            interpreter_name="IPython",
            **ns,
        )
        IPython.start_ipython(args, config=config, user_ns=ns)


def script(fname, *, hub_args=None, args=None):
    """Run a script after connecting to the jupyterhub database

    If fname='-', get script from stdin.
    """
    ns = _load_ns(hub_args)
    # allow `from jupyterhub.dbutil import db` for lintable scripts
    globals().update(ns)
    if args:
        sys.argv = [fname, *args]
    if fname == "-":
        # run stdout
        script = sys.stdin.read()
        exec(script, ns)
    else:
        import runpy

        runpy.run_path(fname, init_globals=ns, run_name="__main__")


def _alembic(args, *, hub_args=None):
    """Run an alembic command with a temporary alembic.ini"""
    hub = _load_hub(hub_args)
    db_url = hub.db_url
    with _temp_alembic_ini(db_url) as alembic_ini:
        check_call(['alembic', '-c', alembic_ini] + args)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    # dumb option parsing, since we want to pass things through
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent("""
        JupyterHub database utilities
        
        Launch a shell or run a script after loading JupyterHub configuration
        and connecting to the database.
        For scripts and shells, a db session will be open as `db`,
        and `db_url` and `session_factory` will be available for constructing new connections.

        Any arguments passed before the subcommand name will be handled by jupyterhub itself,
        such as `-f config_file.py` or `--debug`, etc.
        Arguments _after_ the command will be handled by the command,
        e.g. shell will pass startup arguments to IPython,
        or script will pass them to your script.
        """),
        epilog=dedent("""
        Examples:
            
            python3 -m jupyterhub.dbutil shell
            python3 -m jupyterhub.dbutil alembic show head
            python3 -m jupyterhub.dbutil script ./myscript.py [script args]
            cat myscript.py | kubectl exec -i hub-... -c hub -- python3 -m jupyterhub.dbutil --debug -f /usr/local/etc/jupyterhub_config.py script -
        """),
    )
    # subcommand not found
    subparsers = parser.add_subparsers(
        required=True,
        help="The subcommand to launch. Any arguments before the subcommand will be passed along to JupyterHub (such as `-f my_hub_config.py`)",
    )
    script_parser = subparsers.add_parser('script', help='run a Python script')
    script_parser.add_argument(
        'path', type=str, help="The script to run. Use '-' to read from stdin."
    )
    script_parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Remaining args are passed to the script.",
    )
    script_parser.set_defaults(command=script)

    shell_parser = subparsers.add_parser(
        'shell', help='Launch an interactive shell (IPython, if available)'
    )
    shell_parser.add_argument(
        "args", nargs=argparse.REMAINDER, help="Remaining args are passed to IPython."
    )
    shell_parser.set_defaults(command=shell)

    alembic_parser = subparsers.add_parser(
        'alembic',
        help='Run alembic commands against the JupyterHub database',
    )
    alembic_parser.add_argument(
        "args", nargs=argparse.REMAINDER, help="Remaining args are passed to alembic"
    )
    alembic_parser.set_defaults(command=_alembic)

    # locate command
    commands = {
        "script": script,
        "alembic": _alembic,
        "shell": shell,
    }
    command = None
    # partition on command, _before_ doing any parsing
    for i, arg in enumerate(args):
        if arg in commands:
            command = commands[arg]
            break

    if command is None:
        # this will always fail with the informative argparse error
        # because command hasn't been given
        parser.parse_args(args)
        return 1

    # split hub_args before command
    hub_args = args[:i]
    command_args = args[i:]

    opts = parser.parse_args(command_args)
    if opts.command is script:
        opts.command(opts.path, args=opts.args, hub_args=hub_args)
    else:
        opts.command(args=opts.args, hub_args=hub_args)


if __name__ == '__main__':
    sys.exit(main())
