"""Tests for process spawning"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import logging
import os
import signal
import sys
import tempfile
import time
from unittest import mock

from tornado import gen

from .. import spawner as spawnermod
from ..spawner import LocalProcessSpawner
from .. import orm

_echo_sleep = """
import sys, time
print(sys.argv)
time.sleep(30)
"""

_uninterruptible = """
import time
while True:
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print("interrupted")
"""


def setup():
    logging.basicConfig(level=logging.DEBUG)


def new_spawner(db, **kwargs):
    kwargs.setdefault('cmd', [sys.executable, '-c', _echo_sleep])
    kwargs.setdefault('user', db.query(orm.User).first())
    kwargs.setdefault('hub', db.query(orm.Hub).first())
    kwargs.setdefault('notebook_dir', os.getcwd())
    kwargs.setdefault('default_url', '/user/{username}/lab')
    kwargs.setdefault('INTERRUPT_TIMEOUT', 1)
    kwargs.setdefault('TERM_TIMEOUT', 1)
    kwargs.setdefault('KILL_TIMEOUT', 1)
    kwargs.setdefault('poll_interval', 1)
    return LocalProcessSpawner(db=db, **kwargs)


def test_spawner(db, io_loop):
    spawner = new_spawner(db)
    ip, port = io_loop.run_sync(spawner.start)
    assert ip == '127.0.0.1'
    assert isinstance(port, int)
    assert port > 0
    spawner.user.server.ip = ip
    spawner.user.server.port = port
    db.commit()
    

    # wait for the process to get to the while True: loop
    time.sleep(1)

    status = io_loop.run_sync(spawner.poll)
    assert status is None
    io_loop.run_sync(spawner.stop)
    status = io_loop.run_sync(spawner.poll)
    assert status == 1

def test_single_user_spawner(db, io_loop):
    spawner = new_spawner(db, cmd=['jupyterhub-singleuser'])
    spawner.api_token = 'secret'
    ip, port = io_loop.run_sync(spawner.start)
    assert ip == '127.0.0.1'
    assert isinstance(port, int)
    assert port > 0
    spawner.user.server.ip = ip
    spawner.user.server.port = port
    db.commit()
    # wait for http server to come up,
    # checking for early termination every 1s
    def wait():
        return spawner.user.server.wait_up(timeout=1, http=True)
    for i in range(30):
        status = io_loop.run_sync(spawner.poll)
        assert status is None
        try:
            io_loop.run_sync(wait)
        except TimeoutError:
            continue
        else:
            break
    io_loop.run_sync(wait)
    status = io_loop.run_sync(spawner.poll)
    assert status == None
    io_loop.run_sync(spawner.stop)
    status = io_loop.run_sync(spawner.poll)
    assert status == 0


def test_stop_spawner_sigint_fails(db, io_loop):
    spawner = new_spawner(db, cmd=[sys.executable, '-c', _uninterruptible])
    io_loop.run_sync(spawner.start)
    
    # wait for the process to get to the while True: loop
    time.sleep(1)
    
    status = io_loop.run_sync(spawner.poll)
    assert status is None
    
    io_loop.run_sync(spawner.stop)
    status = io_loop.run_sync(spawner.poll)
    assert status == -signal.SIGTERM


def test_stop_spawner_stop_now(db, io_loop):
    spawner = new_spawner(db)
    io_loop.run_sync(spawner.start)
    
    # wait for the process to get to the while True: loop
    time.sleep(1)
    
    status = io_loop.run_sync(spawner.poll)
    assert status is None
    
    io_loop.run_sync(lambda : spawner.stop(now=True))
    status = io_loop.run_sync(spawner.poll)
    assert status == -signal.SIGTERM


def test_spawner_poll(db, io_loop):
    first_spawner = new_spawner(db)
    user = first_spawner.user
    io_loop.run_sync(first_spawner.start)
    proc = first_spawner.proc
    status = io_loop.run_sync(first_spawner.poll)
    assert status is None
    user.state = first_spawner.get_state()
    assert 'pid' in user.state
    
    # create a new Spawner, loading from state of previous
    spawner = new_spawner(db, user=first_spawner.user)
    spawner.start_polling()
    
    # wait for the process to get to the while True: loop
    io_loop.run_sync(lambda : gen.sleep(1))
    status = io_loop.run_sync(spawner.poll)
    assert status is None
    
    # kill the process
    proc.terminate()
    for i in range(10):
        if proc.poll() is None:
            time.sleep(1)
        else:
            break
    assert proc.poll() is not None

    io_loop.run_sync(lambda : gen.sleep(2))
    status = io_loop.run_sync(spawner.poll)
    assert status is not None


def test_setcwd():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        td = os.path.realpath(os.path.abspath(td))
        spawnermod._try_setcwd(td)
        assert os.path.samefile(os.getcwd(), td)
    os.chdir(cwd)
    chdir = os.chdir
    temp_root = os.path.realpath(os.path.abspath(tempfile.gettempdir()))
    def raiser(path):
        path = os.path.realpath(os.path.abspath(path))
        if not path.startswith(temp_root):
            raise OSError(path)
        chdir(path)
    with mock.patch('os.chdir', raiser):
        spawnermod._try_setcwd(cwd)
        assert os.getcwd().startswith(temp_root)
    os.chdir(cwd)


def test_string_formatting(db):
    s = new_spawner(db, notebook_dir='user/%U/', default_url='/base/{username}')
    name = s.user.name
    assert s.notebook_dir == 'user/{username}/'
    assert s.default_url == '/base/{username}'
    assert s.format_string(s.notebook_dir) == 'user/%s/' % name
    assert s.format_string(s.default_url) == '/base/%s' % name

