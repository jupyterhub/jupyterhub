"""Test the JupyterHub entry point"""

import binascii
import os
import re
import sys
from subprocess import check_output, Popen, PIPE
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import patch

import pytest

from .mocking import MockHub
from .. import orm

def test_help_all():
    out = check_output([sys.executable, '-m', 'jupyterhub', '--help-all']).decode('utf8', 'replace')
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

def test_generate_config():
    with NamedTemporaryFile(prefix='jupyterhub_config', suffix='.py') as tf:
        cfg_file = tf.name
    with open(cfg_file, 'w') as f:
        f.write("c.A = 5")
    p = Popen([sys.executable, '-m', 'jupyterhub',
        '--generate-config', '-f', cfg_file],
        stdout=PIPE, stdin=PIPE)
    out, _ = p.communicate(b'n')
    out = out.decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    assert cfg_text == 'c.A = 5'

    p = Popen([sys.executable, '-m', 'jupyterhub',
        '--generate-config', '-f', cfg_file],
        stdout=PIPE, stdin=PIPE)
    out, _ = p.communicate(b'x\ny')
    out = out.decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    os.remove(cfg_file)
    assert cfg_file in out
    assert 'Spawner.cmd' in cfg_text
    assert 'Authenticator.whitelist' in cfg_text

def test_init_tokens(io_loop):
    with TemporaryDirectory() as td:
        db_file = os.path.join(td, 'jupyterhub.sqlite')
        tokens = {
            'super-secret-token': 'alyx',
            'also-super-secret': 'gordon',
            'boagasdfasdf': 'chell',
        }
        app = MockHub(db_url=db_file, api_tokens=tokens)
        io_loop.run_sync(lambda : app.initialize([]))
        db = app.db
        for token, username in tokens.items():
            api_token = orm.APIToken.find(db, token)
            assert api_token is not None
            user = api_token.user
            assert user.name == username
        
        # simulate second startup, reloading same tokens:
        app = MockHub(db_url=db_file, api_tokens=tokens)
        io_loop.run_sync(lambda : app.initialize([]))
        db = app.db
        for token, username in tokens.items():
            api_token = orm.APIToken.find(db, token)
            assert api_token is not None
            user = api_token.user
            assert user.name == username
        
        # don't allow failed token insertion to create users:
        tokens['short'] = 'gman'
        app = MockHub(db_url=db_file, api_tokens=tokens)
        with pytest.raises(ValueError):
            io_loop.run_sync(lambda : app.initialize([]))
        assert orm.User.find(app.db, 'gman') is None


def test_write_cookie_secret(tmpdir):
    secret_path = str(tmpdir.join('cookie_secret'))
    hub = MockHub(cookie_secret_file=secret_path)
    hub.init_secrets()
    assert os.path.exists(secret_path)
    assert os.stat(secret_path).st_mode & 0o600
    assert not os.stat(secret_path).st_mode & 0o177


def test_cookie_secret_permissions(tmpdir):
    secret_file = tmpdir.join('cookie_secret')
    secret_path = str(secret_file)
    secret = os.urandom(1024)
    secret_file.write(binascii.b2a_base64(secret))
    hub = MockHub(cookie_secret_file=secret_path)

    # raise with public secret file
    os.chmod(secret_path, 0o664)
    with pytest.raises(SystemExit):
        hub.init_secrets()

    # ok with same file, proper permissions
    os.chmod(secret_path, 0o660)
    hub.init_secrets()
    assert hub.cookie_secret == secret


def test_cookie_secret_content(tmpdir):
    secret_file = tmpdir.join('cookie_secret')
    secret_file.write('not base 64: uñiço∂e')
    secret_path = str(secret_file)
    os.chmod(secret_path, 0o660)
    hub = MockHub(cookie_secret_file=secret_path)
    with pytest.raises(SystemExit):
        hub.init_secrets()


def test_cookie_secret_env(tmpdir):
    hub = MockHub(cookie_secret_file=str(tmpdir.join('cookie_secret')))

    with patch.dict(os.environ, {'JPY_COOKIE_SECRET': 'not hex'}):
        with pytest.raises(ValueError):
            hub.init_secrets()

    with patch.dict(os.environ, {'JPY_COOKIE_SECRET': 'abc123'}):
        hub.init_secrets()
    assert hub.cookie_secret == binascii.a2b_hex('abc123')
    assert not os.path.exists(hub.cookie_secret_file)


def test_load_groups(io_loop):
    to_load = {
        'blue': ['cyclops', 'rogue', 'wolverine'],
        'gold': ['storm', 'jean-grey', 'colossus'],
    }
    hub = MockHub(load_groups=to_load)
    hub.init_db()
    io_loop.run_sync(hub.init_users)
    hub.init_groups()
    db = hub.db
    blue = orm.Group.find(db, name='blue')
    assert blue is not None
    assert sorted([ u.name for u in blue.users ]) == sorted(to_load['blue'])
    gold = orm.Group.find(db, name='gold')
    assert gold is not None
    assert sorted([ u.name for u in gold.users ]) == sorted(to_load['gold'])
