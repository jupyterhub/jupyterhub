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

pjoin = os.path.join

here = os.path.abspath(os.path.dirname(__file__))
share_jupyter = pjoin(here, 'share', 'jupyter')
static = pjoin(share_jupyter, 'static')

#---------------------------------------------------------------------------
# Build basic package data, etc.
#---------------------------------------------------------------------------

def get_data_files():
    """Get data files in share/jupyter"""
    
    data_files = []
    ntrim = len(here) + 1
    
    for (d, dirs, filenames) in os.walk(share_jupyter):
        data_files.append((
            d[ntrim:],
            [ pjoin(d, f) for f in filenames ]
        ))
    return data_files


ns = {}
execfile(pjoin(here, 'jupyterhub', 'version.py'), ns)

packages = []
for d, _, _ in os.walk('jupyterhub'):
    if os.path.exists(pjoin(d, '__init__.py')):
        packages.append(d.replace(os.path.sep, '.'))

setup_args = dict(
    name                = 'jupyterhub',
    scripts             = glob(pjoin('scripts', '*')),
    packages            = packages,
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

class BaseCommand(Command):
    """Dumb empty command because Command needs subclasses to override too much"""
    user_options = []
    
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
    
    def get_inputs(self):
        return []
    
    def get_outputs(self):
        return []


class Bower(BaseCommand):
    description = "fetch static components with bower"
    
    user_options = []
    
    def run(self):
        try:
            check_call(['bower', 'install', '--allow-root'])
        except OSError as e:
            print("Failed to run bower: %s" % e, file=sys.stderr)
            print("You can install bower with `npm install -g bower`", file=sys.stderr)
            raise
        # update data-files in case this created new files
        self.distribution.data_files = get_data_files()

class CSS(BaseCommand):
    description = "compile CSS from LESS"
    
    user_options = []
    
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
    
    def run(self):
        style_less = pjoin(static, 'less', 'style.less')
        style_css = pjoin(static, 'css', 'style.min.css')
        sourcemap = style_css + '.map'
        try:
            check_call([
                'lessc', '-x', '--verbose',
                '--source-map-basepath={}'.format(static),
                '--source-map={}'.format(sourcemap),
                '--source-map-rootpath=../',
                style_less, style_css,
            ])
        except OSError as e:
            print("Failed to run lessc: %s" % e, file=sys.stderr)
            print("You can install less with `npm install -g less`", file=sys.stderr)
            raise
        # update data-files in case this created new files
        self.distribution.data_files = get_data_files()

# ensure bower is run as part of install
install.sub_commands.insert(0, ('bower', None))
install.sub_commands.insert(1, ('css', None))

setup_args['cmdclass'] = {
    'bower': Bower,
    'css': CSS,
}


# setuptools requirements

if 'setuptools' in sys.modules:
    setup_args['zip_safe'] = False
    from setuptools.command.develop import develop
    class develop_js_css(develop):
        def run(self):
            if not self.uninstall:
                self.distribution.run_command('bower')
                self.distribution.run_command('css')
            develop.run(self)
    setup_args['cmdclass']['develop'] = develop_js_css


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
