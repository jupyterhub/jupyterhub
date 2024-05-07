#!/usr/bin/env python3
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import shutil
import sys
from subprocess import check_call

from setuptools import Command, setup
from setuptools.command.bdist_egg import bdist_egg
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
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

# Build basic package data, etc.


def get_data_files():
    """Get data files in share/jupyter"""

    data_files = []
    for d, dirs, filenames in os.walk(share_jupyterhub):
        rel_d = os.path.relpath(d, here)
        data_files.append((rel_d, [os.path.join(rel_d, f) for f in filenames]))
    return data_files


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
    description = "compile CSS"

    def should_run(self):
        """Does CSS need to run?"""
        css_targets = [pjoin(static, 'css', 'style.min.css')]
        css_maps = [t + '.map' for t in css_targets]
        targets = css_targets + css_maps
        earliest_target_mtime = float('inf')
        earliest_target_name = ''
        for t in targets:
            if not os.path.exists(t):
                print(f"Need to build css target: {t}")
                return True
            target_mtime = mtime(t)
            if target_mtime < earliest_target_mtime:
                earliest_target_name = t
                earliest_target_mtime = target_mtime

        # check if any .scss files are newer than the generated targets
        for dirpath, dirnames, filenames in os.walk(static):
            for f in filenames:
                if f.endswith('.scss'):
                    path = pjoin(static, dirpath, f)
                    timestamp = mtime(path)
                    if timestamp > earliest_target_mtime:
                        print(
                            f"mtime for {path} > {earliest_target_name}, needs update"
                        )
                        return True

        return False

    def run(self):
        if not self.should_run():
            print("CSS up-to-date")
            return

        self.run_command('js')
        print("Building css")

        args = ['npm', 'run', 'css']
        try:
            check_call(args, cwd=here, shell=shell)
        except OSError as e:
            print(f"Failed to build css: {e}", file=sys.stderr)
            print("You can install js dependencies with `npm install`", file=sys.stderr)
            raise
        # update data-files in case this created new files
        self.distribution.data_files = get_data_files()
        assert not self.should_run(), 'CSS.run did not produce up-to-date output'


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

        if not shutil.which('npm'):
            raise Exception('JSX needs to be updated but npm is not installed')

        print("Installing JSX admin app requirements")
        check_call(
            ['npm', 'install', '--progress=false', '--unsafe-perm'],
            cwd=self.jsx_dir,
            shell=shell,
        )

        print("Building JSX admin app")
        check_call(
            ["npm", "run", "build"],
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


class develop_js_css(develop):
    def run(self):
        if not self.uninstall:
            self.distribution.run_command('js')
            self.distribution.run_command('css')
        super().run()


cmdclass = {
    'js': NPM,
    'css': CSS,
    'jsx': JSX,
    'build_py': js_css_first(build_py, strict=is_repo),
    'sdist': js_css_first(sdist, strict=True),
    'bdist_egg': bdist_egg if 'bdist_egg' in sys.argv else bdist_egg_disabled,
    'develop': develop_js_css,
}

# run setup


def main():
    setup(
        cmdclass=cmdclass,
        data_files=get_data_files(),
    )


if __name__ == '__main__':
    main()
