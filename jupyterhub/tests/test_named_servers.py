"""Tests for named servers"""
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


@pytest.mark.gen_test
def test_default_server(app, named_servers):
    """Test the default /users/:user/server handler when named servers are enabled"""
    username = 'rosie'
    user = add_user(app.db, app, name=username)
    r = yield api_request(app, 'users', username, 'server', method='post')
    assert r.status_code == 201
    assert r.text == ''

    r = yield api_request(app, 'users', username)
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
    r = yield api_request(app, 'users', username, 'server', method='delete')
    assert r.status_code == 204
    assert r.text == ''

    r = yield api_request(app, 'users', username)
    r.raise_for_status()

    user_model = normalize_user(r.json())
    assert user_model == fill_user({
        'name': username,
        'servers': {},
        'auth_state': None,
    })


@pytest.mark.gen_test
def test_create_named_server(app, named_servers):
    username = 'walnut'
    user = add_user(app.db, app, name=username)
    # assert user.allow_named_servers == True
    cookies = yield app.login_user(username)
    servername = 'trevor'
    r = yield api_request(app, 'users', username, 'servers', servername, method='post')
    r.raise_for_status()
    assert r.status_code == 201
    assert r.text == ''

    url = url_path_join(public_url(app, user), servername, 'env')
    r = yield async_requests.get(url, cookies=cookies)
    r.raise_for_status()
    assert r.url == url
    env = r.json()
    prefix = env.get('JUPYTERHUB_SERVICE_PREFIX')
    assert prefix == user.spawners[servername].server.base_url
    assert prefix.endswith('/user/%s/%s/' % (username, servername))

    r = yield api_request(app, 'users', username)
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


@pytest.mark.gen_test
def test_delete_named_server(app, named_servers):
    username = 'donaar'
    user = add_user(app.db, app, name=username)
    assert user.allow_named_servers
    cookies = app.login_user(username)
    servername = 'splugoth'
    r = yield api_request(app, 'users', username, 'servers', servername, method='post')
    r.raise_for_status()
    assert r.status_code == 201

    r = yield api_request(app, 'users', username, 'servers', servername, method='delete')
    r.raise_for_status()
    assert r.status_code == 204

    r = yield api_request(app, 'users', username)
    r.raise_for_status()

    user_model = normalize_user(r.json())
    assert user_model == fill_user({
        'name': username,
        'auth_state': None,
        'servers': {},
    })

@pytest.mark.gen_test
def test_named_server_disabled(app):
    username = 'user'
    servername = 'okay'
    r = yield api_request(app, 'users', username, 'servers', servername, method='post')
    assert r.status_code == 400
    r = yield api_request(app, 'users', username, 'servers', servername, method='delete')
    assert r.status_code == 400
