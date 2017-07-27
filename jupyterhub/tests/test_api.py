"""Tests for the REST API."""

import json
import time
import sys
from unittest import mock
from urllib.parse import urlparse, quote

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

    if 'Authorization' not in headers:
        headers.update(auth_header(app.db, 'admin'))

    url = ujoin(base_url, 'api', *api_path)
    method = kwargs.pop('method', 'get')
    f = getattr(async_requests, method)
    resp = yield f(url, **kwargs)
    assert "frame-ancestors 'self'" in resp.headers['Content-Security-Policy']
    assert ujoin(app.hub.base_url, "security/csp-report") in resp.headers['Content-Security-Policy']
    assert 'http' not in resp.headers['Content-Security-Policy']
    return resp


# --------------------
# Authentication tests
# --------------------


@mark.gen_test
def test_auth_api(app):
    db = app.db
    r = yield api_request(app, 'authorizations', 'gobbledygook')
    assert r.status_code == 404

    # make a new cookie token
    user = db.query(orm.User).first()
    api_token = user.new_api_token()

    # check success:
    r = yield api_request(app, 'authorizations/token', api_token)
    assert r.status_code == 200
    reply = r.json()
    assert reply['name'] == user.name

    # check fail
    r = yield api_request(app, 'authorizations/token', api_token,
        headers={'Authorization': 'no sir'},
    )
    assert r.status_code == 403

    r = yield api_request(app, 'authorizations/token', api_token,
        headers={'Authorization': 'token: %s' % user.cookie_id},
    )
    assert r.status_code == 403


@mark.gen_test
def test_referer_check(app):
    url = ujoin(public_host(app), app.hub.base_url)
    host = urlparse(url).netloc
    user = find_user(app.db, 'admin')
    if user is None:
        user = add_user(app.db, name='admin', admin=True)
    cookies = yield app.login_user('admin')
    app_user = app.users[user]
    # stop the admin's server so we don't mess up future tests
    yield app.proxy.delete_user(app_user)
    yield app_user.stop()

    r = yield api_request(app, 'users',
        headers={
            'Authorization': '',
            'Referer': 'null',
        }, cookies=cookies,
    )
    assert r.status_code == 403

    r = yield api_request(app, 'users',
        headers={
            'Authorization': '',
            'Referer': 'http://attack.com/csrf/vulnerability',
        }, cookies=cookies,
    )
    assert r.status_code == 403

    r = yield api_request(app, 'users',
        headers={
            'Authorization': '',
            'Referer': url,
            'Host': host,
        }, cookies=cookies,
    )
    assert r.status_code == 200

    r = yield api_request(app, 'users',
        headers={
            'Authorization': '',
            'Referer': ujoin(url, 'foo/bar/baz/bat'),
            'Host': host,
        }, cookies=cookies,
    )
    assert r.status_code == 200


# --------------
# User API tests
# --------------


@mark.user
@mark.gen_test
def test_get_users(app):
    db = app.db
    r = yield api_request(app, 'users')
    assert r.status_code == 200

    users = sorted(r.json(), key=lambda d: d['name'])
    for u in users:
        u.pop('last_activity')
    assert users == [
        {
            'kind': 'user',
            'name': 'admin',
            'groups': [],
            'admin': True,
            'server': None,
            'pending': None,
        },
        {
            'kind': 'user',
            'name': 'user',
            'groups': [],
            'admin': False,
            'server': None,
            'pending': None,
        }
    ]

    r = yield api_request(app, 'users',
        headers=auth_header(db, 'user'),
    )
    assert r.status_code == 403


@mark.user
@mark.gen_test
def test_add_user(app):
    db = app.db
    name = 'newuser'
    r = yield api_request(app, 'users', name, method='post')
    assert r.status_code == 201
    user = find_user(db, name)
    assert user is not None
    assert user.name == name
    assert not user.admin


@mark.user
@mark.gen_test
def test_get_user(app):
    name = 'user'
    r = yield api_request(app, 'users', name)
    assert r.status_code == 200
    user = r.json()
    user.pop('last_activity')
    assert user == {
        'kind': 'user',
        'name': name,
        'groups': [],
        'admin': False,
        'server': None,
        'pending': None,
    }


@mark.user
@mark.gen_test
def test_add_multi_user_bad(app):
    r = yield api_request(app, 'users', method='post')
    assert r.status_code == 400
    r = yield api_request(app, 'users', method='post', data='{}')
    assert r.status_code == 400
    r = yield api_request(app, 'users', method='post', data='[]')
    assert r.status_code == 400


@mark.user
@mark.gen_test
def test_add_multi_user_invalid(app):
    app.authenticator.username_pattern = r'w.*'
    r = yield api_request(app, 'users', method='post',
        data=json.dumps({'usernames': ['Willow', 'Andrew', 'Tara']})
    )
    app.authenticator.username_pattern = ''
    assert r.status_code == 400
    assert r.json()['message'] == 'Invalid usernames: andrew, tara'


@mark.user
@mark.gen_test
def test_add_multi_user(app):
    db = app.db
    names = ['a', 'b']
    r = yield api_request(app, 'users', method='post',
        data=json.dumps({'usernames': names}),
    )
    assert r.status_code == 201
    reply = r.json()
    r_names = [ user['name'] for user in reply ]
    assert names == r_names

    for name in names:
        user = find_user(db, name)
        assert user is not None
        assert user.name == name
        assert not user.admin

    # try to create the same users again
    r = yield api_request(app, 'users', method='post',
        data=json.dumps({'usernames': names}),
    )
    assert r.status_code == 400

    names = ['a', 'b', 'ab']

    # try to create the same users again
    r = yield api_request(app, 'users', method='post',
        data=json.dumps({'usernames': names}),
    )
    assert r.status_code == 201
    reply = r.json()
    r_names = [ user['name'] for user in reply ]
    assert r_names == ['ab']


@mark.user
@mark.gen_test
def test_add_multi_user_admin(app):
    db = app.db
    names = ['c', 'd']
    r = yield api_request(app, 'users', method='post',
        data=json.dumps({'usernames': names, 'admin': True}),
    )
    assert r.status_code == 201
    reply = r.json()
    r_names = [ user['name'] for user in reply ]
    assert names == r_names

    for name in names:
        user = find_user(db, name)
        assert user is not None
        assert user.name == name
        assert user.admin


@mark.user
@mark.gen_test
def test_add_user_bad(app):
    db = app.db
    name = 'dne_newuser'
    r = yield api_request(app, 'users', name, method='post')
    assert r.status_code == 400
    user = find_user(db, name)
    assert user is None


@mark.user
@mark.gen_test
def test_add_admin(app):
    db = app.db
    name = 'newadmin'
    r = yield api_request(app, 'users', name, method='post',
        data=json.dumps({'admin': True}),
    )
    assert r.status_code == 201
    user = find_user(db, name)
    assert user is not None
    assert user.name == name
    assert user.admin


@mark.user
@mark.gen_test
def test_delete_user(app):
    db = app.db
    mal = add_user(db, name='mal')
    r = yield api_request(app, 'users', 'mal', method='delete')
    assert r.status_code == 204


@mark.user
@mark.gen_test
def test_make_admin(app):
    db = app.db
    name = 'admin2'
    r = yield api_request(app, 'users', name, method='post')
    assert r.status_code == 201
    user = find_user(db, name)
    assert user is not None
    assert user.name == name
    assert not user.admin

    r = yield api_request(app, 'users', name, method='patch',
        data=json.dumps({'admin': True})
    )
    assert r.status_code == 200
    user = find_user(db, name)
    assert user is not None
    assert user.name == name
    assert user.admin


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
    r = yield async_requests.get(url)
    assert r.status_code == 200
    assert r.text == spawner.server.base_url

    r = yield async_requests.get(ujoin(url, 'args'))
    assert r.status_code == 200
    argv = r.json()
    assert '--port' in ' '.join(argv)
    r = yield async_requests.get(ujoin(url, 'env'))
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


@mark.gen_test
def test_slow_spawn(app, no_patience, request):
    patch = mock.patch.dict(app.tornado_settings, {'spawner_class': mocking.SlowSpawner})
    patch.start()
    request.addfinalizer(patch.stop)
    db = app.db
    name = 'zoe'
    user = add_user(db, app=app, name=name)
    r = yield api_request(app, 'users', name, 'server', method='post')
    r.raise_for_status()
    assert r.status_code == 202
    app_user = app.users[name]
    assert app_user.spawner is not None
    assert app_user.spawner._spawn_pending
    assert not app_user.spawner._stop_pending

    @gen.coroutine
    def wait_spawn():
        while app_user.spawner._spawn_pending:
            yield gen.sleep(0.1)

    yield wait_spawn()
    assert not app_user.spawner._spawn_pending
    status = yield app_user.spawner.poll()
    assert status is None

    @gen.coroutine
    def wait_stop():
        while app_user.spawner._stop_pending:
            yield gen.sleep(0.1)

    r = yield api_request(app, 'users', name, 'server', method='delete')
    r.raise_for_status()
    assert r.status_code == 202
    assert app_user.spawner is not None
    assert app_user.spawner._stop_pending

    r = yield api_request(app, 'users', name, 'server', method='delete')
    r.raise_for_status()
    assert r.status_code == 202
    assert app_user.spawner is not None
    assert app_user.spawner._stop_pending

    yield wait_stop()
    assert not app_user.spawner._stop_pending
    assert app_user.spawner is not None
    r = yield api_request(app, 'users', name, 'server', method='delete')
    assert r.status_code == 400


@mark.gen_test
def test_never_spawn(app, no_patience, request):
    patch = mock.patch.dict(app.tornado_settings, {'spawner_class': mocking.NeverSpawner})
    patch.start()
    request.addfinalizer(patch.stop)

    db = app.db
    name = 'badger'
    user = add_user(db, app=app, name=name)
    r = yield api_request(app, 'users', name, 'server', method='post')
    app_user = app.users[name]
    assert app_user.spawner is not None
    assert app_user.spawner._spawn_pending

    @gen.coroutine
    def wait_pending():
        while app_user.spawner._spawn_pending:
            yield gen.sleep(0.1)

    yield wait_pending()
    assert not app_user.spawner._spawn_pending
    status = yield app_user.spawner.poll()
    assert status is not None


@mark.gen_test
def test_get_proxy(app):
    r = yield api_request(app, 'proxy')
    r.raise_for_status()
    reply = r.json()
    assert list(reply.keys()) == ['/']


@mark.gen_test
def test_cookie(app):
    db = app.db
    name = 'patience'
    user = add_user(db, app=app, name=name)
    r = yield api_request(app, 'users', name, 'server', method='post')
    assert r.status_code == 201
    assert 'pid' in user.orm_spawners[''].state
    app_user = app.users[name]

    cookies = yield app.login_user(name)
    cookie_name = app.hub.cookie_name
    # cookie jar gives '"cookie-value"', we want 'cookie-value'
    cookie = cookies[cookie_name][1:-1]
    r = yield api_request(app, 'authorizations/cookie',
        cookie_name, "nothintoseehere",
    )
    assert r.status_code == 404

    r = yield api_request(app, 'authorizations/cookie',
        cookie_name, quote(cookie, safe=''),
    )
    r.raise_for_status()
    reply = r.json()
    assert reply['name'] == name

    # deprecated cookie in body:
    r = yield api_request(app, 'authorizations/cookie',
        cookie_name, data=cookie,
    )
    r.raise_for_status()
    reply = r.json()
    assert reply['name'] == name


@mark.gen_test
def test_token(app):
    name = 'book'
    user = add_user(app.db, app=app, name=name)
    token = user.new_api_token()
    r = yield api_request(app, 'authorizations/token', token)
    r.raise_for_status()
    user_model = r.json()
    assert user_model['name'] == name
    r = yield api_request(app, 'authorizations/token', 'notauthorized')
    assert r.status_code == 404


@mark.gen_test
@mark.parametrize("headers, data, status", [
    ({}, None, 200),
    ({'Authorization': ''}, None, 403),
    ({}, {'username': 'fake', 'password': 'fake'}, 200),
])
def test_get_new_token(app, headers, data, status):
    if data:
        data = json.dumps(data)
    # request a new token
    r = yield api_request(app, 'authorizations', 'token', method='post', data=data, headers=headers)
    assert r.status_code == status
    if status != 200:
        return
    reply = r.json()
    assert 'token' in reply
    r = yield api_request(app, 'authorizations', 'token', reply['token'])
    r.raise_for_status()
    assert 'name' in r.json()


# ---------------
# Group API tests
# ---------------


@mark.group
@mark.gen_test
def test_groups_list(app):
    r = yield api_request(app, 'groups')
    r.raise_for_status()
    reply = r.json()
    assert reply == []

    # create a group
    group = orm.Group(name='alphaflight')
    app.db.add(group)
    app.db.commit()

    r = yield api_request(app, 'groups')
    r.raise_for_status()
    reply = r.json()
    assert reply == [{
        'kind': 'group',
        'name': 'alphaflight',
        'users': []
    }]


@mark.group
@mark.gen_test
def test_group_get(app):
    group = orm.Group.find(app.db, name='alphaflight')
    user = add_user(app.db, app=app, name='sasquatch')
    group.users.append(user)
    app.db.commit()

    r = yield api_request(app, 'groups/runaways')
    assert r.status_code == 404

    r = yield api_request(app, 'groups/alphaflight')
    r.raise_for_status()
    reply = r.json()
    assert reply == {
        'kind': 'group',
        'name': 'alphaflight',
        'users': ['sasquatch']
    }


@mark.group
@mark.gen_test
def test_group_create_delete(app):
    db = app.db
    r = yield api_request(app, 'groups/runaways', method='delete')
    assert r.status_code == 404

    r = yield api_request(app, 'groups/new', method='post',
        data=json.dumps({'users': ['doesntexist']}),
    )
    assert r.status_code == 400
    assert orm.Group.find(db, name='new') is None

    r = yield api_request(app, 'groups/omegaflight', method='post',
        data=json.dumps({'users': ['sasquatch']}),
    )
    r.raise_for_status()

    omegaflight = orm.Group.find(db, name='omegaflight')
    sasquatch = find_user(db, name='sasquatch')
    assert omegaflight in sasquatch.groups
    assert sasquatch in omegaflight.users

    # create duplicate raises 400
    r = yield api_request(app, 'groups/omegaflight', method='post')
    assert r.status_code == 400

    r = yield api_request(app, 'groups/omegaflight', method='delete')
    assert r.status_code == 204
    assert omegaflight not in sasquatch.groups
    assert orm.Group.find(db, name='omegaflight') is None

    # delete nonexistent gives 404
    r = yield api_request(app, 'groups/omegaflight', method='delete')
    assert r.status_code == 404


@mark.group
@mark.gen_test
def test_group_add_users(app):
    db = app.db
    # must specify users
    r = yield api_request(app, 'groups/alphaflight/users', method='post', data='{}')
    assert r.status_code == 400

    names = ['aurora', 'guardian', 'northstar', 'sasquatch', 'shaman', 'snowbird']
    users = [ find_user(db, name=name) or add_user(db, app=app, name=name) for name in names ]
    r = yield api_request(app, 'groups/alphaflight/users', method='post', data=json.dumps({
        'users': names,
    }))
    r.raise_for_status()

    for user in users:
        print(user.name)
        assert [ g.name for g in user.groups ] == ['alphaflight']

    group = orm.Group.find(db, name='alphaflight')
    assert sorted([ u.name for u in group.users ]) == sorted(names)


@mark.group
@mark.gen_test
def test_group_delete_users(app):
    db = app.db
    # must specify users
    r = yield api_request(app, 'groups/alphaflight/users', method='delete', data='{}')
    assert r.status_code == 400

    names = ['aurora', 'guardian', 'northstar', 'sasquatch', 'shaman', 'snowbird']
    users = [ find_user(db, name=name) for name in names ]
    r = yield api_request(app, 'groups/alphaflight/users', method='delete', data=json.dumps({
        'users': names[:2],
    }))
    r.raise_for_status()

    for user in users[:2]:
        assert user.groups == []
    for user in users[2:]:
        assert [ g.name for g in user.groups ] == ['alphaflight']

    group = orm.Group.find(db, name='alphaflight')
    assert sorted([ u.name for u in group.users ]) == sorted(names[2:])


# -----------------
# Service API tests
# -----------------


@mark.services
@mark.gen_test
def test_get_services(app, mockservice_url):
    mockservice = mockservice_url
    db = app.db
    r = yield api_request(app, 'services')
    r.raise_for_status()
    assert r.status_code == 200

    services = r.json()
    assert services == {
        mockservice.name: {
            'name': mockservice.name,
            'admin': True,
            'command': mockservice.command,
            'pid': mockservice.proc.pid,
            'prefix': mockservice.server.base_url,
            'url': mockservice.url,
        }
    }

    r = yield api_request(app, 'services',
        headers=auth_header(db, 'user'),
    )
    assert r.status_code == 403


@mark.services
@mark.gen_test
def test_get_service(app, mockservice_url):
    mockservice = mockservice_url
    db = app.db
    r = yield api_request(app, 'services/%s' % mockservice.name)
    r.raise_for_status()
    assert r.status_code == 200

    service = r.json()
    assert service == {
        'name': mockservice.name,
        'admin': True,
        'command': mockservice.command,
        'pid': mockservice.proc.pid,
        'prefix': mockservice.server.base_url,
        'url': mockservice.url,
    }

    r = yield api_request(app, 'services/%s' % mockservice.name,
        headers={
            'Authorization': 'token %s' % mockservice.api_token
        }
    )
    r.raise_for_status()
    r = yield api_request(app, 'services/%s' % mockservice.name,
        headers=auth_header(db, 'user'),
    )
    assert r.status_code == 403


@mark.gen_test
def test_root_api(app):
    base_url = app.hub.url
    url = ujoin(base_url, 'api')
    r = yield async_requests.get(url)
    r.raise_for_status()
    expected = {
        'version': jupyterhub.__version__
    }
    assert r.json() == expected


@mark.gen_test
def test_info(app):
    r = yield api_request(app, 'info')
    r.raise_for_status()
    data = r.json()
    assert data['version'] == jupyterhub.__version__
    assert sorted(data) == [
        'authenticator',
        'python',
        'spawner',
        'sys_executable',
        'version',
    ]
    assert data['python'] == sys.version
    assert data['sys_executable'] == sys.executable
    assert data['authenticator'] == {
        'class': 'jupyterhub.tests.mocking.MockPAMAuthenticator',
        'version': jupyterhub.__version__,
    }
    assert data['spawner'] == {
        'class': 'jupyterhub.tests.mocking.MockSpawner',
        'version': jupyterhub.__version__,
    }


# -----------------
# General API tests
# -----------------


@mark.gen_test
def test_options(app):
    r = yield api_request(app, 'users', method='options')
    r.raise_for_status()
    assert 'Access-Control-Allow-Headers' in r.headers


@mark.gen_test
def test_bad_json_body(app):
    r = yield api_request(app, 'users', method='post', data='notjson')
    assert r.status_code == 400


# ---------------------------------
# Shutdown MUST always be last test
# ---------------------------------


def test_shutdown(app):
    loop = app.io_loop

    # have to do things a little funky since we are going to stop the loop,
    # which makes gen_test unhappy. So we run the loop ourselves.

    @gen.coroutine
    def shutdown():
        r = yield api_request(app, 'shutdown', method='post',
            data=json.dumps({'servers': True, 'proxy': True,}),
        )
        return r

    real_stop = loop.stop
    def stop():
        stop.called = True
        loop.call_later(1, real_stop)
    with mock.patch.object(loop, 'stop', stop):
        r = loop.run_sync(shutdown, timeout=5)
    r.raise_for_status()
    reply = r.json()
    assert stop.called
