from glob import glob
import os
import shutil

import pytest
from pytest import raises
from traitlets.config import Config

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
    upgrade(db_url)

@pytest.mark.gen_test
def test_upgrade_entrypoint(tmpdir):
    db_url = os.getenv('JUPYTERHUB_TEST_UPGRADE_DB_URL')
    if not db_url:
        # default: sqlite
        db_url = generate_old_db(str(tmpdir))
    cfg = Config()
    cfg.JupyterHub.db_url = db_url

    tmpdir.chdir()
    tokenapp = NewToken(config=cfg)
    tokenapp.initialize(['kaylee'])
    with raises(SystemExit):
        tokenapp.start()

    if 'sqlite' in db_url:
        sqlite_files = glob(os.path.join(str(tmpdir), 'jupyterhub.sqlite*'))
        assert len(sqlite_files) == 1

    upgradeapp = UpgradeDB(config=cfg)
    yield upgradeapp.initialize([])
    upgradeapp.start()

    # check that backup was created:
    if 'sqlite' in db_url:
        sqlite_files = glob(os.path.join(str(tmpdir), 'jupyterhub.sqlite*'))
        assert len(sqlite_files) == 2

    # run tokenapp again, it should work
    tokenapp.start()
