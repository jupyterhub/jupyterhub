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
    db_path = os.path.join(path, "jupyterhub.sqlite")
    print(old_db, db_path)
    shutil.copy(old_db, db_path)
    return 'sqlite:///%s' % db_path

def test_upgrade(tmpdir):
    print(tmpdir)
    db_url = generate_old_db(str(tmpdir))
    print(db_url)
    upgrade(db_url)

def test_upgrade_entrypoint(tmpdir, io_loop):
    generate_old_db(str(tmpdir))
    tmpdir.chdir()
    tokenapp = NewToken()
    tokenapp.initialize(['kaylee'])
    with raises(OperationalError):
        tokenapp.start()

    sqlite_files = glob(os.path.join(str(tmpdir), 'jupyterhub.sqlite*'))
    assert len(sqlite_files) == 1

    upgradeapp = UpgradeDB()
    io_loop.run_sync(lambda : upgradeapp.initialize([]))
    upgradeapp.start()

    # check that backup was created:
    sqlite_files = glob(os.path.join(str(tmpdir), 'jupyterhub.sqlite*'))
    assert len(sqlite_files) == 2

    # run tokenapp again, it should work
    tokenapp.start()
    