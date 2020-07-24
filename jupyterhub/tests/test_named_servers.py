"""Tests for named servers"""
import asyncio
import json
from unittest import mock
from urllib.parse import urlencode
from urllib.parse import urlparse

import pytest
from tornado.httputil import url_concat

from ..utils import url_path_join
from .mocking import FormSpawner
from .mocking import public_url
from .test_api import add_user
from .test_api import api_request
from .test_api import fill_user
from .test_api import normalize_user
from .test_api import TIMESTAMP
from .utils import async_requests
from .utils import get_page


@pytest.fixture
def named_servers(app):
    with mock.patch.dict(
        app.tornado_settings,
        {'allow_named_servers': True, 'named_server_limit_per_user': 2},
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
    print(user_model)
    assert user_model == fill_user(
        {
            'name': username,
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
        {'name': username, 'servers': {}, 'auth_state': None}
    )


async def test_create_named_server(app, named_servers):
    username = 'walnut'
    user = add_user(app.db, app, name=username)
    # assert user.allow_named_servers == True
    cookies = await app.login_user(username)
    servername = 'trevor'
    r = await api_request(app, 'users', username, 'servers', servername, method='post')
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    url = url_path_join(public_url(app, user), servername, 'env')
    r = await async_requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert r.url == url
    env = r.json()
    prefix = env.get('JUPYTERHUB_SERVICE_PREFIX')
    assert prefix == user.spawners[servername].server.base_url
    assert prefix.endswith('/user/%s/%s/' % (username, servername))

    r = await api_request(app, 'users', username)
    r.raise_for_status()

    user_model = normalize_user(r.json())
    assert user_model == fill_user(
        {
            'name': username,
            'auth_state': None,
            'servers': {
                servername: {
                    'name': name,
                    'started': TIMESTAMP,
                    'last_activity': TIMESTAMP,
                    'url': url_path_join(user.url, name, '/'),
                    'pending': None,
                    'ready': True,
                    'progress_url': 'PREFIX/hub/api/users/{}/servers/{}/progress'.format(
                        username, servername
                    ),
                    'state': {'pid': 0},
                    'user_options': {},
                }
                for name in [servername]
            },
        }
    )


async def test_delete_named_server(app, named_servers):
    username = 'donaar'
    user = add_user(app.db, app, name=username)
    assert user.allow_named_servers
    cookies = app.login_user(username)
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
        {'name': username, 'auth_state': None, 'servers': {}}
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


async def test_named_server_spawn_form(app, username, named_servers):
    server_name = "myserver"
    base_url = public_url(app)
    cookies = await app.login_user(username)
    user = app.users[username]
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        r = await get_page(
            'spawn/%s/%s' % (username, server_name), app, cookies=cookies
        )
        r.raise_for_status()
        assert r.url.endswith('/spawn/%s/%s' % (username, server_name))
        assert FormSpawner.options_form in r.text

        # submit the form
        next_url = url_path_join(
            app.base_url, 'hub/spawn-pending', username, server_name
        )
        r = await async_requests.post(
            url_concat(
                url_path_join(base_url, 'hub/spawn', username, server_name),
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
        app.base_url, '/user/{}/{}/notebooks/test.ipynb'.format(name, server_name)
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
