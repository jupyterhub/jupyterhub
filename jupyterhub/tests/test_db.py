import os
import sys
import tempfile
from glob import glob
from subprocess import CalledProcessError, check_call

import alembic.command
import alembic.config
import pytest
from alembic.script import ScriptDirectory
from packaging.version import parse as V
from pytest import raises
from sqlalchemy import create_engine, text
from traitlets.config import Config

from .. import orm
from ..app import NewToken, UpgradeDB
from ..dbutil import _temp_alembic_ini
from ..scopes import _check_scopes_exist
from .populate_db import populate_db

here = os.path.abspath(os.path.dirname(__file__))
populate_db_py = os.path.join(here, 'populate_db.py')


pytestmark = pytest.mark.db


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
        if V(hub_version) < V("3.1.1"):
            pkgs.append('psycopg2-binary')
            db_url = db_url.replace("psycopg:", "psycopg2:")
        else:
            pkgs.append('psycopg[binary]')
    check_call([env_pip, 'install'] + pkgs)
    check_call([env_py, populate_db_py, db_url])


# changes to this version list must also be reflected
# in ci/init-db.sh
@pytest.mark.parametrize(
    'hub_version',
    ['1.1.0', '1.2.2', '1.3.0', '1.5.0', '2.1.1', '3.1.1', '4.1.6', '5.4.6'],
)
async def test_upgrade(tmpdir, hub_version):
    if sys.version_info >= (3, 13) and V(hub_version) < V("4"):
        pytest.skip("jupyterhub < 4 needs Python 3.12 or earlier")
    db_url = os.getenv('JUPYTERHUB_TEST_DB_URL')
    if db_url:
        db_url += '_upgrade_' + hub_version.replace('.', '')
    else:
        db_url = 'sqlite:///jupyterhub.sqlite'
    tmpdir.chdir()

    # use persistent temp env directory
    # to reuse across multiple runs
    env_dir = os.path.join(tempfile.gettempdir(), f'test-hub-upgrade-{hub_version}')

    generate_old_db(env_dir, hub_version, db_url)

    cfg = Config()
    cfg.JupyterHub.db_url = db_url

    tokenapp = NewToken(config=cfg)
    tokenapp.initialize(['admin'])
    with raises(SystemExit):
        tokenapp.start()

    if 'sqlite' in db_url:
        db_url.split(':///')[1]
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

    # make sure migrated roles are not managed or null
    for role in db.query(orm.Role):
        assert role.managed_by_auth is False
    for assignment_table in orm._role_associations.values():
        for assignment in db.query(assignment_table):
            assert assignment.managed_by_auth is False


@pytest.mark.parametrize(
    'hub_version, expected_revision',
    [
        ('5', '4621fec11365'),
        ('6.1', 'f460b0348206'),
    ],
)
async def test_downgrade(tmpdir, hub_version, expected_revision):
    db_url = os.getenv('JUPYTERHUB_TEST_DB_URL')
    if db_url:
        db_url += '_downgrade_' + hub_version.replace('.', '')
    else:
        db_url = 'sqlite:///jupyterhub.sqlite'
    tmpdir.chdir()
    populate_db(db_url)
    with _temp_alembic_ini(db_url) as ini:
        cfg = alembic.config.Config(ini)
        scripts = ScriptDirectory.from_config(cfg)
        head = scripts.get_heads()[0]
    check_call(
        [
            sys.executable,
            "-m",
            "jupyterhub",
            "downgrade-db",
            hub_version,
        ]
    )

    engine = create_engine(db_url)
    with engine.begin() as connection:
        alembic_revision = connection.execute(
            text('SELECT version_num FROM alembic_version')
        ).first()[0]

    # check downgraded state?
    assert alembic_revision == expected_revision

    check_call(
        [
            sys.executable,
            "-m",
            "jupyterhub",
            "upgrade-db",
        ]
    )
    with engine.begin() as connection:
        alembic_revision = connection.execute(
            text('SELECT version_num FROM alembic_version')
        ).first()[0]
    assert alembic_revision == head


@pytest.mark.parametrize(
    "version",
    [
        None,
        "1.0",
        "9.5",
        "notaversion",
    ],
)
async def test_downgrade_bad(tmpdir, capfd, version):
    cmd = [
        sys.executable,
        "-m",
        "jupyterhub",
        "downgrade-db",
    ]
    if version is not None:
        cmd.append(version)
    with pytest.raises(CalledProcessError):
        check_call(cmd)
    out = capfd.readouterr()
    assert "Traceback" not in out.err
    if version is None:
        assert "Specify a JupyterHub version" in out.err
    elif version == "notaversion":
        assert "Invalid version" in out.err
    else:
        assert f"{version} not supported" in out.err
