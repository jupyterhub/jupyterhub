"""Test the JupyterHub entry point"""
import binascii
import os
import re
import sys
import time
from subprocess import check_output
from subprocess import PIPE
from subprocess import Popen
from tempfile import NamedTemporaryFile
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from traitlets.config import Config

from .. import orm
from ..app import COOKIE_SECRET_BYTES
from ..app import JupyterHub
from .mocking import MockHub
from .test_api import add_user


def test_help_all():
    out = check_output([sys.executable, '-m', 'jupyterhub', '--help-all']).decode(
        'utf8', 'replace'
    )
    assert '--ip' in out
    assert '--JupyterHub.ip' in out


def test_token_app():
    cmd = [sys.executable, '-m', 'jupyterhub', 'token']
    out = check_output(cmd + ['--help-all']).decode('utf8', 'replace')
    with TemporaryDirectory() as td:
        with open(os.path.join(td, 'jupyterhub_config.py'), 'w') as f:
            f.write("c.Authenticator.admin_users={'user'}")
        out = check_output(cmd + ['user'], cwd=td).decode('utf8', 'replace').strip()
    assert re.match(r'^[a-z0-9]+$', out)


def test_raise_error_on_missing_specified_config():
    """
    Using the -f or --config flag when starting JupyterHub should require the
    file to be found and exit if it isn't.
    """
    # subprocess.run doesn't have a timeout flag, so if this test would fail by
    # not letting jupyterhub error out, we would wait forever. subprocess.Popen
    # allow us to manually timeout.
    process = Popen(
        [sys.executable, '-m', 'jupyterhub', '--config', 'not-available.py']
    )
    # wait inpatiently for the process to exit like we want it to
    for i in range(100):
        time.sleep(0.1)
        returncode = process.poll()
        if returncode is not None:
            break
    else:
        process.kill()
    assert returncode == 1


def test_generate_config():
    with NamedTemporaryFile(prefix='jupyterhub_config', suffix='.py') as tf:
        cfg_file = tf.name
    with open(cfg_file, 'w') as f:
        f.write("c.A = 5")
    p = Popen(
        [sys.executable, '-m', 'jupyterhub', '--generate-config', '-f', cfg_file],
        stdout=PIPE,
        stdin=PIPE,
    )
    out, _ = p.communicate(b'n')
    out = out.decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    assert cfg_text == 'c.A = 5'

    p = Popen(
        [sys.executable, '-m', 'jupyterhub', '--generate-config', '-f', cfg_file],
        stdout=PIPE,
        stdin=PIPE,
    )
    out, _ = p.communicate(b'x\ny')
    out = out.decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    os.remove(cfg_file)
    assert cfg_file in out
    assert 'Spawner.cmd' in cfg_text
    assert 'Authenticator.allowed_users' in cfg_text


async def test_init_tokens(request):
    with TemporaryDirectory() as td:
        db_file = os.path.join(td, 'jupyterhub.sqlite')
        tokens = {
            'super-secret-token': 'alyx',
            'also-super-secret': 'gordon',
            'boagasdfasdf': 'chell',
        }
        kwargs = {'db_url': db_file, 'api_tokens': tokens}
        ssl_enabled = getattr(request.module, "ssl_enabled", False)
        if ssl_enabled:
            kwargs['internal_certs_location'] = td
        app = MockHub(**kwargs)
        await app.initialize([])
        db = app.db
        for token, username in tokens.items():
            api_token = orm.APIToken.find(db, token)
            assert api_token is not None
            user = api_token.user
            assert user.name == username

        # simulate second startup, reloading same tokens:
        app = MockHub(**kwargs)
        await app.initialize([])
        db = app.db
        for token, username in tokens.items():
            api_token = orm.APIToken.find(db, token)
            assert api_token is not None
            user = api_token.user
            assert user.name == username

        # don't allow failed token insertion to create users:
        tokens['short'] = 'gman'
        app = MockHub(**kwargs)
        with pytest.raises(ValueError):
            await app.initialize([])
        assert orm.User.find(app.db, 'gman') is None


def test_write_cookie_secret(tmpdir, request):
    secret_path = str(tmpdir.join('cookie_secret'))
    kwargs = {'cookie_secret_file': secret_path}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_secrets()
    assert os.path.exists(secret_path)
    assert os.stat(secret_path).st_mode & 0o600
    assert not os.stat(secret_path).st_mode & 0o177


def test_cookie_secret_permissions(tmpdir, request):
    secret_file = tmpdir.join('cookie_secret')
    secret_path = str(secret_file)
    secret = os.urandom(COOKIE_SECRET_BYTES)
    secret_file.write(binascii.b2a_hex(secret))
    kwargs = {'cookie_secret_file': secret_path}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)

    # raise with public secret file
    os.chmod(secret_path, 0o664)
    with pytest.raises(SystemExit):
        hub.init_secrets()

    # ok with same file, proper permissions
    os.chmod(secret_path, 0o660)
    hub.init_secrets()
    assert hub.cookie_secret == secret


def test_cookie_secret_content(tmpdir, request):
    secret_file = tmpdir.join('cookie_secret')
    secret_file.write('not base 64: uñiço∂e')
    secret_path = str(secret_file)
    os.chmod(secret_path, 0o660)
    kwargs = {'cookie_secret_file': secret_path}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    with pytest.raises(SystemExit):
        hub.init_secrets()


def test_cookie_secret_env(tmpdir, request):
    kwargs = {'cookie_secret_file': str(tmpdir.join('cookie_secret'))}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)

    with patch.dict(os.environ, {'JPY_COOKIE_SECRET': 'not hex'}):
        with pytest.raises(ValueError):
            hub.init_secrets()

    with patch.dict(os.environ, {'JPY_COOKIE_SECRET': 'abc123'}):
        hub.init_secrets()
    assert hub.cookie_secret == binascii.a2b_hex('abc123')
    assert not os.path.exists(hub.cookie_secret_file)


async def test_load_groups(tmpdir, request):
    to_load = {
        'blue': ['cyclops', 'rogue', 'wolverine'],
        'gold': ['storm', 'jean-grey', 'colossus'],
    }
    kwargs = {'load_groups': to_load}
    ssl_enabled = getattr(request.module, "ssl_enabled", False)
    if ssl_enabled:
        kwargs['internal_certs_location'] = str(tmpdir)
    hub = MockHub(**kwargs)
    hub.init_db()
    await hub.init_users()
    await hub.init_groups()
    db = hub.db
    blue = orm.Group.find(db, name='blue')
    assert blue is not None
    assert sorted([u.name for u in blue.users]) == sorted(to_load['blue'])
    gold = orm.Group.find(db, name='gold')
    assert gold is not None
    assert sorted([u.name for u in gold.users]) == sorted(to_load['gold'])


async def test_resume_spawners(tmpdir, request):
    if not os.getenv('JUPYTERHUB_TEST_DB_URL'):
        p = patch.dict(
            os.environ,
            {
                'JUPYTERHUB_TEST_DB_URL': 'sqlite:///%s'
                % tmpdir.join('jupyterhub.sqlite')
            },
        )
        p.start()
        request.addfinalizer(p.stop)

    async def new_hub():
        kwargs = {}
        ssl_enabled = getattr(request.module, "ssl_enabled", False)
        if ssl_enabled:
            kwargs['internal_certs_location'] = str(tmpdir)
        app = MockHub(test_clean_db=False, **kwargs)
        app.config.ConfigurableHTTPProxy.should_start = False
        app.config.ConfigurableHTTPProxy.auth_token = 'unused'
        await app.initialize([])
        return app

    app = await new_hub()
    db = app.db
    # spawn a user's server
    name = 'kurt'
    user = add_user(db, app, name=name)
    await user.spawn()
    proc = user.spawner.proc
    assert proc is not None

    # stop the Hub without cleaning up servers
    app.cleanup_servers = False
    app.stop()

    # proc is still running
    assert proc.poll() is None

    # resume Hub, should still be running
    app = await new_hub()
    db = app.db
    user = app.users[name]
    assert user.running
    assert user.spawner.server is not None

    # stop the Hub without cleaning up servers
    app.cleanup_servers = False
    app.stop()

    # stop the server while the Hub is down. BAMF!
    proc.terminate()
    proc.wait(timeout=10)
    assert proc.poll() is not None

    # resume Hub, should be stopped
    app = await new_hub()
    db = app.db
    user = app.users[name]
    assert not user.running
    assert user.spawner.server is None
    assert list(db.query(orm.Server)) == []


@pytest.mark.parametrize(
    'hub_config, expected',
    [
        ({'ip': '0.0.0.0'}, {'bind_url': 'http://0.0.0.0:8000/'}),
        (
            {'port': 123, 'base_url': '/prefix'},
            {'bind_url': 'http://:123/prefix/', 'base_url': '/prefix/'},
        ),
        ({'bind_url': 'http://0.0.0.0:12345/sub'}, {'base_url': '/sub/'}),
        (
            # no config, test defaults
            {},
            {'base_url': '/', 'bind_url': 'http://:8000', 'ip': '', 'port': 8000},
        ),
    ],
)
def test_url_config(hub_config, expected):
    # construct the config object
    cfg = Config()
    for key, value in hub_config.items():
        cfg.JupyterHub[key] = value

    # instantiate the Hub and load config
    app = JupyterHub(config=cfg)
    # validate config
    for key, value in hub_config.items():
        if key not in expected:
            assert getattr(app, key) == value

    # validate additional properties
    for key, value in expected.items():
        assert getattr(app, key) == value
