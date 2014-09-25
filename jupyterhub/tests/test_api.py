"""Tests for the REST API"""

import json

import requests

from ..utils import url_path_join as ujoin
from .. import orm

def find_user(db, name):
    return db.query(orm.User).filter(orm.User.name==name).first()
    
def add_user(db, **kwargs):
    user = orm.User(**kwargs)
    db.add(user)
    db.commit()
    return user

def auth_header(db, name):
    user = find_user(db, name)
    if user is None:
        user = add_user(db, name=name)
    if not user.api_tokens:
        token = user.new_api_token()
        db.add(token)
        db.commit()
    else:
        token = user.api_tokens[0]
    return {'Authorization': 'token %s' % token.token}

def api_request(app, *api_path, **kwargs):
    """Make an API request"""
    base_url = app.hub.server.url
    headers = kwargs.setdefault('headers', {})

    if 'Authorization' not in headers:
        headers.update(auth_header(app.db, 'admin'))
    
    url = ujoin(base_url, 'api', *api_path)
    method = kwargs.pop('method', 'get')
    f = getattr(requests, method)
    return f(url, **kwargs)

def test_auth_api(app):
    db = app.db
    r = api_request(app, 'authorizations', 'gobbledygook')
    assert r.status_code == 404
    
    # make a new cookie token
    user = db.query(orm.User).first()
    cookie_token = user.new_cookie_token()
    db.add(cookie_token)
    db.commit()
    
    # check success:
    r = api_request(app, 'authorizations', cookie_token.token)
    assert r.status_code == 200
    reply = r.json()
    assert reply['user'] == user.name
    
    # check fail
    r = api_request(app, 'authorizations', cookie_token.token,
        headers={'Authorization': 'no sir'},
    )
    assert r.status_code == 403

    r = api_request(app, 'authorizations', cookie_token.token,
        headers={'Authorization': 'token: %s' % cookie_token.token},
    )
    assert r.status_code == 403
    

def test_get_users(app):
    db = app.db
    r = api_request(app, 'users')
    assert r.status_code == 200
    assert sorted(r.json(), key=lambda d: d['name']) == [
        {
            'name': 'admin',
            'admin': True,
            'server': None,
        },
        {
            'name': 'user',
            'admin': False,
            'server': None,
        }
    ]

    r = api_request(app, 'users',
        headers=auth_header(db, 'user'),
    )
    assert r.status_code == 403

def test_add_user(app):
    db = app.db
    name = 'newuser'
    r = api_request(app, 'users', name, method='post')
    assert r.status_code == 201
    user = find_user(db, name)
    assert user is not None
    assert user.name == name
    assert not user.admin

def test_add_user_bad(app):
    db = app.db
    name = 'dne_newuser'
    r = api_request(app, 'users', name, method='post')
    assert r.status_code == 400
    user = find_user(db, name)
    assert user is None

def test_add_admin(app):
    db = app.db
    name = 'newadmin'
    r = api_request(app, 'users', name, method='post',
        data=json.dumps({'admin': True}),
    )
    assert r.status_code == 201
    user = find_user(db, name)
    assert user is not None
    assert user.name == name
    assert user.admin

def test_delete_user(app):
    db = app.db
    mal = add_user(db, name='mal')
    r = api_request(app, 'users', 'mal', method='delete')
    assert r.status_code == 204
    

def test_make_admin(app):
    db = app.db
    name = 'admin2'
    r = api_request(app, 'users', name, method='post')
    assert r.status_code == 201
    user = find_user(db, name)
    assert user is not None
    assert user.name == name
    assert not user.admin

    r = api_request(app, 'users', name, method='patch',
        data=json.dumps({'admin': True})
    )
    assert r.status_code == 200
    user = find_user(db, name)
    assert user is not None
    assert user.name == name
    assert user.admin


def test_spawn(app, io_loop):
    db = app.db
    name = 'wash'
    user = add_user(db, name=name)
    r = api_request(app, 'users', name, 'server', method='post')
    assert r.status_code == 201
    assert user.spawner is not None
    status = io_loop.run_sync(user.spawner.poll)
    assert status is None
    
    assert user.server.base_url == '/user/%s' % name
    r = requests.get(ujoin(app.proxy.public_server.url, user.server.base_url))
    assert r.status_code == 200
    assert r.text == user.server.base_url

    r = requests.get(ujoin(app.proxy.public_server.url, user.server.base_url, 'args'))
    assert r.status_code == 200
    argv = r.json()
    for expected in ['--user=%s' % name, '--base-url=%s' % user.server.base_url]:
        assert expected in argv
    
    r = api_request(app, 'users', name, 'server', method='delete')
    assert r.status_code == 204
    
    assert user.spawner is None
    