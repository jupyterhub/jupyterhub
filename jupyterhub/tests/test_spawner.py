"""Tests for process spawning"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import logging
import signal
import sys
import time

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
    kwargs.setdefault('INTERRUPT_TIMEOUT', 1)
    kwargs.setdefault('TERM_TIMEOUT', 1)
    kwargs.setdefault('KILL_TIMEOUT', 1)
    return LocalProcessSpawner(db=db, **kwargs)


def test_spawner(db, io_loop):
    spawner = new_spawner(db)
    io_loop.run_sync(spawner.start)
    assert spawner.user.server.ip == 'localhost'
    
    # wait for the process to get to the while True: loop
    time.sleep(1)
    
    status = io_loop.run_sync(spawner.poll)
    assert status is None
    io_loop.run_sync(spawner.stop)
    status = io_loop.run_sync(spawner.poll)
    assert status == 1

def test_single_user_spawner(db, io_loop):
    spawner = new_spawner(db, cmd=[sys.executable, '-m', 'jupyterhub.singleuser'])
    io_loop.run_sync(spawner.start)
    assert spawner.user.server.ip == 'localhost'
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

