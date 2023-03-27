import os
import sys
import tempfile
from glob import glob
from subprocess import check_call

import pytest
from packaging.version import parse as V
from pytest import raises
from traitlets.config import Config

from .. import orm
from ..app import NewToken, UpgradeDB
from ..scopes import _check_scopes_exist

here = os.path.abspath(os.path.dirname(__file__))
populate_db = os.path.join(here, 'populate_db.py')


def generate_old_db(env_dir, hub_version, db_url):
    """Generate an old jupyterhub database

    Installs a particular jupyterhub version in a virtualenv
    and runs populate_db.py to populate a database
    """
    env_pip = os.path.join(env_dir, 'bin', 'pip')
    env_py = os.path.join(env_dir, 'bin', 'python')
    check_call([sys.executable, '-m', 'virtualenv', env_dir])
    pkgs = ['jupyterhub==' + hub_version]

    # older jupyterhub needs older sqlachemy version
    if V(hub_version) < V("2"):
        pkgs.append('sqlalchemy<1.4')
    elif V(hub_version) < V("3.1.1"):
        pkgs.append('sqlalchemy<2')

    if 'mysql' in db_url:
        pkgs.append('mysqlclient')
    elif 'postgres' in db_url:
        pkgs.append('psycopg2-binary')
    check_call([env_pip, 'install'] + pkgs)
    check_call([env_py, populate_db, db_url])


# changes to this version list must also be reflected
# in ci/init-db.sh
@pytest.mark.parametrize('hub_version', ["1.1.0", "1.2.2", "1.3.0", "1.5.0", "2.1.1"])
async def test_upgrade(tmpdir, hub_version):
    db_url = os.getenv('JUPYTERHUB_TEST_DB_URL')
    if db_url:
        db_url += '_upgrade_' + hub_version.replace('.', '')
    else:
        db_url = 'sqlite:///jupyterhub.sqlite'
    tmpdir.chdir()

    # use persistent temp env directory
    # to reuse across multiple runs
    env_dir = os.path.join(tempfile.gettempdir(), 'test-hub-upgrade-%s' % hub_version)

    generate_old_db(env_dir, hub_version, db_url)

    cfg = Config()
    cfg.JupyterHub.db_url = db_url

    tokenapp = NewToken(config=cfg)
    tokenapp.initialize(['admin'])
    with raises(SystemExit):
        tokenapp.start()

    if 'sqlite' in db_url:
        fname = db_url.split(':///')[1]
        sqlite_files = glob(os.path.join(str(tmpdir), 'jupyterhub.sqlite*'))
        assert len(sqlite_files) == 1

    upgradeapp = UpgradeDB(config=cfg)
    upgradeapp.initialize([])
    upgradeapp.start()

    # check that backup was created:
    if 'sqlite' in db_url:
        sqlite_files = glob(os.path.join(str(tmpdir), 'jupyterhub.sqlite*'))
        assert len(sqlite_files) == 2

    # run tokenapp again, it should work
    tokenapp.start()

    db = orm.new_session_factory(db_url)()
    query = db.query(orm.APIToken)
    assert query.count() >= 1
    for token in query:
        assert token.scopes, f"Upgraded token {token} has no scopes"
        _check_scopes_exist(token.scopes)
