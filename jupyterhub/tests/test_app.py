"""Test the JupyterHubApp entry point"""

import io
import os
import sys
from subprocess import check_output
from tempfile import NamedTemporaryFile

def test_help_all():
    out = check_output([sys.executable, '-m', 'jupyterhub', '--help-all']).decode('utf8', 'replace')
    assert u'--ip' in out
    assert u'--JupyterHubApp.ip' in out

def test_generate_config():
    with NamedTemporaryFile(prefix='jupyter_hub_config', suffix='.py') as tf:
        cfg_file = tf.name
    
    out = check_output([sys.executable, '-m', 'jupyterhub',
        '--generate-config', '-f', cfg_file]
    ).decode('utf8', 'replace')
    assert os.path.exists(cfg_file)
    with io.open(cfg_file) as f:
        cfg_text = f.read()
    os.remove(cfg_file)
    assert cfg_file in out
    assert 'Spawner.cmd' in cfg_text
    assert 'Authenticator.whitelist' in cfg_text
