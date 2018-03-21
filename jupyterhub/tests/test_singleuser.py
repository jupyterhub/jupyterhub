"""Tests for jupyterhub.singleuser"""

from subprocess import check_output
import sys
from urllib.parse import urlparse

import pytest

import jupyterhub
from .mocking import StubSingleUserSpawner, public_url
from ..utils import url_path_join

from .utils import async_requests


@pytest.mark.gen_test
def test_singleuser_auth(app):
    # use StubSingleUserSpawner to launch a single-user app in a thread
    app.spawner_class = StubSingleUserSpawner
    app.tornado_settings['spawner_class'] = StubSingleUserSpawner

    # login, start the server
    cookies = yield app.login_user('nandy')
    user = app.users['nandy']
    if not user.running:
        yield user.spawn()
    url = public_url(app, user)

    # no cookies, redirects to login page
    r = yield async_requests.get(url)
    r.raise_for_status()
    assert '/hub/login' in r.url

    # with cookies, login successful
    r = yield async_requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert urlparse(r.url).path.rstrip('/').endswith('/user/nandy/tree')
    assert r.status_code == 200

    # logout
    r = yield async_requests.get(url_path_join(url, 'logout'), cookies=cookies)
    assert len(r.cookies) == 0

    # another user accessing should get 403, not redirect to login
    cookies = yield app.login_user('burgess')
    r = yield async_requests.get(url, cookies=cookies)
    assert r.status_code == 403
    assert 'burgess' in r.text


@pytest.mark.gen_test
def test_disable_user_config(app):
    # use StubSingleUserSpawner to launch a single-user app in a thread
    app.spawner_class = StubSingleUserSpawner
    app.tornado_settings['spawner_class'] = StubSingleUserSpawner
    # login, start the server
    cookies = yield app.login_user('nandy')
    user = app.users['nandy']
    # stop spawner, if running:
    if user.running:
        print("stopping")
        yield user.stop()
    # start with new config:
    user.spawner.debug = True
    user.spawner.disable_user_config = True
    yield user.spawn()
    yield app.proxy.add_user(user)
    
    url = public_url(app, user)
    
    # with cookies, login successful
    r = yield async_requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert r.url.rstrip('/').endswith('/user/nandy/tree')
    assert r.status_code == 200


def test_help_output():
    out = check_output([sys.executable, '-m', 'jupyterhub.singleuser', '--help-all']).decode('utf8', 'replace')
    assert 'JupyterHub' in out

def test_version():
    out = check_output([sys.executable, '-m', 'jupyterhub.singleuser', '--version']).decode('utf8', 'replace')
    assert jupyterhub.__version__ in out

