"""Database tests"""
from glob import glob
import os
import shutil

from sqlalchemy.exc import OperationalError
from pytest import raises

from ..dbutil import upgrade
from ..app import NewToken, UpgradeDB, JupyterHub


here = os.path.dirname(__file__)
old_db = os.path.join(here, 'old-jupyterhub.sqlite')


def generate_old_db(path):
    """Return url for old SQLite test database"""
    db_path = os.path.join(path, "jupyterhub.sqlite")
    print(old_db, db_path)
    shutil.copy(old_db, db_path)
    return 'sqlite:///{}'.format(db_path)


def test_upgrade(tmpdir):
    """Try to upgrade an old SQLite test database"""
    print(tmpdir)
    db_url = generate_old_db(str(tmpdir))
    print(db_url)
    upgrade(db_url)


def test_upgrade_entrypoint(tmpdir, io_loop):
    """Test upgrade of a database creates a backup"""
    generate_old_db(str(tmpdir))
    tmpdir.chdir()
    token_app = NewToken()
    token_app.initialize(['kaylee'])
    with raises(OperationalError):
        token_app.start()

    sqlite_files = glob(os.path.join(str(tmpdir), 'jupyterhub.sqlite*'))
    assert len(sqlite_files) == 1

    upgrade_app = UpgradeDB()
    io_loop.run_sync(lambda: upgrade_app.initialize([]))
    upgrade_app.start()

    # check that backup was created:
    sqlite_files = glob(os.path.join(str(tmpdir), 'jupyterhub.sqlite*'))
    assert len(sqlite_files) == 2

    # run token_app again, it should work
    token_app.start()
