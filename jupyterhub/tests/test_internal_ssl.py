"""Tests for the SSL enabled REST API."""

from concurrent.futures import Future
import json
import time
import sys
from unittest import mock
from urllib.parse import urlparse, quote

import pytest
from pytest import mark
import requests

from tornado import gen

import jupyterhub
from .. import orm
from ..user import User
from ..utils import url_path_join as ujoin
from . import mocking
from .mocking import public_host, public_url
from .utils import async_requests

ssl_enabled = True

def check_db_locks(func):
    """Decorator that verifies no locks are held on database upon exit.

    This decorator for test functions verifies no locks are held on the
    application's database upon exit by creating and dropping a dummy table.

    The decorator relies on an instance of JupyterHubApp being the first
    argument to the decorated function.

    Example
    -------

        @check_db_locks
        def api_request(app, *api_path, **kwargs):

    """
    def new_func(app, *args, **kwargs):
        retval = func(app, *args, **kwargs)

        temp_session = app.session_factory()
        temp_session.execute('CREATE TABLE dummy (foo INT)')
        temp_session.execute('DROP TABLE dummy')
        temp_session.close()

        return retval

    return new_func

def find_user(db, name):
    """Find user in database."""
    return db.query(orm.User).filter(orm.User.name == name).first()

def add_user(db, app=None, **kwargs):
    """Add a user to the database."""
    orm_user = find_user(db, name=kwargs.get('name'))
    if orm_user is None:
        orm_user = orm.User(**kwargs)
        db.add(orm_user)
    else:
        for attr, value in kwargs.items():
            setattr(orm_user, attr, value)
    db.commit()
    if app:
        user = app.users[orm_user.id] = User(orm_user, app.tornado_settings)
        return user
    else:
        return orm_user

def auth_header(db, name):
    """Return header with user's API authorization token."""
    user = find_user(db, name)
    if user is None:
        user = add_user(db, name=name)
    token = user.new_api_token()
    return {'Authorization': 'token %s' % token}

@check_db_locks
@gen.coroutine
def api_request(app, *api_path, **kwargs):
    """Make an API request"""
    base_url = app.hub.url
    headers = kwargs.setdefault('headers', {})

    if 'Authorization' not in headers and not kwargs.pop('noauth', False):
        headers.update(auth_header(app.db, 'admin'))

    kwargs['cert'] = (app.internal_ssl_cert, app.internal_ssl_key)
    kwargs['verify'] = app.internal_ssl_ca

    url = ujoin(base_url, 'api', *api_path)
    method = kwargs.pop('method', 'get')
    f = getattr(async_requests, method)
    resp = yield f(url, **kwargs)
    assert "frame-ancestors 'self'" in resp.headers['Content-Security-Policy']
    assert ujoin(app.hub.base_url, "security/csp-report") in resp.headers['Content-Security-Policy']
    assert 'http' not in resp.headers['Content-Security-Policy']
    return resp

@mark.gen_test
def test_spawn(app):
    db = app.db
    name = 'wash'
    user = add_user(db, app=app, name=name)
    options = {
        's': ['value'],
        'i': 5,
    }
    before_servers = sorted(db.query(orm.Server), key=lambda s: s.url)
    r = yield api_request(app, 'users', name, 'server', method='post',
        data=json.dumps(options),
    )
    assert r.status_code == 201
    assert 'pid' in user.orm_spawners[''].state
    app_user = app.users[name]
    assert app_user.spawner is not None
    spawner = app_user.spawner
    assert app_user.spawner.user_options == options
    assert not app_user.spawner._spawn_pending
    status = yield app_user.spawner.poll()
    assert status is None

    assert spawner.server.base_url == ujoin(app.base_url, 'user/%s' % name) + '/'
    url = public_url(app, user)
    r = yield api_request(app, url)
    assert r.status_code == 200
    assert r.text == spawner.server.base_url

    r = yield api_request(app, ujoin(url, 'args'))
    assert r.status_code == 200
    argv = r.json()
    assert '--port' in ' '.join(argv)
    r = yield api_request(app, ujoin(url, 'env'))
    env = r.json()
    for expected in ['JUPYTERHUB_USER', 'JUPYTERHUB_BASE_URL', 'JUPYTERHUB_API_TOKEN']:
        assert expected in env
    if app.subdomain_host:
        assert env['JUPYTERHUB_HOST'] == app.subdomain_host

    r = yield api_request(app, 'users', name, 'server', method='delete')
    assert r.status_code == 204

    assert 'pid' not in user.orm_spawners[''].state
    status = yield app_user.spawner.poll()
    assert status == 0

    # check that we cleaned up after ourselves
    assert spawner.server is None
    after_servers = sorted(db.query(orm.Server), key=lambda s: s.url)
    assert before_servers == after_servers
    tokens = list(db.query(orm.APIToken).filter(orm.APIToken.user_id == user.id))
    assert tokens == []
    assert app.users.count_active_users()['pending'] == 0

@mark.gen_test
def test_root_api(app):
    base_url = app.hub.url
    r = yield api_request(app, '')
    r.raise_for_status()
    expected = {
        'version': jupyterhub.__version__
    }
    assert r.json() == expected
