"""Tests for service authentication"""
import asyncio
import copy
import json
import os
import sys
from binascii import hexlify
from functools import partial
from queue import Queue
from threading import Thread
from unittest import mock
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest
import requests
import requests_mock
from pytest import raises
from tornado.httpserver import HTTPServer
from tornado.httputil import url_concat
from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.web import authenticated
from tornado.web import HTTPError
from tornado.web import RequestHandler

from .. import orm
from ..services.auth import _ExpiringDict
from ..services.auth import HubOAuth
from ..services.auth import HubOAuthenticated
from ..utils import url_path_join
from .mocking import public_host
from .mocking import public_url
from .test_api import add_user
from .utils import async_requests
from .utils import AsyncSession

# mock for sending monotonic counter way into the future
monotonic_future = mock.patch('time.monotonic', lambda: sys.maxsize)
ssl_enabled = False


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


async def test_hubauth_token(app, mockservice_url):
    """Test HubAuthenticated service with user API tokens"""
    u = add_user(app.db, name='river')
    token = u.new_api_token()
    app.db.commit()

    # token in Authorization header
    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/',
        headers={'Authorization': 'token %s' % token},
    )
    reply = r.json()
    sub_reply = {key: reply.get(key, 'missing') for key in ['name', 'admin']}
    assert sub_reply == {'name': 'river', 'admin': False}

    # token in ?token parameter
    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/?token=%s' % token
    )
    r.raise_for_status()
    reply = r.json()
    sub_reply = {key: reply.get(key, 'missing') for key in ['name', 'admin']}
    assert sub_reply == {'name': 'river', 'admin': False}

    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/?token=no-such-token',
        allow_redirects=False,
    )
    assert r.status_code == 302
    assert 'Location' in r.headers
    location = r.headers['Location']
    path = urlparse(location).path
    assert path.endswith('/hub/login')


async def test_hubauth_service_token(app, mockservice_url):
    """Test HubAuthenticated service with service API tokens"""

    token = hexlify(os.urandom(5)).decode('utf8')
    name = 'test-api-service'
    app.service_tokens[token] = name
    await app.init_api_tokens()

    # token in Authorization header
    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/',
        headers={'Authorization': 'token %s' % token},
        allow_redirects=False,
    )
    r.raise_for_status()
    assert r.status_code == 200
    reply = r.json()
    assert reply == {'kind': 'service', 'name': name, 'admin': False, 'roles': []}
    assert not r.cookies

    # token in ?token parameter
    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/?token=%s' % token
    )
    r.raise_for_status()
    reply = r.json()
    assert reply == {'kind': 'service', 'name': name, 'admin': False, 'roles': []}

    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/?token=no-such-token',
        allow_redirects=False,
    )
    assert r.status_code == 302
    assert 'Location' in r.headers
    location = r.headers['Location']
    path = urlparse(location).path
    assert path.endswith('/hub/login')


@pytest.mark.parametrize(
    "client_allowed_roles, request_roles, expected_roles",
    [
        # allow empty roles
        ([], [], []),
        # allow original 'identify' scope to map to no role
        ([], ["identify"], []),
        # requesting roles outside client list doesn't work
        ([], ["admin"], None),
        ([], ["token"], None),
        # requesting nonexistent roles fails in the same way (no server error)
        ([], ["nosuchrole"], None),
        # requesting exactly client allow list works
        (["user"], ["user"], ["user"]),
        # no explicit request, defaults to all
        (["token", "user"], [], ["token", "user"]),
        # explicit 'identify' maps to none
        (["token", "user"], ["identify"], []),
        # any item outside the list isn't allowed
        (["token", "user"], ["token", "server"], None),
        # reuesting subset
        (["admin", "user"], ["user"], ["user"]),
        (["user", "token", "server"], ["token", "user"], ["token", "user"]),
    ],
)
async def test_oauth_service(
    app,
    mockservice_url,
    client_allowed_roles,
    request_roles,
    expected_roles,
):
    service = mockservice_url
    oauth_client = (
        app.db.query(orm.OAuthClient)
        .filter_by(identifier=service.oauth_client_id)
        .one()
    )
    oauth_client.allowed_roles = [
        orm.Role.find(app.db, role_name) for role_name in client_allowed_roles
    ]
    app.db.commit()
    url = url_path_join(public_url(app, mockservice_url) + 'owhoami/?arg=x')
    # first request is only going to login and get us to the oauth form page
    s = AsyncSession()
    name = 'link'
    s.cookies = await app.login_user(name)

    r = await s.get(url)
    r.raise_for_status()
    # we should be looking at the oauth confirmation page
    assert urlparse(r.url).path == app.base_url + 'hub/api/oauth2/authorize'
    # verify oauth state cookie was set at some point
    assert set(r.history[0].cookies.keys()) == {'service-%s-oauth-state' % service.name}

    # submit the oauth form to complete authorization
    data = {}
    if request_roles:
        data["scopes"] = request_roles
    r = await s.post(r.url, data=data, headers={'Referer': r.url})
    if expected_roles is None:
        # expected failed auth, stop here
        # verify expected 'invalid scope' error, not server error
        dest_url, _, query = r.url.partition("?")
        assert dest_url == public_url(app, mockservice_url) + "oauth_callback"
        assert parse_qs(query).get("error") == ["invalid_scope"]
        assert r.status_code == 400
        return
    r.raise_for_status()
    assert r.url == url
    # verify oauth cookie is set
    assert 'service-%s' % service.name in set(s.cookies.keys())
    # verify oauth state cookie has been consumed
    assert 'service-%s-oauth-state' % service.name not in set(s.cookies.keys())

    # second request should be authenticated, which means no redirects
    r = await s.get(url, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 200
    reply = r.json()
    sub_reply = {key: reply.get(key, 'missing') for key in ('kind', 'name')}
    assert sub_reply == {'name': 'link', 'kind': 'user'}

    # token-authenticated request to HubOAuth
    token = app.users[name].new_api_token()
    # token in ?token parameter
    r = await async_requests.get(url_concat(url, {'token': token}))
    r.raise_for_status()
    reply = r.json()
    assert reply['name'] == name

    # verify that ?token= requests set a cookie
    assert len(r.cookies) != 0
    # ensure cookie works in future requests
    r = await async_requests.get(url, cookies=r.cookies, allow_redirects=False)
    r.raise_for_status()
    assert r.url == url
    reply = r.json()
    assert reply['name'] == name


async def test_oauth_cookie_collision(app, mockservice_url):
    service = mockservice_url
    url = url_path_join(public_url(app, mockservice_url), 'owhoami/')
    print(url)
    s = AsyncSession()
    name = 'mypha'
    s.cookies = await app.login_user(name)
    state_cookie_name = 'service-%s-oauth-state' % service.name
    service_cookie_name = 'service-%s' % service.name
    oauth_1 = await s.get(url)
    print(oauth_1.headers)
    print(oauth_1.cookies, oauth_1.url, url)
    assert state_cookie_name in s.cookies
    state_cookies = [c for c in s.cookies.keys() if c.startswith(state_cookie_name)]
    # only one state cookie
    assert state_cookies == [state_cookie_name]
    state_1 = s.cookies[state_cookie_name]

    # start second oauth login before finishing the first
    oauth_2 = await s.get(url)
    state_cookies = [c for c in s.cookies.keys() if c.startswith(state_cookie_name)]
    assert len(state_cookies) == 2
    # get the random-suffix cookie name
    state_cookie_2 = sorted(state_cookies)[-1]
    # we didn't clobber the default cookie
    assert s.cookies[state_cookie_name] == state_1

    # finish oauth 2
    # submit the oauth form to complete authorization
    r = await s.post(
        oauth_2.url, data={'scopes': ['identify']}, headers={'Referer': oauth_2.url}
    )
    r.raise_for_status()
    assert r.url == url
    # after finishing, state cookie is cleared
    assert state_cookie_2 not in s.cookies
    # service login cookie is set
    assert service_cookie_name in s.cookies
    service_cookie_2 = s.cookies[service_cookie_name]

    # finish oauth 1
    r = await s.post(
        oauth_1.url, data={'scopes': ['identify']}, headers={'Referer': oauth_1.url}
    )
    r.raise_for_status()
    assert r.url == url

    # after finishing, state cookie is cleared (again)
    assert state_cookie_name not in s.cookies
    # service login cookie is set (again, to a different value)
    assert service_cookie_name in s.cookies
    assert s.cookies[service_cookie_name] != service_cookie_2

    # after completing both OAuth logins, no OAuth state cookies remain
    state_cookies = [s for s in s.cookies.keys() if s.startswith(state_cookie_name)]
    assert state_cookies == []


async def test_oauth_logout(app, mockservice_url):
    """Verify that logout via the Hub triggers logout for oauth services

    1. clears session id cookie
    2. revokes oauth tokens
    3. cleared session id ensures cached auth miss
    4. cache hit
    """
    service = mockservice_url
    service_cookie_name = 'service-%s' % service.name
    url = url_path_join(public_url(app, mockservice_url), 'owhoami/?foo=bar')
    # first request is only going to set login cookie
    s = AsyncSession()
    name = 'propha'
    app_user = add_user(app.db, app=app, name=name)

    def auth_tokens():
        """Return list of OAuth access tokens for the user"""
        return list(app.db.query(orm.APIToken).filter_by(user_id=app_user.id))

    # ensure we start empty
    assert auth_tokens() == []

    s.cookies = await app.login_user(name)
    assert 'jupyterhub-session-id' in s.cookies
    r = await s.get(url)
    r.raise_for_status()
    assert urlparse(r.url).path.endswith('oauth2/authorize')
    # submit the oauth form to complete authorization
    r = await s.post(r.url, data={'scopes': ['identify']}, headers={'Referer': r.url})
    r.raise_for_status()
    assert r.url == url

    # second request should be authenticated
    r = await s.get(url, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 200
    reply = r.json()
    sub_reply = {key: reply.get(key, 'missing') for key in ('kind', 'name')}
    assert sub_reply == {'name': name, 'kind': 'user'}
    # save cookies to verify cache
    saved_cookies = copy.deepcopy(s.cookies)
    session_id = s.cookies['jupyterhub-session-id']

    assert len(auth_tokens()) == 1
    token = auth_tokens()[0]
    assert token.expires_in is not None
    # verify that oauth_token_expires_in has its desired effect
    assert abs(app.oauth_token_expires_in - token.expires_in) < 30

    # hit hub logout URL
    r = await s.get(public_url(app, path='hub/logout'))
    r.raise_for_status()
    # verify that all cookies other than the service cookie are cleared
    assert list(s.cookies.keys()) == [service_cookie_name]
    # verify that clearing session id invalidates service cookie
    # i.e. redirect back to login page
    r = await s.get(url)
    r.raise_for_status()
    assert r.url.split('?')[0] == public_url(app, path='hub/login')

    # verify that oauth tokens have been revoked
    assert auth_tokens() == []

    # double check that if we hadn't cleared session id
    # login would have been cached.
    # it's not important that the old login is still cached,
    # but what is important is that the above logout was successful
    # due to session-id causing a cache miss
    # and not a failure to cache auth at all.
    s.cookies = saved_cookies
    # check that we got the old session id back
    assert session_id == s.cookies['jupyterhub-session-id']

    r = await s.get(url, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 200
    reply = r.json()
    sub_reply = {key: reply.get(key, 'missing') for key in ('kind', 'name')}
    assert sub_reply == {'name': name, 'kind': 'user'}
