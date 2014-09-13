"""Tests for the REST API"""

import requests

from ..utils import url_path_join as ujoin
from .. import orm


def api_request(app, *api_path, **kwargs):
    """Make an API request"""
    base_url = app.hub.server.url
    token = app.db.query(orm.APIToken).first()
    kwargs.setdefault('headers', {})
    kwargs['headers'].setdefault('Authorization', 'token %s' % token.token)
    
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
    

