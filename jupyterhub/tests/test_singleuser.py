"""Tests for jupyterhub.singleuser"""
import sys
from subprocess import check_output
from urllib.parse import urlparse

import jupyterhub
from ..utils import url_path_join
from .mocking import public_url
from .mocking import StubSingleUserSpawner
from .utils import async_requests
from .utils import AsyncSession


async def test_singleuser_auth(app):
    # use StubSingleUserSpawner to launch a single-user app in a thread
    app.spawner_class = StubSingleUserSpawner
    app.tornado_settings['spawner_class'] = StubSingleUserSpawner

    # login, start the server
    cookies = await app.login_user('nandy')
    user = app.users['nandy']
    if not user.running:
        await user.spawn()
    url = public_url(app, user)

    # no cookies, redirects to login page
    r = await async_requests.get(url)
    r.raise_for_status()
    assert '/hub/login' in r.url

    # with cookies, login successful
    r = await async_requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert (
        urlparse(r.url)
        .path.rstrip('/')
        .endswith(url_path_join('/user/nandy', user.spawner.default_url or "/tree"))
    )
    assert r.status_code == 200

    # logout
    r = await async_requests.get(url_path_join(url, 'logout'), cookies=cookies)
    assert len(r.cookies) == 0

    # accessing another user's server hits the oauth confirmation page
    cookies = await app.login_user('burgess')
    s = AsyncSession()
    s.cookies = cookies
    r = await s.get(url)
    assert urlparse(r.url).path.endswith('/oauth2/authorize')
    # submit the oauth form to complete authorization
    r = await s.post(r.url, data={'scopes': ['identify']}, headers={'Referer': r.url})
    assert (
        urlparse(r.url)
        .path.rstrip('/')
        .endswith(url_path_join('/user/nandy', user.spawner.default_url or "/tree"))
    )
    # user isn't authorized, should raise 403
    assert r.status_code == 403
    assert 'burgess' in r.text


async def test_disable_user_config(app):
    # use StubSingleUserSpawner to launch a single-user app in a thread
    app.spawner_class = StubSingleUserSpawner
    app.tornado_settings['spawner_class'] = StubSingleUserSpawner
    # login, start the server
    cookies = await app.login_user('nandy')
    user = app.users['nandy']
    # stop spawner, if running:
    if user.running:
        print("stopping")
        await user.stop()
    # start with new config:
    user.spawner.debug = True
    user.spawner.disable_user_config = True
    await user.spawn()
    await app.proxy.add_user(user)

    url = public_url(app, user)

    # with cookies, login successful
    r = await async_requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert r.url.rstrip('/').endswith(
        url_path_join('/user/nandy', user.spawner.default_url or "/tree")
    )
    assert r.status_code == 200


def test_help_output():
    out = check_output(
        [sys.executable, '-m', 'jupyterhub.singleuser', '--help-all']
    ).decode('utf8', 'replace')
    assert 'JupyterHub' in out


def test_version():
    out = check_output(
        [sys.executable, '-m', 'jupyterhub.singleuser', '--version']
    ).decode('utf8', 'replace')
    assert jupyterhub.__version__ in out
