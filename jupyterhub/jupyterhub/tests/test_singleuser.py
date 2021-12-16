"""Tests for jupyterhub.singleuser"""
import os
import sys
from contextlib import contextmanager
from subprocess import CalledProcessError
from subprocess import check_output
from unittest import mock
from urllib.parse import urlparse

import pytest

import jupyterhub
from .. import orm
from ..utils import url_path_join
from .mocking import public_url
from .mocking import StubSingleUserSpawner
from .utils import async_requests
from .utils import AsyncSession


@contextmanager
def nullcontext():
    """Python 3.7+ contextlib.nullcontext, backport for 3.6"""
    yield


@pytest.mark.parametrize(
    "access_scopes, server_name, expect_success",
    [
        (["access:servers!group=$group"], "", True),
        (["access:servers!group=other-group"], "", False),
        (["access:servers"], "", True),
        (["access:servers"], "named", True),
        (["access:servers!user=$user"], "", True),
        (["access:servers!user=$user"], "named", True),
        (["access:servers!server=$server"], "", True),
        (["access:servers!server=$server"], "named-server", True),
        (["access:servers!server=$user/other"], "", False),
        (["access:servers!server=$user/other"], "some-name", False),
        (["access:servers!user=$other"], "", False),
        (["access:servers!user=$other"], "named", False),
        (["access:services"], "", False),
        (["self"], "named", False),
        ([], "", False),
    ],
)
async def test_singleuser_auth(
    app,
    create_user_with_scopes,
    access_scopes,
    server_name,
    expect_success,
):
    # use StubSingleUserSpawner to launch a single-user app in a thread
    app.spawner_class = StubSingleUserSpawner
    app.tornado_settings['spawner_class'] = StubSingleUserSpawner

    # login, start the server
    cookies = await app.login_user('nandy')
    user = app.users['nandy']

    group = orm.Group.find(app.db, name="visitors")
    if group is None:
        group = orm.Group(name="visitors")
        app.db.add(group)
        app.db.commit()
    if group not in user.groups:
        user.groups.append(group)
        app.db.commit()

    if server_name not in user.spawners or not user.spawners[server_name].active:
        await user.spawn(server_name)
        await app.proxy.add_user(user, server_name)
    spawner = user.spawners[server_name]
    url = url_path_join(public_url(app, user), server_name)

    # no cookies, redirects to login page
    r = await async_requests.get(url)
    r.raise_for_status()
    assert '/hub/login' in r.url

    # unauthenticated /api/ should 403, not redirect
    api_url = url_path_join(url, "api/status")
    r = await async_requests.get(api_url, allow_redirects=False)
    assert r.status_code == 403

    # with cookies, login successful
    r = await async_requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert (
        urlparse(r.url)
        .path.rstrip('/')
        .endswith(
            url_path_join(
                f'/user/{user.name}', spawner.name, spawner.default_url or "/tree"
            )
        )
    )
    assert r.status_code == 200

    # logout
    r = await async_requests.get(url_path_join(url, 'logout'), cookies=cookies)
    assert len(r.cookies) == 0

    # accessing another user's server hits the oauth confirmation page
    access_scopes = [s.replace("$user", user.name) for s in access_scopes]
    access_scopes = [
        s.replace("$server", f"{user.name}/{server_name}") for s in access_scopes
    ]
    access_scopes = [s.replace("$group", f"{group.name}") for s in access_scopes]
    other_user = create_user_with_scopes(*access_scopes, name="burgess")

    cookies = await app.login_user('burgess')
    s = AsyncSession()
    s.cookies = cookies
    r = await s.get(url)
    assert urlparse(r.url).path.endswith('/oauth2/authorize')
    if not expect_success:
        # user isn't authorized, should raise 403
        assert r.status_code == 403
        return
    r.raise_for_status()
    # submit the oauth form to complete authorization
    r = await s.post(r.url, data={'scopes': ['identify']}, headers={'Referer': r.url})
    final_url = urlparse(r.url).path.rstrip('/')
    final_path = url_path_join(
        '/user/', user.name, spawner.name, spawner.default_url or "/tree"
    )
    assert final_url.endswith(final_path)
    r.raise_for_status()

    # revoke user access, should result in 403
    other_user.roles = []
    app.db.commit()

    # reset session id to avoid cached response
    s.cookies.pop('jupyterhub-session-id')

    r = await s.get(r.url, allow_redirects=False)
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


@pytest.mark.parametrize(
    "JUPYTERHUB_SINGLEUSER_APP",
    [
        "",
        "notebook.notebookapp.NotebookApp",
        "jupyter_server.serverapp.ServerApp",
    ],
)
def test_singleuser_app_class(JUPYTERHUB_SINGLEUSER_APP):
    try:
        import jupyter_server  # noqa
    except ImportError:
        have_server = False
        expect_error = "jupyter_server" in JUPYTERHUB_SINGLEUSER_APP
    else:
        have_server = True
        expect_error = False

    if expect_error:
        ctx = pytest.raises(CalledProcessError)
    else:
        ctx = nullcontext()

    with mock.patch.dict(
        os.environ,
        {
            "JUPYTERHUB_SINGLEUSER_APP": JUPYTERHUB_SINGLEUSER_APP,
        },
    ):
        with ctx:
            out = check_output(
                [sys.executable, '-m', 'jupyterhub.singleuser', '--help-all']
            ).decode('utf8', 'replace')
    if expect_error:
        return
    # use help-all output to check inheritance
    if 'NotebookApp' in JUPYTERHUB_SINGLEUSER_APP or not have_server:
        assert '--NotebookApp.' in out
        assert '--ServerApp.' not in out
    else:
        assert '--ServerApp.' in out
        assert '--NotebookApp.' not in out
