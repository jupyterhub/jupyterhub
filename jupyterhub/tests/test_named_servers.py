"""Tests for named servers"""
import pytest

from ..utils import url_path_join

from .test_api import api_request, add_user
from .mocking import public_url
from .utils import async_requests

@pytest.fixture
def named_servers(app):
    key = 'allow_named_servers'
    app.tornado_application.settings[key] = app.tornado_settings[key] = True
    try:
        yield True
    finally:
        app.tornado_application.settings[key] = app.tornado_settings[key] = False


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

    user_model = r.json()
    user_model.pop('last_activity')
    assert user_model == {
        'name': username,
        'groups': [],
        'kind': 'user',
        'admin': False,
        'pending': None,
        'server': user.url,
        'servers': {
            '': {
                'name': '',
                'url': user.url,
            },
        },
    }

    # now stop the server
    r = yield api_request(app, 'users', username, 'server', method='delete')
    assert r.status_code == 204
    assert r.text == ''

    r = yield api_request(app, 'users', username)
    r.raise_for_status()

    user_model = r.json()
    user_model.pop('last_activity')
    assert user_model == {
        'name': username,
        'groups': [],
        'kind': 'user',
        'admin': False,
        'pending': None,
        'server': None,
        'servers': {},
    }



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

    user_model = r.json()
    user_model.pop('last_activity')
    assert user_model == {
        'name': username,
        'groups': [],
        'kind': 'user',
        'admin': False,
        'pending': None,
        'server': user.url,
        'servers': {
            name: {
                'name': name,
                'url': url_path_join(user.url, name, '/'),
            }
            for name in ['', servername]
        },
    }


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
    
    user_model = r.json()
    user_model.pop('last_activity')
    assert user_model == {
        'name': username,
        'groups': [],
        'kind': 'user',
        'admin': False,
        'pending': None,
        'server': user.url,
        'servers': {
            name: {
                'name': name,
                'url': url_path_join(user.url, name, '/'),
            }
            for name in ['']
        },
    }

@pytest.mark.gen_test
def test_named_server_disabled(app):
    username = 'user'
    servername = 'okay'
    r = yield api_request(app, 'users', username, 'servers', servername, method='post')
    assert r.status_code == 400
    r = yield api_request(app, 'users', username, 'servers', servername, method='delete')
    assert r.status_code == 400
