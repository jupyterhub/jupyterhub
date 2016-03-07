"""Test the JupyterHub entry point"""

import os
import re
import sys
from subprocess import check_output, Popen, PIPE
from tempfile import NamedTemporaryFile, TemporaryDirectory
from .mocking import MockHub

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
