"""Tests for service authentication"""
import copy
import os
import sys
from binascii import hexlify
from unittest import mock
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest
from pytest import raises
from tornado.httputil import url_concat

from .. import orm
from .. import roles
from ..services.auth import _ExpiringDict
from ..utils import url_path_join
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


async def test_hubauth_token(app, mockservice_url, create_user_with_scopes):
    """Test HubAuthenticated service with user API tokens"""
    u = create_user_with_scopes("access:services")
    token = u.new_api_token()
    no_access_token = u.new_api_token(roles=[])
    app.db.commit()

    # token without sufficient permission in Authorization header
    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/',
        headers={'Authorization': f'token {no_access_token}'},
    )
    assert r.status_code == 403

    # token in Authorization header
    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/',
        headers={'Authorization': f'token {token}'},
    )
    r.raise_for_status()
    reply = r.json()
    sub_reply = {key: reply.get(key, 'missing') for key in ['name', 'admin']}
    assert sub_reply == {'name': u.name, 'admin': False}

    # token in ?token parameter
    r = await async_requests.get(
        public_url(app, mockservice_url) + '/whoami/?token=%s' % token
    )
    r.raise_for_status()
    reply = r.json()
    sub_reply = {key: reply.get(key, 'missing') for key in ['name', 'admin']}
    assert sub_reply == {'name': u.name, 'admin': False}

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
    "scopes, allowed",
    [
        (
            [
                "access:services",
            ],
            True,
        ),
        (
            [
                "access:services!service=$service",
            ],
            True,
        ),
        (
            [
                "access:services!service=other-service",
            ],
            False,
        ),
        (
            [
                "access:servers!user=$service",
            ],
            False,
        ),
    ],
)
async def test_hubauth_service_token(request, app, mockservice_url, scopes, allowed):
    """Test HubAuthenticated service with service API tokens"""

    scopes = [scope.replace('$service', mockservice_url.name) for scope in scopes]

    token = hexlify(os.urandom(5)).decode('utf8')
    name = 'test-api-service'
    app.service_tokens[token] = name
    await app.init_api_tokens()

    orm_service = app.db.query(orm.Service).filter_by(name=name).one()
    role_name = "test-hubauth-service-token"

    roles.create_role(
        app.db,
        {
            "name": role_name,
            "description": "role for test",
            "scopes": scopes,
        },
    )
    request.addfinalizer(lambda: roles.delete_role(app.db, role_name))
    roles.grant_role(app.db, orm_service, role_name)

    # token in Authorization header
    r = await async_requests.get(
        public_url(app, mockservice_url) + 'whoami/',
        headers={'Authorization': 'token %s' % token},
        allow_redirects=False,
    )
    service_model = {
        'kind': 'service',
        'name': name,
        'admin': False,
        'scopes': scopes,
    }
    if allowed:
        r.raise_for_status()
        assert r.status_code == 200
        reply = r.json()
        assert service_model.items() <= reply.items()
        assert not r.cookies
    else:
        assert r.status_code == 403

    # token in ?token parameter
    r = await async_requests.get(
        public_url(app, mockservice_url) + 'whoami/?token=%s' % token
    )
    if allowed:
        r.raise_for_status()
        assert r.status_code == 200
        reply = r.json()
        assert service_model.items() <= reply.items()
        assert not r.cookies
    else:
        assert r.status_code == 403

    r = await async_requests.get(
        public_url(app, mockservice_url) + 'whoami/?token=no-such-token',
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
        # requesting subset
        (["admin", "user"], ["user"], ["user"]),
        (["user", "token", "server"], ["token", "user"], ["token", "user"]),
    ],
)
async def test_oauth_service_roles(
    app,
    mockservice_url,
    create_user_with_scopes,
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
    user = create_user_with_scopes("access:services")
    roles.grant_role(app.db, user, "user")
    name = user.name
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
    assert sub_reply == {'name': user.name, 'kind': 'user'}

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


@pytest.mark.parametrize(
    "access_scopes, expect_success",
    [
        (["access:services"], True),
        (["access:services!service=$service"], True),
        (["access:services!service=other-service"], False),
        (["self"], False),
        ([], False),
    ],
)
async def test_oauth_access_scopes(
    app,
    mockservice_url,
    create_user_with_scopes,
    access_scopes,
    expect_success,
):
    """Check that oauth/authorize validates access scopes"""
    service = mockservice_url
    access_scopes = [s.replace("$service", service.name) for s in access_scopes]
    url = url_path_join(public_url(app, mockservice_url) + 'owhoami/?arg=x')
    # first request is only going to login and get us to the oauth form page
    s = AsyncSession()
    user = create_user_with_scopes(*access_scopes)
    name = user.name
    s.cookies = await app.login_user(name)

    r = await s.get(url)
    if not expect_success:
        assert r.status_code == 403
        return
    r.raise_for_status()
    # we should be looking at the oauth confirmation page
    assert urlparse(r.url).path == app.base_url + 'hub/api/oauth2/authorize'
    # verify oauth state cookie was set at some point
    assert set(r.history[0].cookies.keys()) == {'service-%s-oauth-state' % service.name}

    # submit the oauth form to complete authorization
    r = await s.post(r.url, headers={'Referer': r.url})
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
    assert sub_reply == {'name': name, 'kind': 'user'}

    # revoke user access, should result in 403
    user.roles = []
    app.db.commit()

    # reset session id to avoid cached response
    s.cookies.pop('jupyterhub-session-id')

    r = await s.get(url, allow_redirects=False)
    assert r.status_code == 403


@pytest.mark.parametrize(
    "token_roles, hits_page",
    [([], True), (['writer'], True), (['writer', 'reader'], False)],
)
async def test_oauth_page_hit(
    app,
    mockservice_url,
    create_user_with_scopes,
    create_temp_role,
    token_roles,
    hits_page,
):
    test_roles = {
        'reader': create_temp_role(['read:users'], role_name='reader'),
        'writer': create_temp_role(['users:activity'], role_name='writer'),
    }
    service = mockservice_url
    user = create_user_with_scopes("access:services", "self")
    user.new_api_token()
    token = user.api_tokens[0]
    token.roles = [test_roles[t] for t in token_roles]

    oauth_client = (
        app.db.query(orm.OAuthClient)
        .filter_by(identifier=service.oauth_client_id)
        .one()
    )
    oauth_client.allowed_roles = list(test_roles.values())
    token.client_id = service.oauth_client_id
    app.db.commit()
    s = AsyncSession()
    s.cookies = await app.login_user(user.name)
    url = url_path_join(public_url(app, service) + 'owhoami/?arg=x')
    r = await s.get(url)
    r.raise_for_status()
    if hits_page:
        # hit auth page to confirm permissions
        assert urlparse(r.url).path == app.base_url + 'hub/api/oauth2/authorize'
    else:
        # skip auth page, permissions are granted
        assert r.status_code == 200
        assert r.url == url


async def test_oauth_cookie_collision(app, mockservice_url, create_user_with_scopes):
    service = mockservice_url
    url = url_path_join(public_url(app, mockservice_url), 'owhoami/')
    print(url)
    s = AsyncSession()
    name = 'mypha'
    user = create_user_with_scopes("access:services", name=name)
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


async def test_oauth_logout(app, mockservice_url, create_user_with_scopes):
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
    user = create_user_with_scopes("access:services", name=name)

    def auth_tokens():
        """Return list of OAuth access tokens for the user"""
        return list(app.db.query(orm.APIToken).filter_by(user_id=user.id))

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
