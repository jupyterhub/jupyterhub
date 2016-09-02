"""Tests for HTML pages"""

from urllib.parse import urlencode, urlparse

import requests

from ..utils import url_path_join as ujoin
from .. import orm

import mock
from .mocking import FormSpawner, public_url, public_host
from .test_api import api_request

def get_page(path, app, hub=True, **kw):
    if hub:
        prefix = app.hub.server.base_url
    else:
        prefix = app.base_url
    base_url = ujoin(public_host(app), prefix)
    print(base_url)
    return requests.get(ujoin(base_url, path), **kw)

def test_root_no_auth(app, io_loop):
    print(app.hub.server.is_up())
    routes = io_loop.run_sync(app.proxy.get_routes)
    print(routes)
    print(app.hub.server)
    url = ujoin(public_host(app), app.hub.server.base_url)
    print(url)
    r = requests.get(url)
    r.raise_for_status()
    assert r.url == ujoin(url, 'login')

def test_root_auth(app):
    cookies = app.login_user('river')
    r = requests.get(public_url(app), cookies=cookies)
    r.raise_for_status()
    assert r.url == public_url(app, app.users['river'])

def test_root_redirect(app):
    name = 'wash'
    cookies = app.login_user(name)
    next_url = ujoin(app.base_url, 'user/other/test.ipynb')
    url = '/?' + urlencode({'next': next_url})
    r = get_page(url, app, cookies=cookies)
    r.raise_for_status()
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, 'user/%s/test.ipynb' % name)

def test_home_no_auth(app):
    r = get_page('home', app, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 302
    assert '/hub/login' in r.headers['Location']

def test_home_auth(app):
    cookies = app.login_user('river')
    r = get_page('home', app, cookies=cookies)
    r.raise_for_status()
    assert r.url.endswith('home')

def test_admin_no_auth(app):
    r = get_page('admin', app)
    assert r.status_code == 403

def test_admin_not_admin(app):
    cookies = app.login_user('wash')
    r = get_page('admin', app, cookies=cookies)
    assert r.status_code == 403

def test_admin(app):
    cookies = app.login_user('river')
    u = orm.User.find(app.db, 'river')
    u.admin = True
    app.db.commit()
    r = get_page('admin', app, cookies=cookies)
    r.raise_for_status()
    assert r.url.endswith('/admin')


def test_spawn_redirect(app, io_loop):
    name = 'wash'
    cookies = app.login_user(name)
    u = app.users[orm.User.find(app.db, name)]
    
    # ensure wash's server isn't running:
    r = api_request(app, 'users', name, 'server', method='delete', cookies=cookies)
    r.raise_for_status()
    status = io_loop.run_sync(u.spawner.poll)
    assert status is not None
    
    # test spawn page when no server is running
    r = get_page('spawn', app, cookies=cookies)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, 'user/%s' % name)
    
    # should have started server
    status = io_loop.run_sync(u.spawner.poll)
    assert status is None
    
    # test spawn page when server is already running (just redirect)
    r = get_page('spawn', app, cookies=cookies)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/user/%s' % name)

def test_spawn_page(app):
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        cookies = app.login_user('jones')
        r = get_page('spawn', app, cookies=cookies)
        assert r.url.endswith('/spawn')
        assert FormSpawner.options_form in r.text

def test_spawn_form(app, io_loop):
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        base_url = ujoin(public_host(app), app.hub.server.base_url)
        cookies = app.login_user('jones')
        orm_u = orm.User.find(app.db, 'jones')
        u = app.users[orm_u]
        io_loop.run_sync(u.stop)
    
        r = requests.post(ujoin(base_url, 'spawn'), cookies=cookies, data={
            'bounds': ['-1', '1'],
            'energy': '511keV',
        })
        r.raise_for_status()
        print(u.spawner)
        print(u.spawner.user_options)
        assert u.spawner.user_options == {
            'energy': '511keV',
            'bounds': [-1, 1],
            'notspecified': 5,
        }

def test_spawn_form_with_file(app, io_loop):
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        base_url = ujoin(public_host(app), app.hub.server.base_url)
        cookies = app.login_user('jones')
        orm_u = orm.User.find(app.db, 'jones')
        u = app.users[orm_u]
        io_loop.run_sync(u.stop)

        r = requests.post(ujoin(base_url, 'spawn'),
                          cookies=cookies,
                          data={
                              'bounds': ['-1', '1'],
                              'energy': '511keV',
                          },
                          files={'hello': ('hello.txt', b'hello world\n')}
                      )
        r.raise_for_status()
        assert u.spawner.user_options == {
            'energy': '511keV',
            'bounds': [-1, 1],
            'notspecified': 5,
            'hello': {'filename': 'hello.txt',
                      'body': b'hello world\n',
                      'content_type': 'application/unknown'},
        }


def test_user_redirect(app):
    name = 'wash'
    cookies = app.login_user(name)

    r = get_page('/user-redirect/tree/top/', app)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/hub/login')
    query = urlparse(r.url).query
    assert query == urlencode({
        'next': ujoin(app.hub.server.base_url, '/user-redirect/tree/top/')
    })

    r = get_page('/user-redirect/notebooks/test.ipynb', app, cookies=cookies)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/user/%s/notebooks/test.ipynb' % name)


def test_user_redirect_deprecated(app):
    """redirecting from /user/someonelse/ URLs (deprecated)"""
    name = 'wash'
    cookies = app.login_user(name)

    r = get_page('/user/baduser', app, cookies=cookies, hub=False)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/user/%s' % name)

    r = get_page('/user/baduser/test.ipynb', app, cookies=cookies, hub=False)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/user/%s/test.ipynb' % name)

    r = get_page('/user/baduser/test.ipynb', app, hub=False)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/hub/login')
    query = urlparse(r.url).query
    assert query == urlencode({
        'next': ujoin(app.base_url, '/hub/user/baduser/test.ipynb')
    })


def test_login_fail(app):
    name = 'wash'
    base_url = public_url(app)
    r = requests.post(base_url + 'hub/login',
        data={
            'username': name,
            'password': 'wrong',
        },
        allow_redirects=False,
    )
    assert not r.cookies


def test_login_redirect(app, io_loop):
    cookies = app.login_user('river')
    user = app.users['river']
    # no next_url, server running
    io_loop.run_sync(user.spawn)
    r = get_page('login', app, cookies=cookies, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 302
    assert '/user/river' in r.headers['Location']
    
    # no next_url, server not running
    io_loop.run_sync(user.stop)
    r = get_page('login', app, cookies=cookies, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 302
    assert '/hub/' in r.headers['Location']
    
    # next URL given, use it
    r = get_page('login?next=/hub/admin', app, cookies=cookies, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 302
    assert r.headers['Location'].endswith('/hub/admin')


def test_logout(app):
    name = 'wash'
    cookies = app.login_user(name)
    r = requests.get(public_host(app) + app.tornado_settings['logout_url'], cookies=cookies)
    r.raise_for_status()
    login_url = public_host(app) + app.tornado_settings['login_url']
    assert r.url == login_url
    assert r.cookies == {}


def test_login_no_whitelist_adds_user(app):
    auth = app.authenticator
    mock_add_user = mock.Mock()
    with mock.patch.object(auth, 'add_user', mock_add_user):
        cookies = app.login_user('jubal')

    user = app.users['jubal']
    assert mock_add_user.mock_calls == [mock.call(user)]


def test_static_files(app):
    base_url = ujoin(public_host(app), app.hub.server.base_url)
    r = requests.get(ujoin(base_url, 'logo'))
    r.raise_for_status()
    assert r.headers['content-type'] == 'image/png'
    r = requests.get(ujoin(base_url, 'static', 'images', 'jupyter.png'))
    r.raise_for_status()
    assert r.headers['content-type'] == 'image/png'
    r = requests.get(ujoin(base_url, 'static', 'css', 'style.min.css'))
    r.raise_for_status()
    assert r.headers['content-type'] == 'text/css'
