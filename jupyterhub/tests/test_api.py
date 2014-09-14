"""Tests for the REST API"""

import requests

from ..utils import url_path_join as ujoin
from .. import orm

def add_user(db, **kwargs):
    user = orm.User(**kwargs)
    db.add(user)
    db.commit()
    return user

def auth_header(db, name):
    user = db.query(orm.User).filter(orm.User.name==name).first()
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
            'server': None,
        },
        {
            'name': 'user',
            'server': None,
        }
    ]

    r = api_request(app, 'users',
        headers=auth_header(db, 'user'),
    )
    assert r.status_code == 403
