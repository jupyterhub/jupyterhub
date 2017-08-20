#!/usr/bin/env python
import os
from subprocess import check_call
import sys

V = os.environ['JUPYTERHUB_VERSION']

pip_install = [
    sys.executable, '-m', 'pip', 'install', '--no-cache', '--upgrade',
    '--upgrade-strategy', 'only-if-needed',
]
if V == 'master':
    req = 'https://github.com/jupyterhub/jupyterhub/archive/master.tar.gz'
else:
    version_info = [ int(part) for part in V.split('.') ]
    version_info[-1] += 1
    upper_bound = '.'.join(map(str, version_info))
    vs = '>=%s,<%s' % (V, upper_bound)
    req = 'jupyterhub%s' % vs

check_call(pip_install + [req])
