"""Tests for process spawning"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import logging
import os
import signal
from subprocess import Popen
import sys
import tempfile
import time
from unittest import mock
from urllib.parse import urlparse

import pytest
from tornado import gen

from ..objects import Hub, Server
from .. import orm
from .. import spawner as spawnermod
from ..spawner import LocalProcessSpawner, Spawner
from ..user import User
from ..utils import new_token, url_path_join
from .mocking import public_url
from .test_api import add_user
from .utils import async_requests

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
    user = kwargs.setdefault('user', User(db.query(orm.User).first(), {}))
    kwargs.setdefault('cmd', [sys.executable, '-c', _echo_sleep])
    kwargs.setdefault('hub', Hub())
    kwargs.setdefault('notebook_dir', os.getcwd())
    kwargs.setdefault('default_url', '/user/{username}/lab')
    kwargs.setdefault('oauth_client_id', 'mock-client-id')
    kwargs.setdefault('interrupt_timeout', 1)
    kwargs.setdefault('term_timeout', 1)
    kwargs.setdefault('kill_timeout', 1)
    kwargs.setdefault('poll_interval', 1)
    return user._new_spawner('', spawner_class=LocalProcessSpawner, **kwargs)


@pytest.mark.gen_test
def test_spawner(db, request):
    spawner = new_spawner(db)
    ip, port = yield spawner.start()
    assert ip == '127.0.0.1'
    assert isinstance(port, int)
    assert port > 0
    db.commit()

    # wait for the process to get to the while True: loop
    time.sleep(1)

    status = yield spawner.poll()
    assert status is None
    yield spawner.stop()
    status = yield spawner.poll()
    assert status == 1


@gen.coroutine
def wait_for_spawner(spawner, timeout=10):
    """Wait for an http server to show up
    
    polling at shorter intervals for early termination
    """
    deadline = time.monotonic() + timeout
    def wait():
        return spawner.server.wait_up(timeout=1, http=True)
    while time.monotonic() < deadline:
        status = yield spawner.poll()
        assert status is None
        try:
            yield wait()
        except TimeoutError:
            continue
        else:
            break
    yield wait()


@pytest.mark.gen_test
def test_single_user_spawner(app, request):
    user = next(iter(app.users.values()), None)
    spawner = user.spawner
    spawner.cmd = ['jupyterhub-singleuser']
    yield user.spawn()
    assert spawner.server.ip == '127.0.0.1'
    assert spawner.server.port > 0
    yield wait_for_spawner(spawner)
    status = yield spawner.poll()
    assert status is None
    yield spawner.stop()
    status = yield spawner.poll()
    assert status == 0


@pytest.mark.gen_test
def test_stop_spawner_sigint_fails(db):
    spawner = new_spawner(db, cmd=[sys.executable, '-c', _uninterruptible])
    yield spawner.start()

    # wait for the process to get to the while True: loop
    yield gen.sleep(1)

    status = yield spawner.poll()
    assert status is None
    
    yield spawner.stop()
    status = yield spawner.poll()
    assert status == -signal.SIGTERM


@pytest.mark.gen_test
def test_stop_spawner_stop_now(db):
    spawner = new_spawner(db)
    yield spawner.start()

    # wait for the process to get to the while True: loop
    yield gen.sleep(1)

    status = yield spawner.poll()
    assert status is None
    
    yield spawner.stop(now=True)
    status = yield spawner.poll()
    assert status == -signal.SIGTERM


@pytest.mark.gen_test
def test_spawner_poll(db):
    first_spawner = new_spawner(db)
    user = first_spawner.user
    yield first_spawner.start()
    proc = first_spawner.proc
    status = yield first_spawner.poll()
    assert status is None
    if user.state is None:
        user.state = {}
    first_spawner.orm_spawner.state = first_spawner.get_state()
    assert 'pid' in first_spawner.orm_spawner.state
    
    # create a new Spawner, loading from state of previous
    spawner = new_spawner(db, user=first_spawner.user)
    spawner.start_polling()
    
    # wait for the process to get to the while True: loop
    yield gen.sleep(1)
    status = yield spawner.poll()
    assert status is None
    
    # kill the process
    proc.terminate()
    for i in range(10):
        if proc.poll() is None:
            yield gen.sleep(1)
        else:
            break
    assert proc.poll() is not None

    yield gen.sleep(2)
    status = yield spawner.poll()
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


@pytest.mark.gen_test
def test_popen_kwargs(db):
    mock_proc = mock.Mock(spec=Popen)
    def mock_popen(*args, **kwargs):
        mock_proc.args = args
        mock_proc.kwargs = kwargs
        mock_proc.pid = 5
        return mock_proc

    s = new_spawner(db, popen_kwargs={'shell': True}, cmd='jupyterhub-singleuser')
    with mock.patch.object(spawnermod, 'Popen', mock_popen):
        yield s.start()

    assert mock_proc.kwargs['shell'] == True
    assert mock_proc.args[0][:1] == (['jupyterhub-singleuser'])


@pytest.mark.gen_test
def test_shell_cmd(db, tmpdir, request):
    f = tmpdir.join('bashrc')
    f.write('export TESTVAR=foo\n')
    s = new_spawner(db,
        cmd=[sys.executable, '-m', 'jupyterhub.tests.mocksu'],
        shell_cmd=['bash', '--rcfile', str(f), '-i', '-c'],
    )
    server = orm.Server()
    db.add(server)
    db.commit()
    s.server = Server.from_orm(server)
    db.commit()
    (ip, port) = yield s.start()
    request.addfinalizer(s.stop)
    s.server.ip = ip
    s.server.port = port
    db.commit()
    yield wait_for_spawner(s)
    r = yield async_requests.get('http://%s:%i/env' % (ip, port))
    r.raise_for_status()
    env = r.json()
    assert env['TESTVAR'] == 'foo'


def test_inherit_overwrite():
    """On 3.6+ we check things are overwritten at import time
    """
    if sys.version_info >= (3,6):
        with pytest.raises(NotImplementedError):
            class S(Spawner):
                pass


def test_inherit_ok():
    class S(Spawner):
        def start():
            pass

        def stop():
            pass

        def poll():
            pass


@pytest.mark.gen_test
def test_spawner_reuse_api_token(db, app):
    # setup: user with no tokens, whose spawner has set the .will_resume flag
    user = add_user(app.db, app, name='snoopy')
    spawner = user.spawner
    assert user.api_tokens == []
    # will_resume triggers reuse of tokens
    spawner.will_resume = True
    # first start: gets a new API token
    yield user.spawn()
    api_token = spawner.api_token
    found = orm.APIToken.find(app.db, api_token)
    assert found
    assert found.user.name == user.name
    assert user.api_tokens == [found]
    yield user.stop()
    # stop now deletes unused spawners.
    # put back the mock spawner!
    user.spawners[''] = spawner
    # second start: should reuse the token
    yield user.spawn()
    # verify re-use of API token
    assert spawner.api_token == api_token
    # verify that a new token was not created
    assert user.api_tokens == [found]


@pytest.mark.gen_test
def test_spawner_insert_api_token(app):
    """Token provided by spawner is not in the db

    Insert token into db as a user-provided token.
    """
    # setup: new user, double check that they don't have any tokens registered
    user = add_user(app.db, app, name='tonkee')
    spawner = user.spawner
    assert user.api_tokens == []

    # setup: spawner's going to use a token that's not in the db
    api_token = new_token()
    assert not orm.APIToken.find(app.db, api_token)
    user.spawner.use_this_api_token = api_token
    # The spawner's provided API token would already be in the db
    # unless there is a bug somewhere else (in the Spawner),
    # but handle it anyway.
    yield user.spawn()
    assert spawner.api_token == api_token
    found = orm.APIToken.find(app.db, api_token)
    assert found
    assert found.user.name == user.name
    assert user.api_tokens == [found]
    yield user.stop()


@pytest.mark.gen_test
def test_spawner_bad_api_token(app):
    """Tokens are revoked when a Spawner gets another user's token"""
    # we need two users for this one
    user = add_user(app.db, app, name='antimone')
    spawner = user.spawner
    other_user = add_user(app.db, app, name='alabaster')
    assert user.api_tokens == []
    assert other_user.api_tokens == []

    # create a token owned by alabaster that antimone's going to try to use
    other_token = other_user.new_api_token()
    spawner.use_this_api_token = other_token
    assert len(other_user.api_tokens) == 1

    # starting a user's server with another user's token
    # should revoke it
    with pytest.raises(ValueError):
        yield user.spawn()
    assert orm.APIToken.find(app.db, other_token) is None
    assert other_user.api_tokens == []


@pytest.mark.gen_test
def test_spawner_delete_server(app):
    """Test deleting spawner.server

    This can occur during app startup if their server has been deleted.
    """
    db = app.db
    user = add_user(app.db, app, name='gaston')
    spawner = user.spawner
    orm_server = orm.Server()
    db.add(orm_server)
    db.commit()
    server_id = orm_server.id
    spawner.server = Server.from_orm(orm_server)
    db.commit()

    assert spawner.server is not None
    assert spawner.orm_spawner.server is not None

    # setting server = None triggers delete
    spawner.server = None
    db.commit()
    assert spawner.orm_spawner.server is None
    # verify that the server was actually deleted from the db
    assert db.query(orm.Server).filter(orm.Server.id == server_id).first() is None
    # verify that both ORM and top-level references are None
    assert spawner.orm_spawner.server is None
    assert spawner.server is None


@pytest.mark.parametrize(
    "name",
    [
        "has@x",
        "has~x",
        "has%x",
        "has%40x",
    ]
)
@pytest.mark.gen_test
def test_spawner_routing(app, name):
    """Test routing of names with special characters"""
    db = app.db
    with mock.patch.dict(app.config.LocalProcessSpawner, {'cmd': [sys.executable, '-m', 'jupyterhub.tests.mocksu']}):
        user = add_user(app.db, app, name=name)
        yield user.spawn()
        yield wait_for_spawner(user.spawner)
        yield app.proxy.add_user(user)
    url = url_path_join(public_url(app, user), "test/url")
    r = yield async_requests.get(url, allow_redirects=False)
    r.raise_for_status()
    assert r.url == url
    assert r.text == urlparse(url).path
