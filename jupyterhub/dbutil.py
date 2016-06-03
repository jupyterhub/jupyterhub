"""Database utilities for JupyterHub"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Based on pgcontents.utils.migrate, used under the Apache license.

from contextlib import contextmanager
import os
from subprocess import check_call
import sys
from tempfile import TemporaryDirectory

_here = os.path.abspath(os.path.dirname(__file__))

ALEMBIC_INI_TEMPLATE_PATH = os.path.join(_here, 'alembic.ini')
ALEMBIC_DIR = os.path.join(_here, 'alembic')


def write_alembic_ini(alembic_ini='alembic.ini', db_url='sqlite:///jupyterhub.sqlite'):
    """Write a complete alembic.ini from our template.
    
    Parameters
    ----------
    
    alembic_ini: str
        path to the alembic.ini file that should be written.
    db_url: str
        The SQLAlchemy database url, e.g. `sqlite:///jupyterhub.sqlite`.
    """
    with open(ALEMBIC_INI_TEMPLATE_PATH) as f:
        alembic_ini_tpl = f.read()
    
    with open(alembic_ini, 'w') as f:
        f.write(
            alembic_ini_tpl.format(
                alembic_dir=ALEMBIC_DIR,
                db_url=db_url,
            )
        )
    


@contextmanager
def _temp_alembic_ini(db_url):
    """Context manager for temporary JupyterHub alembic directory
    
    Temporarily write an alembic.ini file for use with alembic migration scripts.
    
    Context manager yields alembic.ini path.
    
    Parameters
    ----------
    
    db_url: str
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
        check_call(
            ['alembic', '-c', alembic_ini, 'upgrade', revision]
        )

def _alembic(*args):
    """Run an alembic command with a temporary alembic.ini"""
    with _temp_alembic_ini('sqlite:///jupyterhub.sqlite') as alembic_ini:
        check_call(
            ['alembic', '-c', alembic_ini] + list(args)
        )


if __name__ == '__main__':
    import sys
    _alembic(*sys.argv[1:])
