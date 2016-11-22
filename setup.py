#!/usr/bin/env python3
# coding: utf-8

# Copyright (c) Juptyer Development Team.
# Distributed under the terms of the Modified BSD License.

#-----------------------------------------------------------------------------
# Minimal Python version sanity check (from IPython)
#-----------------------------------------------------------------------------

from __future__ import print_function

import os
import shutil
import sys

v = sys.version_info
if v[:2] < (3,3):
    error = "ERROR: JupyterHub requires Python version 3.3 or above."
    print(error, file=sys.stderr)
    sys.exit(1)


if os.name in ('nt', 'dos'):
    error = "ERROR: Windows is not supported"
    print(error, file=sys.stderr)

# At least we're on the python version we need, move on.

import os
from glob import glob
from subprocess import check_call

from setuptools import setup
from setuptools.command.bdist_egg import bdist_egg

pjoin = os.path.join

here = os.path.abspath(os.path.dirname(__file__))
share_jupyter = pjoin(here, 'share', 'jupyter', 'hub')
static = pjoin(share_jupyter, 'static')

is_repo = os.path.exists(pjoin(here, '.git'))

#---------------------------------------------------------------------------
# Build basic package data, etc.
#---------------------------------------------------------------------------

def get_data_files():
    """Get data files in share/jupyter"""
    
    data_files = []
    ntrim = len(here + os.path.sep)
    
    for (d, dirs, filenames) in os.walk(share_jupyter):
        data_files.append((
            d[ntrim:],
            [ pjoin(d, f) for f in filenames ]
        ))
    return data_files

def get_package_data():
    """Get package data

    (mostly alembic config)
    """
    package_data = {}
    package_data['jupyterhub'] = [
        'alembic.ini',
        'alembic/*',
        'alembic/versions/*',
    ]
    return package_data

ns = {}
with open(pjoin(here, 'jupyterhub', 'version.py')) as f:
    exec(f.read(), {}, ns)


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
    package_data        = get_package_data(),
    version             = ns['__version__'],
    description         = "JupyterHub: A multi-user server for Jupyter notebooks",
    long_description    = "See https://jupyterhub.readthedocs.io for more info.",
    author              = "Jupyter Development Team",
    author_email        = "jupyter@googlegroups.com",
    url                 = "http://jupyter.org",
    license             = "BSD",
    platforms           = "Linux, Mac OS X",
    keywords            = ['Interactive', 'Interpreter', 'Shell', 'Web'],
    classifiers         = [
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
)

#---------------------------------------------------------------------------
# custom distutils commands
#---------------------------------------------------------------------------

# imports here, so they are after setuptools import if there was one
from distutils.cmd import Command
from distutils.command.build_py import build_py
from distutils.command.sdist import sdist


npm_path = ':'.join([
    pjoin(here, 'node_modules', '.bin'),
    os.environ.get("PATH", os.defpath),
])


def mtime(path):
    """shorthand for mtime"""
    return os.stat(path).st_mtime


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
    description = "fetch static client-side components with bower"
    
    user_options = []
    bower_dir = pjoin(static, 'components')
    node_modules = pjoin(here, 'node_modules')
    
    def should_run(self):
        if not os.path.exists(self.bower_dir):
            return True
        return mtime(self.bower_dir) < mtime(pjoin(here, 'bower.json'))

    def should_run_npm(self):
        if not shutil.which('npm'):
            print("npm unavailable", file=sys.stderr)
            return False
        if not os.path.exists(self.node_modules):
            return True
        return mtime(self.node_modules) < mtime(pjoin(here, 'package.json'))
    
    def run(self):
        if not self.should_run():
            print("bower dependencies up to date")
            return
        
        if self.should_run_npm():
            print("installing build dependencies with npm")
            check_call(['npm', 'install', '--progress=false'], cwd=here)
            os.utime(self.node_modules)
        
        env = os.environ.copy()
        env['PATH'] = npm_path
        
        try:
            check_call(
                ['bower', 'install', '--allow-root', '--config.interactive=false'],
                cwd=here,
                env=env,
            )
        except OSError as e:
            print("Failed to run bower: %s" % e, file=sys.stderr)
            print("You can install js dependencies with `npm install`", file=sys.stderr)
            raise
        os.utime(self.bower_dir)
        # update data-files in case this created new files
        self.distribution.data_files = get_data_files()


class CSS(BaseCommand):
    description = "compile CSS from LESS"
    
    def should_run(self):
        """Does less need to run?"""
        # from IPython.html.tasks.py
        
        css_targets = [pjoin(static, 'css', 'style.min.css')]
        css_maps = [t + '.map' for t in css_targets]
        targets = css_targets + css_maps
        if not all(os.path.exists(t) for t in targets):
            # some generated files don't exist
            return True
        earliest_target = sorted(mtime(t) for t in targets)[0]
    
        # check if any .less files are newer than the generated targets
        for (dirpath, dirnames, filenames) in os.walk(static):
            for f in filenames:
                if f.endswith('.less'):
                    path = pjoin(static, dirpath, f)
                    timestamp = mtime(path)
                    if timestamp > earliest_target:
                        return True
    
        return False
    
    def run(self):
        if not self.should_run():
            print("CSS up-to-date")
            return
        
        self.run_command('js')
        
        style_less = pjoin(static, 'less', 'style.less')
        style_css = pjoin(static, 'css', 'style.min.css')
        sourcemap = style_css + '.map'
        
        env = os.environ.copy()
        env['PATH'] = npm_path
        try:
            check_call([
                'lessc', '--clean-css',
                '--source-map-basepath={}'.format(static),
                '--source-map={}'.format(sourcemap),
                '--source-map-rootpath=../',
                style_less, style_css,
            ], cwd=here, env=env)
        except OSError as e:
            print("Failed to run lessc: %s" % e, file=sys.stderr)
            print("You can install js dependencies with `npm install`", file=sys.stderr)
            raise
        # update data-files in case this created new files
        self.distribution.data_files = get_data_files()


def js_css_first(cls, strict=True):
    class Command(cls):
        def run(self):
            try:
                self.run_command('js')
                self.run_command('css')
            except Exception:
                if strict:
                    raise
                else:
                    pass
            return super().run()
    return Command


class bdist_egg_disabled(bdist_egg):
    """Disabled version of bdist_egg

    Prevents setup.py install performing setuptools' default easy_install,
    which it should never ever do.
    """
    def run(self):
        sys.exit("Aborting implicit building of eggs. Use `pip install .` to install from source.")


setup_args['cmdclass'] = {
    'js': Bower,
    'css': CSS,
    'build_py': js_css_first(build_py, strict=is_repo),
    'sdist': js_css_first(sdist, strict=True),
    'bdist_egg': bdist_egg if 'bdist_egg' in sys.argv else bdist_egg_disabled,
}


# setuptools requirements

setup_args['zip_safe'] = False
from setuptools.command.develop import develop
class develop_js_css(develop):
    def run(self):
        if not self.uninstall:
            self.distribution.run_command('js')
            self.distribution.run_command('css')
        develop.run(self)
setup_args['cmdclass']['develop'] = develop_js_css
setup_args['install_requires'] = install_requires = []

with open('requirements.txt') as f:
    for line in f.readlines():
        req = line.strip()
        if not req or req.startswith('#') or '://' in req:
            continue
        install_requires.append(req)

#---------------------------------------------------------------------------
# setup
#---------------------------------------------------------------------------

def main():
    setup(**setup_args)

if __name__ == '__main__':
    main()
