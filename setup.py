#!/usr/bin/env python3
# coding: utf-8
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
# -----------------------------------------------------------------------------
# Minimal Python version sanity check (from IPython)
# -----------------------------------------------------------------------------
from __future__ import print_function

import os
import shutil
import sys
from subprocess import check_call

from setuptools import setup
from setuptools.command.bdist_egg import bdist_egg


v = sys.version_info
if v[:2] < (3, 6):
    error = "ERROR: JupyterHub requires Python version 3.6 or above."
    print(error, file=sys.stderr)
    sys.exit(1)

shell = False
if os.name in ('nt', 'dos'):
    shell = True
    warning = "WARNING: Windows is not officially supported"
    print(warning, file=sys.stderr)


pjoin = os.path.join

here = os.path.abspath(os.path.dirname(__file__))
share_jupyterhub = pjoin(here, 'share', 'jupyterhub')
static = pjoin(share_jupyterhub, 'static')

is_repo = os.path.exists(pjoin(here, '.git'))

# ---------------------------------------------------------------------------
# Build basic package data, etc.
# ---------------------------------------------------------------------------


def get_data_files():
    """Get data files in share/jupyter"""

    data_files = []
    ntrim = len(here + os.path.sep)

    for (d, dirs, filenames) in os.walk(share_jupyterhub):
        data_files.append((d[ntrim:], [pjoin(d, f) for f in filenames]))
    return data_files


def get_package_data():
    """Get package data

    (mostly alembic config)
    """
    package_data = {}
    package_data['jupyterhub'] = ['alembic.ini', 'alembic/*', 'alembic/versions/*']
    return package_data


ns = {}
with open(pjoin(here, 'jupyterhub', '_version.py')) as f:
    exec(f.read(), {}, ns)


packages = []
for d, _, _ in os.walk('jupyterhub'):
    if os.path.exists(pjoin(d, '__init__.py')):
        packages.append(d.replace(os.path.sep, '.'))

with open('README.md', encoding="utf8") as f:
    readme = f.read()


setup_args = dict(
    name='jupyterhub',
    packages=packages,
    # dummy, so that install_data doesn't get skipped
    # this will be overridden when bower is run anyway
    data_files=get_data_files() or ['dummy'],
    package_data=get_package_data(),
    version=ns['__version__'],
    description="JupyterHub: A multi-user server for Jupyter notebooks",
    long_description=readme,
    long_description_content_type='text/markdown',
    author="Jupyter Development Team",
    author_email="jupyter@googlegroups.com",
    url="https://jupyter.org",
    license="BSD",
    platforms="Linux, Mac OS X",
    keywords=['Interactive', 'Interpreter', 'Shell', 'Web'],
    python_requires=">=3.6",
    entry_points={
        'jupyterhub.authenticators': [
            'default = jupyterhub.auth:PAMAuthenticator',
            'pam = jupyterhub.auth:PAMAuthenticator',
            'dummy = jupyterhub.auth:DummyAuthenticator',
        ],
        'jupyterhub.proxies': [
            'default = jupyterhub.proxy:ConfigurableHTTPProxy',
            'configurable-http-proxy = jupyterhub.proxy:ConfigurableHTTPProxy',
        ],
        'jupyterhub.spawners': [
            'default = jupyterhub.spawner:LocalProcessSpawner',
            'localprocess = jupyterhub.spawner:LocalProcessSpawner',
            'simple = jupyterhub.spawner:SimpleLocalProcessSpawner',
        ],
        'console_scripts': [
            'jupyterhub = jupyterhub.app:main',
            'jupyterhub-singleuser = jupyterhub.singleuser:main',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    project_urls={
        'Documentation': 'https://jupyterhub.readthedocs.io',
        'Funding': 'https://jupyter.org/about',
        'Source': 'https://github.com/jupyterhub/jupyterhub/',
        'Tracker': 'https://github.com/jupyterhub/jupyterhub/issues',
    },
)

# ---------------------------------------------------------------------------
# custom distutils commands
# ---------------------------------------------------------------------------

# imports here, so they are after setuptools import if there was one
from distutils.cmd import Command
from distutils.command.build_py import build_py
from distutils.command.sdist import sdist


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


class NPM(BaseCommand):
    description = "fetch static client-side components with bower"

    user_options = []
    node_modules = pjoin(here, 'node_modules')
    bower_dir = pjoin(static, 'components')

    def should_run(self):
        if not shutil.which('npm'):
            print("npm unavailable", file=sys.stderr)
            return False
        if not os.path.exists(self.bower_dir):
            return True
        if not os.path.exists(self.node_modules):
            return True
        if mtime(self.bower_dir) < mtime(self.node_modules):
            return True
        return mtime(self.node_modules) < mtime(pjoin(here, 'package.json'))

    def run(self):
        if not self.should_run():
            print("npm dependencies up to date")
            return

        print("installing js dependencies with npm")
        check_call(
            ['npm', 'install', '--progress=false', '--unsafe-perm'],
            cwd=here,
            shell=shell,
        )
        os.utime(self.node_modules)

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
        print("Building css with less")

        style_less = pjoin(static, 'less', 'style.less')
        style_css = pjoin(static, 'css', 'style.min.css')
        sourcemap = style_css + '.map'

        args = [
            'npm',
            'run',
            'lessc',
            '--',
            '--clean-css',
            '--source-map-basepath={}'.format(static),
            '--source-map={}'.format(sourcemap),
            '--source-map-rootpath=../',
            style_less,
            style_css,
        ]
        try:
            check_call(args, cwd=here, shell=shell)
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

    Prevents setup.py install from performing setuptools' default easy_install,
    which it should never ever do.
    """

    def run(self):
        sys.exit(
            "Aborting implicit building of eggs. Use `pip install .` to install from source."
        )


setup_args['cmdclass'] = {
    'js': NPM,
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

# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------


def main():
    setup(**setup_args)


if __name__ == '__main__':
    main()
