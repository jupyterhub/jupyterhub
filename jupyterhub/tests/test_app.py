"""Test the JupyterHubApp entry point"""

import sys
from subprocess import check_output

def test_help_all():
    out = check_output([sys.executable, '-m', 'jupyterhub', '--help-all']).decode('utf8', 'replace')
    assert u'--ip' in out
    assert u'--JupyterHubApp.ip' in out

    