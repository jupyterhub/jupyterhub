#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Juptyer Development Team.
# Distributed under the terms of the Modified BSD License.

#-----------------------------------------------------------------------------
# Minimal Python version sanity check (from IPython)
#-----------------------------------------------------------------------------

from __future__ import print_function

import os
import sys

v = sys.version_info
if v[:2] < (2,7) or (v[0] >= 3 and v[:2] < (3,3)):
    error = "ERROR: IPython requires Python version 2.7 or 3.3 or above."
    print(error, file=sys.stderr)
    sys.exit(1)

PY3 = (sys.version_info[0] >= 3)

if os.name in ('nt', 'dos'):
    error = "ERROR: Windows is not supported"
    print(error, file=sys.stderr)

# At least we're on the python version we need, move on.

import os

from glob import glob

from distutils.core import setup
from subprocess import check_call

try:
    execfile
except NameError:
    # py3
    def execfile(fname, globs, locs=None):
        locs = locs or globs
        exec(compile(open(fname).read(), fname, "exec"), globs, locs)

here = os.path.abspath(os.path.dirname(__file__))
pjoin = os.path.join

#---------------------------------------------------------------------------
# Build basic package data, etc.
#---------------------------------------------------------------------------

def get_data_files():
    """Get data files in share/jupyter"""
    
    data_files = []
    share_jupyter = pjoin(here, 'share', 'jupyter')
    ntrim = len(here) + 1
    
    for (d, dirs, filenames) in os.walk(share_jupyter):
        data_files.append((
            d[ntrim:],
            [ pjoin(d, f) for f in filenames ]
        ))
    return data_files


ns = {}
execfile(pjoin(here, 'jupyterhub', 'version.py'), ns)

setup_args = dict(
    name                = 'jupyterhub',
    scripts             = glob(pjoin('scripts', '*')),
    packages            = ['jupyterhub'],
    package_data        = {'jupyterhub' : ['templates/*']},
                        # dummy, so that install_data doesn't get skipped
                        # this will be overridden when bower is run anyway
    data_files          = get_data_files() or ['dummy'],
    version             = ns['__version__'],
    description         = """JupyterHub: A multi-user server for Jupyter notebooks""",
    long_description    = "",
    author              = "Jupyter Development Team",
    author_email        = "ipython-dev@scipy.org",
    url                 = "http://jupyter.org",
    license             = "BSD",
    platforms           = "Linux, Mac OS X",
    keywords            = ['Interactive', 'Interpreter', 'Shell', 'Web'],
    classifiers         = [
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Shells',
    ],
)

#---------------------------------------------------------------------------
# custom distutils commands
#---------------------------------------------------------------------------

# imports here, so they are after setuptools import if there was one
from distutils.cmd import Command
from distutils.command.install import install

class Bower(Command):
    description = "fetch static components with bower"
    
    user_options = []
    
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
    
    def run(self):
        check_call(['bower', 'install'])
        self.distribution.data_files = get_data_files()
    
    def get_outputs(self):
        return []
    
    def get_inputs(self):
        return []

# ensure bower is run as part of install
install.sub_commands.insert(0, ('bower', None))

setup_args['cmdclass'] = {
    'bower': Bower,
}

# setuptools requirements

if 'setuptools' in sys.modules:
    setup_args['zip_safe'] = False

    with open('requirements.txt') as f:
        install_requires = [ line.strip() for line in f.readlines() ]
    setup_args['install_requires'] = install_requires

#---------------------------------------------------------------------------
# setup
#---------------------------------------------------------------------------

def main():
    setup(**setup_args)

if __name__ == '__main__':
    main()
