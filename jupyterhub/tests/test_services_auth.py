from binascii import hexlify
import json
import os
from queue import Queue
import sys
from threading import Thread
import time
from unittest import mock
from urllib.parse import urlparse

import pytest
from pytest import raises
import requests
import requests_mock

from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, authenticated, HTTPError
from tornado.httputil import url_concat

from ..services.auth import _ExpiringDict, HubAuth, HubAuthenticated
from ..utils import url_path_join
from .mocking import public_url, public_host
from .test_api import add_user
from .utils import async_requests

# mock for sending monotonic counter way into the future
monotonic_future = mock.patch('time.monotonic', lambda : sys.maxsize)

def test_expiring_dict():
    cache = _ExpiringDict(max_age=30)
    cache['key'] = 'cached value'
    assert 'key' in cache
    assert cache['key'] == 'cached value'

    with raises(KeyError):
        cache['nokey']

    with monotonic_future:
        assert 'key' not in cache

    cache['key'] = 'cached value'
    assert 'key' in cache
    with monotonic_future:
        assert 'key' not in cache

    cache['key'] = 'cached value'
    assert 'key' in cache
    with monotonic_future:
        with raises(KeyError):
            cache['key']

    cache['key'] = 'cached value'
    assert 'key' in cache
    with monotonic_future:
        assert cache.get('key', 'default') == 'default'

    cache.max_age = 0

    cache['key'] = 'cached value'
    assert 'key' in cache
    with monotonic_future:
        assert cache.get('key', 'default') == 'cached value'


def test_hub_auth():
    start = time.monotonic()
    auth = HubAuth(cookie_name='foo')
    mock_model = {
        'name': 'onyxia'
    }
    url = url_path_join(auth.api_url, "authorizations/cookie/foo/bar")
    with requests_mock.Mocker() as m:
        m.get(url, text=json.dumps(mock_model))
        user_model = auth.user_for_cookie('bar')
    assert user_model == mock_model
    # check cache
    user_model = auth.user_for_cookie('bar')
    assert user_model == mock_model

    with requests_mock.Mocker() as m:
        m.get(url, status_code=404)
        user_model = auth.user_for_cookie('bar', use_cache=False)
    assert user_model is None

    # invalidate cache with timer
    mock_model = {
        'name': 'willow'
    }
    with monotonic_future, requests_mock.Mocker() as m:
        m.get(url, text=json.dumps(mock_model))
        user_model = auth.user_for_cookie('bar')
    assert user_model == mock_model

    with requests_mock.Mocker() as m:
        m.get(url, status_code=500)
        with raises(HTTPError) as exc_info:
            user_model = auth.user_for_cookie('bar', use_cache=False)
    assert exc_info.value.status_code == 502

    with requests_mock.Mocker() as m:
        m.get(url, status_code=400)
        with raises(HTTPError) as exc_info:
            user_model = auth.user_for_cookie('bar', use_cache=False)
    assert exc_info.value.status_code == 500


def test_hub_authenticated(request):
    auth = HubAuth(cookie_name='jubal')
    mock_model = {
        'name': 'jubalearly',
        'groups': ['lions'],
    }
    cookie_url = url_path_join(auth.api_url, "authorizations/cookie", auth.cookie_name)
    good_url = url_path_join(cookie_url, "early")
    bad_url = url_path_join(cookie_url, "late")

    class TestHandler(HubAuthenticated, RequestHandler):
        hub_auth = auth
        @authenticated
        def get(self):
            self.finish(self.get_current_user())

    # start hub-authenticated service in a thread:
    port = 50505
    q = Queue()
    def run():
        app = Application([
            ('/*', TestHandler),
        ], login_url=auth.login_url)

        http_server = HTTPServer(app)
        http_server.listen(port)
        loop = IOLoop.current()
        loop.add_callback(lambda : q.put(loop))
        loop.start()

    t = Thread(target=run)
    t.start()

    def finish_thread():
        loop.stop()
        t.join()
    request.addfinalizer(finish_thread)

    # wait for thread to start
    loop = q.get(timeout=10)

    with requests_mock.Mocker(real_http=True) as m:
        # no cookie
        r = requests.get('http://127.0.0.1:%i' % port,
            allow_redirects=False,
        )
        r.raise_for_status()
        assert r.status_code == 302
        assert auth.login_url in r.headers['Location']
        
        # wrong cookie
        m.get(bad_url, status_code=404)
        r = requests.get('http://127.0.0.1:%i' % port,
            cookies={'jubal': 'late'},
            allow_redirects=False,
        )
        r.raise_for_status()
        assert r.status_code == 302
        assert auth.login_url in r.headers['Location']

        # upstream 403
        m.get(bad_url, status_code=403)
        r = requests.get('http://127.0.0.1:%i' % port,
            cookies={'jubal': 'late'},
            allow_redirects=False,
        )
        assert r.status_code == 500

        m.get(good_url, text=json.dumps(mock_model))

        # no whitelist
        r = requests.get('http://127.0.0.1:%i' % port,
            cookies={'jubal': 'early'},
            allow_redirects=False,
        )
        r.raise_for_status()
        assert r.status_code == 200

        # pass whitelist
        TestHandler.hub_users = {'jubalearly'}
        r = requests.get('http://127.0.0.1:%i' % port,
            cookies={'jubal': 'early'},
            allow_redirects=False,
        )
        r.raise_for_status()
        assert r.status_code == 200

        # no pass whitelist
        TestHandler.hub_users = {'kaylee'}
        r = requests.get('http://127.0.0.1:%i' % port,
            cookies={'jubal': 'early'},
            allow_redirects=False,
        )
        assert r.status_code == 403
        
        # pass group whitelist
        TestHandler.hub_groups = {'lions'}
        r = requests.get('http://127.0.0.1:%i' % port,
            cookies={'jubal': 'early'},
            allow_redirects=False,
        )
        r.raise_for_status()
        assert r.status_code == 200

        # no pass group whitelist
        TestHandler.hub_groups = {'tigers'}
        r = requests.get('http://127.0.0.1:%i' % port,
            cookies={'jubal': 'early'},
            allow_redirects=False,
        )
        assert r.status_code == 403


@pytest.mark.gen_test
def test_hubauth_cookie(app, mockservice_url):
    """Test HubAuthenticated service with user cookies"""
    cookies = yield app.login_user('badger')
    r = yield async_requests.get(public_url(app, mockservice_url) + '/whoami/', cookies=cookies)
    r.raise_for_status()
    print(r.text)
    reply = r.json()
    sub_reply = { key: reply.get(key, 'missing') for key in ['name', 'admin']}
    assert sub_reply == {
        'name': 'badger',
        'admin': False,
    }


@pytest.mark.gen_test
def test_hubauth_token(app, mockservice_url):
    """Test HubAuthenticated service with user API tokens"""
    u = add_user(app.db, name='river')
    token = u.new_api_token()
    app.db.commit()

    # token in Authorization header
    r = yield async_requests.get(public_url(app, mockservice_url) + '/whoami/',
        headers={
            'Authorization': 'token %s' % token,
        })
    reply = r.json()
    sub_reply = { key: reply.get(key, 'missing') for key in ['name', 'admin']}
    assert sub_reply == {
        'name': 'river',
        'admin': False,
    }

    # token in ?token parameter
    r = yield async_requests.get(public_url(app, mockservice_url) + '/whoami/?token=%s' % token)
    r.raise_for_status()
    reply = r.json()
    sub_reply = { key: reply.get(key, 'missing') for key in ['name', 'admin']}
    assert sub_reply == {
        'name': 'river',
        'admin': False,
    }

    r = yield async_requests.get(public_url(app, mockservice_url) + '/whoami/?token=no-such-token',
        allow_redirects=False,
    )
    assert r.status_code == 302
    assert 'Location' in r.headers
    location = r.headers['Location']
    path = urlparse(location).path
    assert path.endswith('/hub/login')


@pytest.mark.gen_test
def test_hubauth_service_token(app, mockservice_url):
    """Test HubAuthenticated service with service API tokens"""
    
    token = hexlify(os.urandom(5)).decode('utf8')
    name = 'test-api-service'
    app.service_tokens[token] = name
    yield app.init_api_tokens()

    # token in Authorization header
    r = yield async_requests.get(public_url(app, mockservice_url) + '/whoami/',
        headers={
            'Authorization': 'token %s' % token,
        })
    r.raise_for_status()
    reply = r.json()
    assert reply == {
        'kind': 'service',
        'name': name,
        'admin': False,
    }
    assert not r.cookies

    # token in ?token parameter
    r = yield async_requests.get(public_url(app, mockservice_url) + '/whoami/?token=%s' % token)
    r.raise_for_status()
    reply = r.json()
    assert reply == {
        'kind': 'service',
        'name': name,
        'admin': False,
    }

    r = yield async_requests.get(public_url(app, mockservice_url) + '/whoami/?token=no-such-token',
        allow_redirects=False,
    )
    assert r.status_code == 302
    assert 'Location' in r.headers
    location = r.headers['Location']
    path = urlparse(location).path
    assert path.endswith('/hub/login')


@pytest.mark.gen_test
def test_oauth_service(app, mockservice_url):
    service = mockservice_url
    url = url_path_join(public_url(app, mockservice_url) + 'owhoami/?arg=x')
    # first request is only going to set login cookie
    # FIXME: redirect to originating URL (OAuth loses this info)
    s = requests.Session()
    name = 'link'
    s.cookies = yield app.login_user(name)
    # run session.get in async_requests thread
    s_get = lambda *args, **kwargs: async_requests.executor.submit(s.get, *args, **kwargs)
    r = yield s_get(url)
    r.raise_for_status()
    assert r.url == url
    # verify oauth cookie is set
    assert 'service-%s' % service.name in set(s.cookies.keys())
    # verify oauth state cookie has been consumed
    assert 'service-%s-oauth-state' % service.name not in set(s.cookies.keys())
    # verify oauth state cookie was set at some point
    assert set(r.history[0].cookies.keys()) == {'service-%s-oauth-state' % service.name}

    # second request should be authenticated
    r = yield s_get(url, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 200
    reply = r.json()
    sub_reply = { key:reply.get(key, 'missing') for key in ('kind', 'name') }
    assert sub_reply == {
        'name': 'link',
        'kind': 'user',
    }

    # token-authenticated request to HubOAuth
    token = app.users[name].new_api_token()
    # token in ?token parameter
    r = yield async_requests.get(url_concat(url, {'token': token}))
    r.raise_for_status()
    reply = r.json()
    assert reply['name'] == name

    # verify that ?token= requests set a cookie
    assert len(r.cookies) != 0
    # ensure cookie works in future requests
    r = yield async_requests.get(
        url,
        cookies=r.cookies,
        allow_redirects=False,
    )
    r.raise_for_status()
    assert r.url == url
    reply = r.json()
    assert reply['name'] == name

