#!/usr/bin/env python3
"""
invoke script for releasing jupyterhub

usage:

    invoke release 1.2.3 [--upload]

This does:

- clone into /tmp/jupyterhub-repo
- patches version.py with release version
- creates tag (push if uploading)
- makes a virtualenv with python3.4 (PYTHON_EXE env to override)
- builds an sdist (optionally uploads)
- patches version.py with post-release version (X.Y+1.Z.dev) (push if uploading)
- unpacks sdist to /tmp/jupyterhub-release
- builds bdist_wheel from sdist (optional upload)

"""
# derived from PyZMQ release/tasks.py (used under BSD)
# Copyright (c) Jupyter Developers
# Distributed under the terms of the Modified BSD License.
import glob
import os
import pipes
import shutil
from contextlib import contextmanager
from distutils.version import LooseVersion as V

from invoke import run as invoke_run
from invoke import task

pjoin = os.path.join
here = os.path.dirname(__file__)

repo = "git@github.com:jupyter/jupyterhub"
pkg = repo.rsplit('/', 1)[-1]

py_exe = os.environ.get('PYTHON_EXE', 'python3.4')

tmp = "/tmp"
env_root = os.path.join(tmp, 'envs')
repo_root = pjoin(tmp, '%s-repo' % pkg)
sdist_root = pjoin(tmp, '%s-release' % pkg)


def run(cmd, **kwargs):
    """wrapper around invoke.run that accepts a Popen list"""
    if isinstance(cmd, list):
        cmd = " ".join(pipes.quote(s) for s in cmd)
    kwargs.setdefault('echo', True)
    return invoke_run(cmd, **kwargs)


@contextmanager
def cd(path):
    """Context manager for temporary CWD"""
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


@task
def clone_repo(reset=False):
    """Clone the repo"""
    if os.path.exists(repo_root) and reset:
        shutil.rmtree(repo_root)
    if os.path.exists(repo_root):
        with cd(repo_root):
            run("git pull")
    else:
        run("git clone %s %s" % (repo, repo_root))


@task
def patch_version(vs, path=pjoin(here, '..')):
    """Patch zmq/sugar/version.py for the current release"""
    v = parse_vs(vs)
    version_py = pjoin(path, 'jupyterhub', 'version.py')
    print("patching %s with %s" % (version_py, vs))
    # read version.py, minus version parts
    with open(version_py) as f:
        pre_lines = []
        post_lines = []
        for line in f:
            pre_lines.append(line)
            if line.startswith("version_info"):
                break
        for line in f:
            if line.startswith(')'):
                post_lines.append(line)
                break
        for line in f:
            post_lines.append(line)

    # write new version.py
    with open(version_py, 'w') as f:
        for line in pre_lines:
            f.write(line)
        for part in v:
            f.write('    %r,\n' % part)
        for line in post_lines:
            f.write(line)

    # verify result
    ns = {}
    with open(version_py) as f:
        exec(f.read(), {}, ns)
    assert ns['__version__'] == vs, "%r != %r" % (ns['__version__'], vs)


@task
def tag(vs, push=False):
    """Make the tagged release commit"""
    patch_version(vs, repo_root)
    with cd(repo_root):
        run('git commit -a -m "release {}"'.format(vs))
        run('git tag -a -m "release {0}" {0}'.format(vs))
        if push:
            run('git push')
            run('git push --tags')


@task
def untag(vs, push=False):
    """Make the post-tag 'back to dev' commit"""
    v2 = parse_vs(vs)
    v2.append('dev')
    v2[1] += 1
    v2[2] = 0
    vs2 = unparse_vs(v2)
    patch_version(vs2, repo_root)
    with cd(repo_root):
        run('git commit -a -m "back to dev"')
        if push:
            run('git push')


def make_env(*packages):
    """Make a virtualenv

    Assumes `which python` has the `virtualenv` package
    """
    if not os.path.exists(env_root):
        os.makedirs(env_root)

    env = os.path.join(env_root, os.path.basename(py_exe))
    py = pjoin(env, 'bin', 'python')
    # new env
    if not os.path.exists(py):
        run(
            'python -m virtualenv {} -p {}'.format(
                pipes.quote(env), pipes.quote(py_exe)
            )
        )
        py = pjoin(env, 'bin', 'python')
        run([py, '-V'])
        install(py, 'pip', 'setuptools')
    if packages:
        install(py, *packages)
    return py


def build_sdist(py):
    """Build sdists

    Returns the path to the tarball
    """
    with cd(repo_root):
        cmd = [py, 'setup.py', 'sdist', '--formats=gztar']
        run(cmd)

    return glob.glob(pjoin(repo_root, 'dist', '*.tar.gz'))[0]


@task
def sdist(vs, upload=False):
    clone_repo()
    tag(vs, push=upload)
    py = make_env()
    tarball = build_sdist(py)
    if upload:
        with cd(repo_root):
            install(py, 'twine')
            run([py, '-m', 'twine', 'upload', 'dist/*'])

    untag(vs, push=upload)
    return untar(tarball)


def install(py, *packages):
    run([py, '-m', 'pip', 'install', '--upgrade'] + list(packages))


def parse_vs(vs):
    """version string to list"""
    return V(vs).version


def unparse_vs(tup):
    """version list to string"""
    return '.'.join(map(str, tup))


def untar(tarball):
    """extract sdist, returning path to unpacked package directory"""
    if os.path.exists(sdist_root):
        shutil.rmtree(sdist_root)
    os.makedirs(sdist_root)
    with cd(sdist_root):
        run(['tar', '-xzf', tarball])

    return glob.glob(pjoin(sdist_root, '*'))[0]


def bdist():
    """build a wheel, optionally uploading it"""
    py = make_env('wheel')
    run([py, 'setup.py', 'bdist_wheel'])


@task
def release(vs, upload=False):
    """Release the package"""
    # start from scrach with clone and envs
    clone_repo(reset=True)
    if os.path.exists(env_root):
        shutil.rmtree(env_root)

    path = sdist(vs, upload=upload)
    print("Working in %r" % path)
    with cd(path):
        bdist()
        if upload:
            py = make_env('twine')
            run([py, '-m', 'twine', 'upload', 'dist/*'])
