"""Tests for named servers"""
import json
from unittest import mock

import pytest

from ..utils import url_path_join

from .test_api import api_request, add_user, fill_user, normalize_user, TIMESTAMP
from .mocking import public_url
from .utils import async_requests

@pytest.fixture
def named_servers(app):
    with mock.patch.dict(app.tornado_settings,
                         {'allow_named_servers': True}):
        yield


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
    assert user_model == fill_user({
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
                'progress_url': 'PREFIX/hub/api/users/{}/server/progress'.format(username),
                'state': {'pid': 0},
            },
        },
    })


    # now stop the server
    r = await api_request(app, 'users', username, 'server', method='delete')
    assert r.status_code == 204
    assert r.text == ''

    r = await api_request(app, 'users', username)
    r.raise_for_status()

    user_model = normalize_user(r.json())
    assert user_model == fill_user({
        'name': username,
        'servers': {},
        'auth_state': None,
    })


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
    assert user_model == fill_user({
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
                    username, servername),
                'state': {'pid': 0},
            }
            for name in [servername]
        },
    })


async def test_delete_named_server(app, named_servers):
    username = 'donaar'
    user = add_user(app.db, app, name=username)
    assert user.allow_named_servers
    cookies = app.login_user(username)
    servername = 'splugoth'
    r = await api_request(app, 'users', username, 'servers', servername, method='post')
    r.raise_for_status()
    assert r.status_code == 201

    r = await api_request(app, 'users', username, 'servers', servername, method='delete')
    r.raise_for_status()
    assert r.status_code == 204

    r = await api_request(app, 'users', username)
    r.raise_for_status()

    user_model = normalize_user(r.json())
    assert user_model == fill_user({
        'name': username,
        'auth_state': None,
        'servers': {},
    })
    # wrapper Spawner is gone
    assert servername not in user.spawners
    # low-level record still exists
    assert servername in user.orm_spawners

    r = await api_request(
        app, 'users', username, 'servers', servername,
        method='delete',
        data=json.dumps({'remove': True}),
    )
    r.raise_for_status()
    assert r.status_code == 204
    # low-level record is now removes
    assert servername not in user.orm_spawners


async def test_named_server_disabled(app):
    username = 'user'
    servername = 'okay'
    r = await api_request(app, 'users', username, 'servers', servername, method='post')
    assert r.status_code == 400
    r = await api_request(app, 'users', username, 'servers', servername, method='delete')
    assert r.status_code == 400
