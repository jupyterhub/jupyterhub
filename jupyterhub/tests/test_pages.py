"""Tests for HTML pages"""

import requests

from ..utils import url_path_join as ujoin
from .. import orm


def get_page(path, app, **kw):
    base_url = ujoin(app.proxy.public_server.host, app.hub.server.base_url)
    print(base_url)
    return requests.get(ujoin(base_url, path), **kw)

def test_root_no_auth(app, io_loop):
    print(app.hub.server.is_up())
    routes = io_loop.run_sync(app.proxy.get_routes)
    print(routes)
    print(app.hub.server)
    r = requests.get(app.proxy.public_server.host)
    r.raise_for_status()
    assert r.url == ujoin(app.proxy.public_server.host, app.hub.server.base_url, 'login')

def test_root_auth(app):
    cookies = app.login_user('river')
    r = requests.get(app.proxy.public_server.host, cookies=cookies)
    r.raise_for_status()
    assert r.url == ujoin(app.proxy.public_server.host, '/user/river')

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

