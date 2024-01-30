"""Tests for named servers"""

import asyncio
import json
import time
from unittest import mock
from urllib.parse import unquote, urlencode, urlparse

import pytest
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError
from tornado.httputil import url_concat

from .. import orm
from ..utils import url_escape_path, url_path_join
from .mocking import FormSpawner
from .test_api import TIMESTAMP, add_user, api_request, fill_user, normalize_user
from .utils import async_requests, get_page, public_host, public_url


@pytest.fixture
def named_servers(app):
    with mock.patch.dict(
        app.tornado_settings,
        {'allow_named_servers': True, 'named_server_limit_per_user': 2},
    ):
        yield


@pytest.fixture
def named_servers_with_callable_limit(app):
    def named_server_limit_per_user_fn(handler):
        """Limit number of named servers to `2` for non-admin users. No limit for admin users."""
        user = handler.current_user
        if user and user.admin:
            return 0
        return 2

    with mock.patch.dict(
        app.tornado_settings,
        {
            'allow_named_servers': True,
            'named_server_limit_per_user': named_server_limit_per_user_fn,
        },
    ):
        yield


@pytest.fixture
def default_server_name(app, named_servers):
    """configure app to use a default server name"""
    server_name = 'myserver'
    try:
        app.default_server_name = server_name
        yield server_name
    finally:
        app.default_server_name = ''


async def test_default_server(app, named_servers):
    """Test the default /users/:user/server handler when named servers are enabled"""
    username = 'rosie'
    user = add_user(app.db, app, name=username)
    r = await api_request(app, 'users', username, 'server', method='post')
    assert r.status_code == 201
    assert r.text == ''

    r = await api_request(app, 'users', username)
    r.raise_for_status()

    user_model = normalize_user(r.json())
    assert user_model == fill_user(
        {
            'name': username,
            'roles': ['user'],
            'auth_state': None,
            'server': user.url,
            'servers': {
                '': {
                    'name': '',
                    'started': TIMESTAMP,
                    'last_activity': TIMESTAMP,
                    'url': user.url,
                    'pending': None,
                    'ready': True,
                    'stopped': False,
                    'progress_url': 'PREFIX/hub/api/users/{}/server/progress'.format(
                        username
                    ),
                    'state': {'pid': 0},
                    'user_options': {},
                }
            },
        }
    )

    # now stop the server
    r = await api_request(app, 'users', username, 'server', method='delete')
    assert r.status_code == 204
    assert r.text == ''

    r = await api_request(app, 'users', username)
    r.raise_for_status()

    user_model = normalize_user(r.json())
    assert user_model == fill_user(
        {'name': username, 'roles': ['user'], 'auth_state': None}
    )


@pytest.mark.parametrize(
    'servername,escapedname,caller_escape',
    [
        ('trevor', 'trevor', False),
        ('$p~c|a! ch@rs', '%24p~c%7Ca%21%20ch@rs', False),
        ('$p~c|a! ch@rs', '%24p~c%7Ca%21%20ch@rs', True),
        ('hash#?question', 'hash%23%3Fquestion', True),
    ],
)
async def test_create_named_server(
    app, named_servers, servername, escapedname, caller_escape
):
    username = 'walnut'
    user = add_user(app.db, app, name=username)
    # assert user.allow_named_servers == True
    cookies = await app.login_user(username)
    request_servername = servername
    if caller_escape:
        request_servername = url_escape_path(servername)

    r = await api_request(
        app, 'users', username, 'servers', request_servername, method='post'
    )
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    url = url_path_join(public_url(app, user), request_servername, 'env')
    expected_url = url_path_join(public_url(app, user), escapedname, 'env')
    r = await async_requests.get(url, cookies=cookies)
    r.raise_for_status()
    # requests doesn't fully encode the servername: "$p~c%7Ca!%20ch@rs".
    # Since this is the internal requests representation and not the JupyterHub
    # representation it just needs to be equivalent.
    assert unquote(r.url) == unquote(expected_url)
    env = r.json()
    prefix = env.get('JUPYTERHUB_SERVICE_PREFIX')
    assert prefix == user.spawners[servername].server.base_url
    assert prefix.endswith(f'/user/{username}/{escapedname}/')

    r = await api_request(app, 'users', username)
    r.raise_for_status()

    # Ensure the unescaped name is stored in the DB
    db_server_names = set(
        app.db.query(orm.User).filter_by(name=username).first().orm_spawners.keys()
    )
    assert db_server_names == {"", servername}

    user_model = normalize_user(r.json())
    assert user_model == fill_user(
        {
            'name': username,
            'roles': ['user'],
            'auth_state': None,
            'servers': {
                servername: {
                    'name': name,
                    'started': TIMESTAMP,
                    'last_activity': TIMESTAMP,
                    'url': url_path_join(user.url, escapedname, '/'),
                    'pending': None,
                    'ready': True,
                    'stopped': False,
                    'progress_url': 'PREFIX/hub/api/users/{}/servers/{}/progress'.format(
                        username, escapedname
                    ),
                    'state': {'pid': 0},
                    'user_options': {},
                }
                for name in [servername]
            },
        }
    )


async def test_create_invalid_named_server(app, named_servers):
    username = 'walnut'
    user = add_user(app.db, app, name=username)
    # assert user.allow_named_servers == True
    cookies = await app.login_user(username)
    server_name = "a$/b"
    request_servername = 'a%24%2fb'

    r = await api_request(
        app, 'users', username, 'servers', request_servername, method='post'
    )

    with pytest.raises(HTTPError) as exc:
        r.raise_for_status()
    assert exc.value.response.json() == {
        'status': 400,
        'message': "Invalid server_name (may not contain '/'): a$/b",
    }


async def test_delete_named_server(app, named_servers):
    username = 'donaar'
    user = add_user(app.db, app, name=username)
    assert user.allow_named_servers
    cookies = await app.login_user(username)
    servername = 'splugoth'
    r = await api_request(app, 'users', username, 'servers', servername, method='post')
    r.raise_for_status()
    assert r.status_code == 201

    r = await api_request(
        app, 'users', username, 'servers', servername, method='delete'
    )
    r.raise_for_status()
    assert r.status_code == 204

    r = await api_request(app, 'users', username)
    r.raise_for_status()

    user_model = normalize_user(r.json())
    assert user_model == fill_user(
        {'name': username, 'roles': ['user'], 'auth_state': None}
    )
    # wrapper Spawner is gone
    assert servername not in user.spawners
    # low-level record still exists
    assert servername in user.orm_spawners

    r = await api_request(
        app,
        'users',
        username,
        'servers',
        servername,
        method='delete',
        data=json.dumps({'remove': True}),
    )
    r.raise_for_status()
    assert r.status_code == 204
    # low-level record is now removed
    assert servername not in user.orm_spawners
    # and it's still not in the high-level wrapper dict
    assert servername not in user.spawners


async def test_named_server_disabled(app):
    username = 'user'
    servername = 'okay'
    r = await api_request(app, 'users', username, 'servers', servername, method='post')
    assert r.status_code == 400
    r = await api_request(
        app, 'users', username, 'servers', servername, method='delete'
    )
    assert r.status_code == 400


async def test_named_server_limit(app, named_servers):
    username = 'foo'
    user = add_user(app.db, app, name=username)
    cookies = await app.login_user(username)

    # Create 1st named server
    servername1 = 'bar-1'
    r = await api_request(app, 'users', username, 'servers', servername1, method='post')
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    # Create 2nd named server
    servername2 = 'bar-2'
    r = await api_request(app, 'users', username, 'servers', servername2, method='post')
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    # Create 3rd named server
    servername3 = 'bar-3'
    r = await api_request(app, 'users', username, 'servers', servername3, method='post')
    assert r.status_code == 400
    assert r.json() == {
        "status": 400,
        "message": "User foo already has the maximum of 2 named servers.  One must be deleted before a new server can be created",
    }

    # Create default server
    r = await api_request(app, 'users', username, 'server', method='post')
    assert r.status_code == 201
    assert r.text == ''

    # Delete 1st named server
    r = await api_request(
        app,
        'users',
        username,
        'servers',
        servername1,
        method='delete',
        data=json.dumps({'remove': True}),
    )
    r.raise_for_status()
    assert r.status_code == 204

    # Create 3rd named server again
    r = await api_request(app, 'users', username, 'servers', servername3, method='post')
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''


@pytest.mark.parametrize(
    'username,admin',
    [
        ('nonsuperfoo', False),
        ('superfoo', True),
    ],
)
async def test_named_server_limit_as_callable(
    app, named_servers_with_callable_limit, username, admin
):
    """Test named server limit based on `named_server_limit_per_user_fn` callable"""
    user = add_user(app.db, app, name=username, admin=admin)
    cookies = await app.login_user(username)

    # Create 1st named server
    servername1 = 'bar-1'
    r = await api_request(
        app, 'users', username, 'servers', servername1, method='post', cookies=cookies
    )
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    # Create 2nd named server
    servername2 = 'bar-2'
    r = await api_request(
        app, 'users', username, 'servers', servername2, method='post', cookies=cookies
    )
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    # Create 3rd named server
    servername3 = 'bar-3'
    r = await api_request(
        app, 'users', username, 'servers', servername3, method='post', cookies=cookies
    )

    # No named server limit for admin users as in `named_server_limit_per_user_fn` callable
    if admin:
        r.raise_for_status()
        assert r.status_code == 201
        assert r.text == ''
    else:
        assert r.status_code == 400
        assert r.json() == {
            "status": 400,
            "message": f"User {username} already has the maximum of 2 named servers.  One must be deleted before a new server can be created",
        }


async def test_named_server_spawn_form(app, username, named_servers):
    server_name = "myserver"
    base_url = public_url(app)
    cookies = await app.login_user(username)
    user = app.users[username]
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        r = await get_page(f'spawn/{username}/{server_name}', app, cookies=cookies)
        r.raise_for_status()
        assert r.url.endswith(f'/spawn/{username}/{server_name}')
        assert FormSpawner.options_form in r.text
        spawn_page = BeautifulSoup(r.text, 'html.parser')
        form = spawn_page.find("form")
        action_url = public_host(app) + form["action"]

        # submit the form
        next_url = url_path_join(
            app.base_url, 'hub/spawn-pending', username, server_name
        )
        r = await async_requests.post(
            url_concat(
                action_url,
                {'next': next_url},
            ),
            cookies=cookies,
            data={'bounds': ['-10', '10'], 'energy': '938MeV'},
        )
        r.raise_for_status()
        assert r.history
        history = [_.url for _ in r.history] + [r.url]
        path_history = [urlparse(url).path for url in history]
        assert next_url in path_history
    assert server_name in user.spawners
    spawner = user.spawners[server_name]
    spawner.user_options == {'energy': '938MeV', 'bounds': [-10, 10], 'notspecified': 5}


async def test_user_redirect_default_server_name(
    app, username, named_servers, default_server_name
):
    name = username
    server_name = default_server_name
    cookies = await app.login_user(name)

    r = await api_request(app, 'users', username, 'servers', server_name, method='post')
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    r = await get_page('/user-redirect/tree/top/', app)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == url_path_join(app.base_url, '/hub/login')
    query = urlparse(r.url).query
    assert query == urlencode(
        {'next': url_path_join(app.hub.base_url, '/user-redirect/tree/top/')}
    )

    r = await get_page('/user-redirect/notebooks/test.ipynb', app, cookies=cookies)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    while '/spawn-pending/' in path:
        await asyncio.sleep(0.1)
        r = await async_requests.get(r.url, cookies=cookies)
        path = urlparse(r.url).path
    assert path == url_path_join(
        app.base_url, f'/user/{name}/{server_name}/notebooks/test.ipynb'
    )


async def test_user_redirect_hook_default_server_name(
    app, username, named_servers, default_server_name
):
    """
    Test proper behavior of user_redirect_hook when c.JupyterHub.default_server_name is set
    """
    name = username
    server_name = default_server_name
    cookies = await app.login_user(name)

    r = await api_request(app, 'users', username, 'servers', server_name, method='post')
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    async def dummy_redirect(path, request, user, base_url):
        assert base_url == app.base_url
        assert path == 'redirect-to-terminal'
        assert request.uri == url_path_join(
            base_url, 'hub', 'user-redirect', 'redirect-to-terminal'
        )
        # exclude custom server_name
        # custom hook is respected exactly
        url = url_path_join(user.url, '/terminals/1')
        return url

    app.user_redirect_hook = dummy_redirect

    r = await get_page('/user-redirect/redirect-to-terminal', app)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == url_path_join(app.base_url, '/hub/login')
    query = urlparse(r.url).query
    assert query == urlencode(
        {'next': url_path_join(app.hub.base_url, '/user-redirect/redirect-to-terminal')}
    )

    # We don't actually want to start the server by going through spawn - just want to make sure
    # the redirect is to the right place
    r = await get_page(
        '/user-redirect/redirect-to-terminal',
        app,
        cookies=cookies,
        allow_redirects=False,
    )
    r.raise_for_status()
    redirected_url = urlparse(r.headers['Location'])
    assert redirected_url.path == url_path_join(
        app.base_url, 'user', username, 'terminals/1'
    )


async def test_named_server_stop_server(app, username, named_servers):
    server_name = "myserver"
    await app.login_user(username)
    user = app.users[username]

    r = await api_request(app, 'users', username, 'server', method='post')
    assert r.status_code == 201
    assert r.text == ''
    assert user.spawners[''].server

    with mock.patch.object(
        app.proxy, 'add_user', side_effect=Exception('mock exception')
    ):
        r = await api_request(
            app, 'users', username, 'servers', server_name, method='post'
        )
        r.raise_for_status()
        assert r.status_code == 201
        assert r.text == ''

    assert user.spawners[server_name].server is None
    assert user.spawners[''].server
    assert user.running


@pytest.mark.parametrize(
    "include_stopped_servers",
    [True, False],
)
async def test_stopped_servers(app, user, named_servers, include_stopped_servers):
    r = await api_request(app, 'users', user.name, 'server', method='post')
    r.raise_for_status()
    r = await api_request(app, 'users', user.name, 'servers', "named", method='post')
    r.raise_for_status()

    # wait for starts
    for i in range(60):
        r = await api_request(app, 'users', user.name)
        r.raise_for_status()
        user_model = r.json()
        if not all(s["ready"] for s in user_model["servers"].values()):
            time.sleep(1)
        else:
            break
    else:
        raise TimeoutError(f"User never stopped: {user_model}")

    r = await api_request(app, 'users', user.name, 'server', method='delete')
    r.raise_for_status()
    r = await api_request(app, 'users', user.name, 'servers', "named", method='delete')
    r.raise_for_status()

    # wait for stops
    for i in range(60):
        r = await api_request(app, 'users', user.name)
        r.raise_for_status()
        user_model = r.json()
        if not all(s["stopped"] for s in user_model["servers"].values()):
            time.sleep(1)
        else:
            break
    else:
        raise TimeoutError(f"User never stopped: {user_model}")

    # we have two stopped servers
    path = f"users/{user.name}"
    if include_stopped_servers:
        path = f"{path}?include_stopped_servers"
    r = await api_request(app, path)
    r.raise_for_status()
    user_model = r.json()
    servers = list(user_model["servers"].values())
    if include_stopped_servers:
        assert len(servers) == 2
        assert all(s["last_activity"] for s in servers)
        assert all(s["started"] is None for s in servers)
        assert all(s["stopped"] for s in servers)
        assert not any(s["ready"] for s in servers)
        assert not any(s["pending"] for s in servers)
    else:
        assert user_model["servers"] == {}
