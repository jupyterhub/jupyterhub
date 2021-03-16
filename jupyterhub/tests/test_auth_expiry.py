"""
test authentication expiry

authentication can expire in a number of ways:

- needs refresh and can be refreshed
- doesn't need refresh
- needs refresh and cannot be refreshed without new login
"""
from contextlib import contextmanager
from unittest import mock
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest

from .utils import api_request
from .utils import get_page


async def refresh_expired(authenticator, user):
    return None


@pytest.fixture
def disable_refresh(app):
    """Fixture disabling auth refresh"""
    with mock.patch.object(app.authenticator, 'refresh_user', refresh_expired):
        yield


@pytest.fixture
def refresh_pre_spawn(app):
    """Fixture enabling auth refresh pre spawn"""
    app.authenticator.refresh_pre_spawn = True
    try:
        yield
    finally:
        app.authenticator.refresh_pre_spawn = False


async def test_auth_refresh_at_login(app, user):
    # auth_refreshed starts unset:
    assert not user._auth_refreshed
    # login sets auth_refreshed timestamp
    await app.login_user(user.name)
    assert user._auth_refreshed
    user._auth_refreshed -= 10
    before = user._auth_refreshed
    # login again updates auth_refreshed timestamp
    # even when auth is fresh
    await app.login_user(user.name)
    assert user._auth_refreshed > before


async def test_auth_refresh_page(app, user):
    cookies = await app.login_user(user.name)
    assert user._auth_refreshed
    user._auth_refreshed -= 10
    before = user._auth_refreshed

    # get a page with auth not expired
    # doesn't trigger refresh
    r = await get_page('home', app, cookies=cookies)
    assert r.status_code == 200
    assert user._auth_refreshed == before

    # get a page with stale auth, refreshes auth
    user._auth_refreshed -= app.authenticator.auth_refresh_age
    r = await get_page('home', app, cookies=cookies)
    assert r.status_code == 200
    assert user._auth_refreshed > before


async def test_auth_expired_page(app, user, disable_refresh):
    cookies = await app.login_user(user.name)
    assert user._auth_refreshed
    user._auth_refreshed -= 10
    before = user._auth_refreshed

    # auth is fresh, doesn't trigger expiry
    r = await get_page('home', app, cookies=cookies)
    assert user._auth_refreshed == before
    assert r.status_code == 200

    # get a page with stale auth, triggers expiry
    user._auth_refreshed -= app.authenticator.auth_refresh_age
    before = user._auth_refreshed
    r = await get_page('home', app, cookies=cookies, allow_redirects=False)

    # verify that we redirect to login with ?next=requested page
    assert r.status_code == 302
    redirect_url = urlparse(r.headers['Location'])
    assert redirect_url.path.endswith('/login')
    query = parse_qs(redirect_url.query)
    assert query['next']
    next_url = urlparse(query['next'][0])
    assert next_url.path == urlparse(r.url).path

    # make sure refresh didn't get updated
    assert user._auth_refreshed == before


async def test_auth_expired_api(app, user, disable_refresh):
    cookies = await app.login_user(user.name)
    assert user._auth_refreshed
    user._auth_refreshed -= 10
    before = user._auth_refreshed

    # auth is fresh, doesn't trigger expiry
    r = await api_request(app, 'users/' + user.name, name=user.name)
    assert user._auth_refreshed == before
    assert r.status_code == 200

    # get a page with stale auth, triggers expiry
    user._auth_refreshed -= app.authenticator.auth_refresh_age
    r = await api_request(app, 'users/' + user.name, name=user.name)
    # api requests can't do login redirects
    assert r.status_code == 403


async def test_refresh_pre_spawn(app, user, refresh_pre_spawn):
    cookies = await app.login_user(user.name)
    assert user._auth_refreshed
    user._auth_refreshed -= 10
    before = user._auth_refreshed

    # auth is fresh, but should be forced to refresh by spawn
    r = await api_request(
        app, 'users/{}/server'.format(user.name), method='post', name=user.name
    )
    assert 200 <= r.status_code < 300
    assert user._auth_refreshed > before


async def test_refresh_pre_spawn_expired(app, user, refresh_pre_spawn, disable_refresh):
    cookies = await app.login_user(user.name)
    assert user._auth_refreshed
    user._auth_refreshed -= 10
    before = user._auth_refreshed

    # auth is fresh, doesn't trigger expiry
    r = await api_request(
        app, 'users/{}/server'.format(user.name), method='post', name=user.name
    )
    assert r.status_code == 403
    assert user._auth_refreshed == before


async def test_refresh_pre_spawn_admin_request(
    app, user, admin_user, refresh_pre_spawn
):
    await app.login_user(user.name)
    await app.login_user(admin_user.name)
    user._auth_refreshed -= 10
    before = user._auth_refreshed

    # admin request, auth is fresh. Should still refresh user auth.
    r = await api_request(
        app, 'users', user.name, 'server', method='post', name=admin_user.name
    )
    assert 200 <= r.status_code < 300
    assert user._auth_refreshed > before


async def test_refresh_pre_spawn_expired_admin_request(
    app, user, admin_user, refresh_pre_spawn, disable_refresh
):
    await app.login_user(user.name)
    await app.login_user(admin_user.name)
    user._auth_refreshed -= 10

    # auth needs refresh but can't without a new login; spawn should fail
    user._auth_refreshed -= app.authenticator.auth_refresh_age
    r = await api_request(
        app, 'users', user.name, 'server', method='post', name=admin_user.name
    )
    # api requests can't do login redirects
    assert r.status_code == 403
