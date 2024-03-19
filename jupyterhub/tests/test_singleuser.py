"""Tests for jupyterhub.singleuser"""

import os
import sys
from contextlib import nullcontext
from pprint import pprint
from subprocess import CalledProcessError, check_output
from unittest import mock
from urllib.parse import urlencode, urlparse

import pytest
from bs4 import BeautifulSoup

import jupyterhub

from .. import orm
from ..utils import url_path_join
from .mocking import public_url
from .utils import AsyncSession, async_requests, get_page

IS_JUPYVERSE = False  # backport compatibility


@pytest.fixture(autouse=True)
def _jupyverse(app):
    if IS_JUPYVERSE:
        app.config.Spawner.default_url = "/lab"


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
    full_spawn,
):
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

    s = AsyncSession()

    # no cookies, redirects to login page
    r = await s.get(url)
    r.raise_for_status()
    assert '/hub/login' in r.url

    # unauthenticated /api/ should 403, not redirect
    api_url = url_path_join(url, "api/status")
    r = await s.get(api_url, allow_redirects=False)
    assert r.status_code == 403

    # with cookies, login successful
    r = await s.get(url, cookies=cookies)
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
    r = await s.get(url_path_join(url, 'logout'))
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
    r = await s.post(r.url, data={'scopes': ['identify'], '_xsrf': s.cookies['_xsrf']})
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
    await user.stop(server_name)


async def test_disable_user_config(request, app, tmpdir, full_spawn):
    # login, start the server
    cookies = await app.login_user('nandy')
    s = AsyncSession()
    s.cookies = cookies
    user = app.users['nandy']
    # stop spawner, if running:
    if user.running:
        print("stopping")
        await user.stop()
    # start with new config:
    user.spawner.debug = True
    user.spawner.disable_user_config = True
    home_dir = tmpdir.join("home")
    home_dir.mkdir()
    # home_dir is defined on SimpleSpawner
    user.spawner.home_dir = home = str(home_dir)
    jupyter_config_dir = home_dir.join(".jupyter")
    jupyter_config_dir.mkdir()
    # verify config paths
    with jupyter_config_dir.join("jupyter_server_config.py").open("w") as f:
        f.write("c.TestSingleUser.jupyter_config_py = True")

    await user.spawn()
    await app.proxy.add_user(user)

    url = public_url(app, user)

    # with cookies, login successful
    r = await s.get(url)
    r.raise_for_status()
    assert r.url.rstrip('/').endswith(
        url_path_join('/user/nandy', user.spawner.default_url or "/tree")
    )
    assert r.status_code == 200

    r = await s.get(url_path_join(public_url(app, user), 'jupyterhub-test-info'))
    r.raise_for_status()
    info = r.json()
    pprint(info)
    assert info['disable_user_config']
    server_config = info['config']
    settings = info['settings']
    assert 'TestSingleUser' not in server_config
    # check config paths
    norm_home = os.path.realpath(os.path.abspath(home))

    def assert_not_in_home(path, name):
        path = os.path.realpath(os.path.abspath(path))
        assert not path.startswith(
            norm_home + os.path.sep
        ), f"{name}: {path} is in home {norm_home}"

    for path in info['config_file_paths']:
        assert_not_in_home(path, 'config_file_paths')

    # check every path setting for lookup in $HOME
    # is this too much?
    for key, setting in settings.items():
        if 'path' in key and isinstance(setting, list):
            for path in setting:
                assert_not_in_home(path, key)


@pytest.mark.parametrize("extension", [True, False])
@pytest.mark.parametrize("notebook_dir", ["", "~", "~/sub", "ABS"])
async def test_notebook_dir(
    request, app, tmpdir, user, full_spawn, extension, notebook_dir
):
    if extension:
        try:
            import jupyter_server  # noqa
        except ImportError:
            pytest.skip("needs jupyter-server 2")
        else:
            if jupyter_server.version_info < (2,):
                pytest.skip("needs jupyter-server 2")

    token = user.new_api_token(scopes=["access:servers!user"])
    headers = {"Authorization": f"Bearer {token}"}

    spawner = user.spawner
    if extension:
        user.spawner.environment["JUPYTERHUB_SINGLEUSER_EXTENSION"] = "1"
    else:
        user.spawner.environment["JUPYTERHUB_SINGLEUSER_EXTENSION"] = "0"

    home_dir = tmpdir.join("home").mkdir()
    sub_dir = home_dir.join("sub").mkdir()
    with sub_dir.join("subfile.txt").open("w") as f:
        f.write("txt\n")
    abs_dir = tmpdir.join("abs").mkdir()
    with abs_dir.join("absfile.txt").open("w") as f:
        f.write("absfile\n")

    if notebook_dir:
        expected_root_dir = notebook_dir.replace("ABS", str(abs_dir)).replace(
            "~", str(home_dir)
        )
    else:
        expected_root_dir = str(home_dir)

    spawner.notebook_dir = notebook_dir.replace("ABS", str(abs_dir))

    # home_dir is defined on SimpleSpawner
    user.spawner.home_dir = home = str(home_dir)
    spawner.environment["HOME"] = home
    await user.spawn()
    await app.proxy.add_user(user)
    url = public_url(app, user)
    r = await async_requests.get(
        url_path_join(public_url(app, user), 'jupyterhub-test-info'), headers=headers
    )
    r.raise_for_status()
    info = r.json()
    pprint(info)

    assert info["root_dir"] == expected_root_dir
    # secondary check: make sure it has the intended effect on root_dir
    r = await async_requests.get(
        url_path_join(public_url(app, user), 'api/contents/'), headers=headers
    )
    r.raise_for_status()
    root_contents = sorted(item['name'] for item in r.json()['content'])

    # check contents
    if not notebook_dir or notebook_dir == "~":
        # use any to avoid counting possible automatically created files in $HOME
        assert 'sub' in root_contents
    elif notebook_dir == "ABS":
        assert 'absfile.txt' in root_contents
    elif notebook_dir == "~/sub":
        assert 'subfile.txt' in root_contents
    else:
        raise ValueError(f"No contents check for {notebook_dir}")


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
    else:
        have_server = True
    try:
        import notebook.notebookapp  # noqa
    except ImportError:
        have_notebook = False
    else:
        have_notebook = True

    if JUPYTERHUB_SINGLEUSER_APP.startswith("notebook."):
        expect_error = (
            os.environ.get("JUPYTERHUB_SINGLEUSER_EXTENSION") == "1"
            or not have_notebook
        )
    elif JUPYTERHUB_SINGLEUSER_APP.startswith("jupyter_server."):
        expect_error = not have_server
    else:
        # not specified, will try both
        expect_error = not (have_server or have_notebook)

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


async def test_nbclassic_control_panel(app, user, full_spawn):
    # login, start the server
    await user.spawn()
    cookies = await app.login_user(user.name)
    next_url = url_path_join(user.url, "tree/")
    url = '/?' + urlencode({'next': next_url})
    r = await get_page(url, app, cookies=cookies)
    r.raise_for_status()
    assert urlparse(r.url).path == urlparse(next_url).path
    page = BeautifulSoup(r.text, "html.parser")
    link = page.find("a", id="jupyterhub-control-panel-link")
    assert link, f"Missing jupyterhub-control-panel-link in {page}"
    if app.subdomain_host:
        prefix = public_url(app)
    else:
        prefix = app.base_url
    assert link["href"] == url_path_join(prefix, "hub/home")


@pytest.mark.skipif(
    IS_JUPYVERSE, reason="jupyverse doesn't implement token authentication"
)
@pytest.mark.parametrize("accept_token_in_url", ["1", "0", ""])
async def test_token_url_cookie(app, user, full_spawn, accept_token_in_url):
    if accept_token_in_url:
        user.spawner.environment["JUPYTERHUB_ALLOW_TOKEN_IN_URL"] = accept_token_in_url
    should_accept = accept_token_in_url != "0"

    await user.spawn()
    await app.proxy.add_user(user)

    token = user.new_api_token(scopes=["access:servers!user"])
    url = url_path_join(public_url(app, user), user.spawner.default_url or "/tree/")

    # first request: auth with token in URL
    s = AsyncSession()
    r = await s.get(url + f"?token={token}", allow_redirects=False)
    print(r.url, r.status_code)
    if not should_accept:
        assert r.status_code == 302
        return

    assert r.status_code == 200
    assert s.cookies
    # second request, use cookies set by first response,
    # no token in URL
    r = await s.get(url, allow_redirects=False)
    assert r.status_code == 200
    await user.stop()


async def test_api_403_no_cookie(app, user, full_spawn):
    """unused oauth cookies don't get set for failed requests to API handlers"""
    await user.spawn()
    await app.proxy.add_user(user)
    url = url_path_join(public_url(app, user), "/api/contents/")
    s = AsyncSession()
    r = await s.get(url, allow_redirects=False)
    # 403, not redirect
    assert r.status_code == 403
    # no state cookie set
    assert not r.cookies
    await user.stop()
