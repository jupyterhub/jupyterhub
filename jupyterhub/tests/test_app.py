"""Test the JupyterHub entry point"""

import os
import re
import sys
from getpass import getuser
from subprocess import check_output
from tempfile import NamedTemporaryFile

def test_help_all():
    out = check_output([sys.executable, '-m', 'jupyterhub', '--help-all']).decode('utf8', 'replace')
    assert '--ip' in out
    assert '--JupyterHub.ip' in out

def test_token_app():
    cmd = [sys.executable, '-m', 'jupyterhub', 'token']
    out = check_output(cmd + ['--help-all']).decode('utf8', 'replace')
    out = check_output(cmd + [getuser()]).decode('utf8', 'replace').strip()
    assert re.match(r'^[a-z0-9]+$', out)

def test_generate_config():
    with NamedTemporaryFile(prefix='jupyterhub_config', suffix='.py') as tf:
        cfg_file = tf.name
    
    out = check_output([sys.executable, '-m', 'jupyterhub',
        '--generate-config', '-f', cfg_file]
    ).decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with open(cfg_file) as f:
        cfg_text = f.read()
    os.remove(cfg_file)
    assert cfg_file in out
    assert 'Spawner.cmd' in cfg_text
    assert 'Authenticator.whitelist' in cfg_text
