#!/usr/bin/env python3
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
# -----------------------------------------------------------------------------
# Minimal Python version sanity check (from IPython)
# -----------------------------------------------------------------------------
import os
import shutil
import sys
from subprocess import check_call

from setuptools import Command, setup
from setuptools.command.bdist_egg import bdist_egg
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

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
    for d, dirs, filenames in os.walk(share_jupyterhub):
        rel_d = os.path.relpath(d, here)
        data_files.append((rel_d, [os.path.join(rel_d, f) for f in filenames]))
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
        'event-schemas/*/*.yaml',
        'singleuser/templates/*.html',
    ]
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
    python_requires=">=3.7",
    entry_points={
        'jupyterhub.authenticators': [
            'default = jupyterhub.auth:PAMAuthenticator',
            'pam = jupyterhub.auth:PAMAuthenticator',
            'dummy = jupyterhub.auth:DummyAuthenticator',
            'null = jupyterhub.auth:NullAuthenticator',
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
    extras_require={
        "test": [
            "beautifulsoup4[html5lib]",
            "coverage",
            # cryptography is an optional dependency for jupyterhub that we test
            # against by default
            "cryptography",
            "jsonschema",
            "jupyterlab>=3",
            "mock",
            # nbclassic provides the '/tree/' handler that we tests against in
            # the test test_nbclassic_control_panel.
            "nbclassic",
            "pytest>=3.3,<8",
            "pytest-asyncio>=0.17,<0.23",
            "pytest-cov",
            "requests-mock",
            "playwright",
            "pytest-rerunfailures",
            "virtualenv",
        ],
    },
)


def mtime(path):
    """shorthand for mtime"""
    return os.stat(path).st_mtime


def recursive_mtime(path):
    """Recursively get newest mtime of files"""
    if os.path.isfile(path):
        return mtime(path)
    current = 0
    for dirname, _, filenames in os.walk(path):
        if filenames:
            current = max(
                current, max(mtime(os.path.join(dirname, f)) for f in filenames)
            )
    return current


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
        assert not self.should_run(), 'NPM.run failed'


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
        for dirpath, dirnames, filenames in os.walk(static):
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
            f'--source-map-basepath={static}',
            f'--source-map={sourcemap}',
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
        assert not self.should_run(), 'CSS.run failed'


class JSX(BaseCommand):
    description = "build admin app"

    jsx_dir = pjoin(here, 'jsx')
    js_target = pjoin(static, 'js', 'admin-react.js')

    def should_run(self):
        if os.getenv('READTHEDOCS'):
            # yarn not available on RTD
            return False

        if not os.path.exists(self.js_target):
            return True

        js_target_mtime = mtime(self.js_target)
        jsx_mtime = recursive_mtime(self.jsx_dir)
        if js_target_mtime < jsx_mtime:
            return True
        return False

    def run(self):
        if not self.should_run():
            print("JSX admin app is up to date")
            return

        # jlpm is a version of yarn bundled with JupyterLab
        if shutil.which('yarn'):
            yarn = 'yarn'
        elif shutil.which('jlpm'):
            print("yarn not found, using jlpm")
            yarn = 'jlpm'
        else:
            raise Exception('JSX needs to be updated but yarn is not installed')

        print("Installing JSX admin app requirements")
        check_call(
            [yarn],
            cwd=self.jsx_dir,
            shell=shell,
        )

        print("Building JSX admin app")
        check_call(
            [yarn, 'build'],
            cwd=self.jsx_dir,
            shell=shell,
        )

        print("Copying JSX admin app to static/js")
        check_call(
            [yarn, 'place'],
            cwd=self.jsx_dir,
            shell=shell,
        )

        # update data-files in case this created new files
        self.distribution.data_files = get_data_files()
        assert not self.should_run(), 'JSX.run failed'


def js_css_first(cls, strict=True):
    class Command(cls):
        def run(self):
            try:
                self.run_command('js')
                self.run_command('css')
                self.run_command('jsx')
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
    'jsx': JSX,
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
        super().run()


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
