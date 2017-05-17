"""Tests for jupyterhub.singleuser"""

from subprocess import check_output
import sys

import requests

import jupyterhub
from .mocking import StubSingleUserSpawner, public_url
from ..utils import url_path_join


def test_singleuser_auth(app, io_loop):
    """Checks login authorization with and without cookies and logout"""
    # use StubSingleUserSpawner to launch a single-user app in a thread
    app.spawner_class = StubSingleUserSpawner
    app.tornado_settings['spawner_class'] = StubSingleUserSpawner
    
    # login, start the server
    cookies = app.login_user('nandy')
    user = app.users['nandy']
    if not user.running:
        io_loop.run_sync(user.spawn)
    url = public_url(app, user)
    
    # check if no cookies, redirects to login page
    r = requests.get(url)
    r.raise_for_status()
    assert '/hub/login' in r.url
    
    # check with cookies, login successful
    r = requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert r.url.rstrip('/').endswith('/user/nandy/tree')
    assert r.status_code == 200
    
    # check that logout request removes user's cookie
    r = requests.get(url_path_join(url, 'logout'), cookies=cookies)
    assert len(r.cookies) == 0


def test_disable_user_config(app, io_loop):
    """Test updating a user's config spawns a new single user server

    - Using a mocked StubSingleUserSpawner launch a single user app in a thread
    - Login 'nandy' and grab associated cookie and user from db
    - If there is an existing single user server running for 'nandy', stop it
    - Start a new single user server with 'nandy's' updated configuration
    - Get the public url for nandy's new single user server
    - Check that nandy's new single user server is working and accessible
    """
    # use StubSingleUserSpawner to launch a single-user app in a thread
    app.spawner_class = StubSingleUserSpawner
    app.tornado_settings['spawner_class'] = StubSingleUserSpawner

    # login, start the server
    cookies = app.login_user('nandy')
    user = app.users['nandy']
    if user.running:
        print("stopping")
        io_loop.run_sync(user.stop)

    # start a single user server with new config
    user.spawner.debug = True  # Enable debug log
    # use config from db not any config that my be in user's $HOME directory
    user.spawner.disable_user_config = True
    io_loop.run_sync(user.spawn)
    io_loop.run_sync(lambda: app.proxy.add_user(user))
    
    url = public_url(app, user)
    
    # with cookies, login successful
    r = requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert r.url.rstrip('/').endswith('/user/nandy/tree')
    assert r.status_code == 200


def test_help_output():
    """Test command line option --help-all"""
    out = check_output([sys.executable, '-m', 'jupyterhub.singleuser', '--help-all']).decode('utf8', 'replace')
    assert 'JupyterHub' in out


def test_version():
    """Test command line option --version"""
    out = check_output([sys.executable, '-m', 'jupyterhub.singleuser', '--version']).decode('utf8', 'replace')
    assert jupyterhub.__version__ in out
