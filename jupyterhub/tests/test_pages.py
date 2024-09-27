"""Tests for HTML pages"""

import asyncio
import sys
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from bs4 import BeautifulSoup
from tornado.httputil import url_concat

from .. import orm, roles, scopes
from ..auth import Authenticator
from ..handlers import BaseHandler
from ..utils import url_path_join
from ..utils import url_path_join as ujoin
from .mocking import FalsyCallableFormSpawner, FormSpawner
from .test_api import next_event
from .utils import (
    AsyncSession,
    api_request,
    async_requests,
    get_page,
    public_host,
    public_url,
)


async def test_root_no_auth(app):
    url = ujoin(public_host(app), app.hub.base_url)
    r = await async_requests.get(url)
    r.raise_for_status()
    assert r.url == url_concat(ujoin(url, 'login'), dict(next=app.hub.base_url))


async def test_root_auth(app):
    cookies = await app.login_user('river')
    r = await async_requests.get(public_url(app), cookies=cookies)
    r.raise_for_status()
    assert r.history
    history = [_.url for _ in r.history] + [r.url]
    assert history[1] == ujoin(public_url(app), "hub/")
    assert history[2] == ujoin(public_url(app), "hub/spawn")
    assert history[3] == ujoin(public_url(app), "hub/spawn-pending/river")
    # if spawning was quick, there will be one more entry that's public_url(user)


async def test_root_redirect(app, user):
    name = 'wash'
    cookies = await app.login_user(name)
    next_url = ujoin(app.base_url, f'user/{user.name}/test.ipynb')
    url = '/?' + urlencode({'next': next_url})
    r = await get_page(url, app, cookies=cookies)
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, f'hub/user/{user.name}/test.ipynb')
    # preserves choice to requested user, which 404s as unavailable without access
    assert r.status_code == 404


async def test_root_default_url_noauth(app):
    with mock.patch.dict(app.tornado_settings, {'default_url': '/foo/bar'}):
        r = await get_page('/', app, allow_redirects=False)
    r.raise_for_status()
    url = r.headers.get('Location', '')
    path = urlparse(url).path
    assert path == '/foo/bar'


async def test_root_default_url_auth(app):
    name = 'wash'
    cookies = await app.login_user(name)
    with mock.patch.dict(app.tornado_settings, {'default_url': '/foo/bar'}):
        r = await get_page('/', app, cookies=cookies, allow_redirects=False)
    r.raise_for_status()
    url = r.headers.get('Location', '')
    path = urlparse(url).path
    assert path == '/foo/bar'


async def test_home_no_auth(app):
    r = await get_page('home', app, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 302
    assert '/hub/login' in r.headers['Location']


async def test_home_auth(app):
    cookies = await app.login_user('river')
    r = await get_page('home', app, cookies=cookies)
    r.raise_for_status()
    assert r.url.endswith('home')


async def test_admin_no_auth(app):
    r = await get_page('admin', app, allow_redirects=False)
    assert r.status_code == 302
    assert '/hub/login' in r.headers['Location']


async def test_admin_not_admin(app):
    cookies = await app.login_user('wash')
    r = await get_page('admin', app, cookies=cookies)
    assert r.status_code == 403


async def test_admin(app):
    cookies = await app.login_user('admin')
    r = await get_page('admin', app, cookies=cookies, allow_redirects=False)
    r.raise_for_status()
    assert r.url.endswith('/admin')


async def test_admin_version(app):
    cookies = await app.login_user('admin')
    r = await get_page('admin', app, cookies=cookies, allow_redirects=False)
    r.raise_for_status()
    assert "version_footer" in r.text


@pytest.mark.parametrize('sort', ['running', 'last_activity', 'admin', 'name'])
async def test_admin_sort(app, sort):
    cookies = await app.login_user('admin')
    r = await get_page(f'admin?sort={sort}', app, cookies=cookies)
    r.raise_for_status()
    assert r.status_code == 200


@pytest.mark.parametrize("last_failed", [True, False])
async def test_spawn_redirect(app, last_failed):
    name = 'wash'
    cookies = await app.login_user(name)
    u = app.users[orm.User.find(app.db, name)]

    if last_failed:
        # mock a failed spawn
        last_spawner = u.spawners['']
        last_spawner._spawn_future = asyncio.Future()
        last_spawner._spawn_future.set_exception(RuntimeError("I failed!"))
    else:
        last_spawner = None

    status = await u.spawner.poll()
    assert status is not None

    # test spawn page when no server is running
    r = await get_page('spawn', app, cookies=cookies)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path

    # ensure we got a new spawner
    assert u.spawners[''] is not last_spawner

    # make sure we visited hub/spawn-pending after spawn
    # if spawn was really quick, we might get redirected all the way to the running server,
    # so check history instead of r.url
    history = [urlparse(_.url).path for _ in r.history]
    history.append(path)
    assert ujoin(app.base_url, 'hub/spawn-pending', name) in history

    # should have started server
    status = await u.spawner.poll()
    assert status is None
    # wait for ready signal before checking next redirect
    while not u.spawner.ready:
        await asyncio.sleep(0.1)

    # test spawn page when server is already running (just redirect)
    r = await get_page('spawn', app, cookies=cookies)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, f'/user/{name}/')

    # stop server to ensure /user/name is handled by the Hub
    r = await api_request(
        app, 'users', name, 'server', method='delete', cookies=cookies
    )
    r.raise_for_status()

    # test handing of trailing slash on `/user/name`
    r = await get_page('user/' + name, app, hub=False, cookies=cookies)
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, f'hub/user/{name}/')
    assert r.status_code == 424


async def test_spawn_handler_access(app):
    name = 'winston'
    cookies = await app.login_user(name)
    u = app.users[orm.User.find(app.db, name)]

    status = await u.spawner.poll()
    assert status is not None

    # spawn server via browser link with ?arg=value
    r = await get_page('spawn', app, cookies=cookies, params={'arg': 'value'})
    r.raise_for_status()
    # wait for spawn-pending to complete
    while not u.spawner.ready:
        await asyncio.sleep(0.1)
        assert u.spawner.active

    # verify that request params got passed down
    # implemented in MockSpawner
    r = await async_requests.get(ujoin(public_url(app, u), 'env'))
    env = r.json()
    assert 'HANDLER_ARGS' in env
    assert env['HANDLER_ARGS'] == 'arg=value'

    # stop server
    r = await api_request(app, 'users', name, 'server', method='delete')
    r.raise_for_status()


@pytest.mark.parametrize(
    "has_access", ["all", "user", (pytest.param("group", id="in-group")), False]
)
async def test_spawn_other_user(
    app, user, username, group, create_temp_role, has_access
):
    """GET /user/:name as another user with access to spawns user's server"""
    cookies = await app.login_user(username)
    requester = app.users[username]
    name = user.name
    assert username != user.name

    if has_access:
        if has_access == "group":
            group.users.append(user.orm_user)
            app.db.commit()
            scopes = [
                f"access:servers!group={group.name}",
                f"servers!group={group.name}",
            ]
            assert group in user.orm_user.groups
        elif has_access == "all":
            scopes = ["access:servers", "servers"]
        elif has_access == "user":
            scopes = [f"access:servers!user={user.name}", f"servers!user={user.name}"]
        role = create_temp_role(scopes)
        roles.grant_role(app.db, requester, role)

    r = await get_page('spawn/' + name, app, cookies=cookies)
    if not has_access:
        assert r.status_code == 404
        return
    r.raise_for_status()

    while '/spawn-pending/' in r.url:
        await asyncio.sleep(0.1)
        r = await async_requests.get(r.url, cookies=cookies)
        r.raise_for_status()

    assert (r.url.split('?')[0] + '/').startswith(public_url(app, user))
    r = await get_page(f'user/{name}/env', app, hub=False, cookies=cookies)

    r.raise_for_status()
    env = r.json()
    assert env['JUPYTERHUB_USER'] == name


async def test_spawn_page(app):
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        cookies = await app.login_user('jones')
        r = await get_page('spawn', app, cookies=cookies)
        assert r.url.endswith('/spawn')
        assert FormSpawner.options_form in r.text

        r = await get_page('spawn?next=foo', app, cookies=cookies)
        assert r.url.endswith('/spawn?next=foo')
        assert FormSpawner.options_form in r.text


async def test_spawn_page_after_failed(app, user):
    cookies = await app.login_user(user.name)

    # mock a failed spawn
    last_spawner = user.spawners['']
    last_spawner._spawn_future = asyncio.Future()
    last_spawner._spawn_future.set_exception(RuntimeError("I failed!"))

    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        r = await get_page('spawn', app, cookies=cookies)
        spawner = user.spawners['']
        # make sure we didn't reuse last spawner
        assert isinstance(spawner, FormSpawner)
        assert spawner is not last_spawner
        assert r.url.endswith('/spawn')
        spawner = user.spawners['']
        assert FormSpawner.options_form in r.text


async def test_spawn_page_falsy_callable(app):
    with mock.patch.dict(
        app.users.settings, {'spawner_class': FalsyCallableFormSpawner}
    ):
        cookies = await app.login_user('erik')
        r = await get_page('spawn', app, cookies=cookies)
    history = [_.url for _ in r.history] + [r.url]
    assert history[0] == ujoin(public_url(app), "hub/spawn")
    assert history[1] == ujoin(public_url(app), "hub/spawn-pending/erik")


@pytest.mark.parametrize(
    "has_access", ["all", "user", (pytest.param("group", id="in-group")), False]
)
async def test_spawn_page_access(
    app, has_access, group, username, user, create_temp_role
):
    cookies = await app.login_user(username)
    requester = app.users[username]
    if has_access:
        if has_access == "group":
            group.users.append(user.orm_user)
            app.db.commit()
            scopes = [
                f"access:servers!group={group.name}",
                f"servers!group={group.name}",
            ]
        elif has_access == "all":
            scopes = ["access:servers", "servers"]
        elif has_access == "user":
            scopes = [f"access:servers!user={user.name}", f"servers!user={user.name}"]
        role = create_temp_role(scopes)
        roles.grant_role(app.db, requester, role)

    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        r = await get_page('spawn/' + user.name, app, cookies=cookies)
        if not has_access:
            assert r.status_code == 404
            return
        assert r.status_code == 200
        assert r.url.endswith('/spawn/' + user.name)
        assert FormSpawner.options_form in r.text
        assert f"Spawning server for {user.name}" in r.text


async def test_spawn_with_query_arguments(app):
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        base_url = ujoin(public_host(app), app.hub.base_url)
        cookies = await app.login_user('jones')
        orm_u = orm.User.find(app.db, 'jones')
        u = app.users[orm_u]
        await u.stop()
        next_url = ujoin(app.base_url, 'user/jones/tree')
        r = await async_requests.get(
            url_concat(
                ujoin(base_url, 'spawn'),
                {'next': next_url, 'energy': '510keV'},
            ),
            cookies=cookies,
        )
        r.raise_for_status()
        assert r.history
        assert u.spawner.user_options == {
            'energy': '510keV',
            'notspecified': 5,
        }


async def test_spawn_with_query_arguments_error(app):
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        base_url = ujoin(public_host(app), app.hub.base_url)
        cookies = await app.login_user('jones')
        orm_u = orm.User.find(app.db, 'jones')
        u = app.users[orm_u]
        await u.stop()
        next_url = ujoin(app.base_url, 'user/jones/tree')
        r = await async_requests.get(
            url_concat(
                ujoin(base_url, 'spawn'),
                {'next': next_url, 'energy': '510keV', 'illegal_argument': '42'},
            ),
            cookies=cookies,
        )
        r.raise_for_status()
        assert "You are not allowed to specify " in r.text


async def test_spawn_form(app):
    with mock.patch.dict(app.users.settings, {'spawner_class': FormSpawner}):
        base_url = ujoin(public_host(app), app.hub.base_url)
        cookies = await app.login_user('jones')
        orm_u = orm.User.find(app.db, 'jones')
        u = app.users[orm_u]
        await u.stop()
        next_url = ujoin(app.base_url, 'user/jones/tree')
        r = await async_requests.get(
            url_concat(ujoin(base_url, 'spawn'), {'next': next_url}), cookies=cookies
        )
        r.raise_for_status()
        spawn_page = BeautifulSoup(r.text, 'html.parser')
        form = spawn_page.find("form")
        action_url = public_host(app) + form["action"]
        r = await async_requests.post(
            action_url,
            cookies=cookies,
            data={'bounds': ['-1', '1'], 'energy': '511keV'},
        )
        r.raise_for_status()
        assert r.history
        assert u.spawner.user_options == {
            'energy': '511keV',
            'bounds': [-1, 1],
            'notspecified': 5,
        }


@pytest.mark.parametrize(
    "has_access", ["all", "user", (pytest.param("group", id="in-group")), False]
)
async def test_spawn_form_other_user(
    app, username, user, group, create_temp_role, has_access
):
    cookies = await app.login_user(username)
    requester = app.users[username]
    if has_access:
        if has_access == "group":
            group.users.append(user.orm_user)
            app.db.commit()
            scopes = [
                f"access:servers!group={group.name}",
                f"servers!group={group.name}",
            ]
        elif has_access == "all":
            scopes = ["access:servers", "servers"]
        elif has_access == "user":
            scopes = [f"access:servers!user={user.name}", f"servers!user={user.name}"]
        role = create_temp_role(scopes)
        roles.grant_role(app.db, requester, role)

    with mock.patch.dict(app.tornado_settings, {'spawner_class': FormSpawner}):
        base_url = ujoin(public_host(app), app.hub.base_url)
        next_url = ujoin(app.base_url, 'user', user.name, 'tree')

        url = ujoin(base_url, 'spawn', user.name)
        r = await async_requests.get(
            url_concat(url, {'next': next_url}),
            cookies=cookies,
        )
        if has_access:
            r.raise_for_status()
            spawn_page = BeautifulSoup(r.text, 'html.parser')
            form = spawn_page.find("form")
            action_url = ujoin(public_host(app), form["action"])
        else:
            assert r.status_code == 404
            action_url = url_concat(url, {"_xsrf": cookies['_xsrf']})

        r = await async_requests.post(
            action_url,
            cookies=cookies,
            data={'bounds': ['-3', '3'], 'energy': '938MeV'},
        )
        if not has_access:
            assert r.status_code == 404
            return
        r.raise_for_status()

        while '/spawn-pending/' in r.url:
            await asyncio.sleep(0.1)
            r = await async_requests.get(r.url, cookies=cookies)
            r.raise_for_status()

        assert r.history
        assert r.url.startswith(public_url(app, user))
        assert user.spawner.user_options == {
            'energy': '938MeV',
            'bounds': [-3, 3],
            'notspecified': 5,
        }


async def test_spawn_form_with_file(app):
    with mock.patch.dict(app.tornado_settings, {'spawner_class': FormSpawner}):
        base_url = ujoin(public_host(app), app.hub.base_url)
        cookies = await app.login_user('jones')
        orm_u = orm.User.find(app.db, 'jones')
        u = app.users[orm_u]
        await u.stop()
        url = ujoin(base_url, 'spawn')

        r = await async_requests.get(
            url,
            cookies=cookies,
        )
        r.raise_for_status()
        spawn_page = BeautifulSoup(r.text, 'html.parser')
        form = spawn_page.find("form")
        action_url = public_host(app) + form["action"]

        r = await async_requests.post(
            action_url,
            cookies=cookies,
            data={'bounds': ['-1', '1'], 'energy': '511keV'},
            files={'hello': ('hello.txt', b'hello world\n')},
        )
        r.raise_for_status()
        assert u.spawner.user_options == {
            'energy': '511keV',
            'bounds': [-1, 1],
            'notspecified': 5,
            'hello': {
                'filename': 'hello.txt',
                'body': b'hello world\n',
                'content_type': 'application/unknown',
            },
        }


async def test_spawn_pending(app, username, slow_spawn):
    cookies = await app.login_user(username)
    # first request, no spawn is pending
    # spawn-pending shows button linking to spawn
    r = await get_page('/spawn-pending/' + username, app, cookies=cookies)
    r.raise_for_status()
    page = BeautifulSoup(r.text, "html.parser")
    assert "is not running" in page.body.text
    link = page.find("a", id="start")
    assert link
    assert link['href'] == ujoin(app.base_url, '/hub/spawn/', username)

    # request spawn
    next_url = ujoin(app.base_url, 'user', username, 'tree/foo')
    spawn_url = url_concat('/spawn/' + username, dict(next=next_url))
    r = await get_page(spawn_url, app, cookies=cookies)
    r.raise_for_status()
    url = urlparse(r.url)
    # spawn redirects to spawn-pending
    assert url.path == ujoin(app.base_url, 'hub/spawn-pending', username)
    # ?next query arg is preserved
    assert parse_qs(url.query).get('next') == [next_url]

    # check spawn-pending html
    page = BeautifulSoup(r.text, "html.parser")
    assert page.find('div', {'class': 'progress'})

    # validate event source url by consuming it
    script = page.body.find('script').string
    assert 'EventSource' in script
    # find EventSource url in javascript
    # maybe not the most robust way to check this?
    eventsource = script.find('new EventSource')
    start = script.find('(', eventsource)
    end = script.find(')', start)
    # strip quotes
    progress_url = script[start + 2 : end - 1]
    # verify that it works by watching progress events
    # (double-duty because we also want to wait for the spawn to finish)
    progress = await api_request(app, 'users', username, 'server/progress', stream=True)
    ex = async_requests.executor
    line_iter = iter(progress.iter_lines(decode_unicode=True))
    evt = True
    while evt is not None:
        evt = await ex.submit(next_event, line_iter)
        if evt:
            print(evt)

    # refresh page after progress is complete
    r = await async_requests.get(r.url, cookies=cookies)
    r.raise_for_status()
    # should have redirected to the now-running server
    assert urlparse(r.url).path == urlparse(next_url).path


async def test_user_redirect(app, username):
    name = username
    cookies = await app.login_user(name)

    r = await get_page('/user-redirect/tree/top/', app)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/hub/login')
    query = urlparse(r.url).query
    assert query == urlencode(
        {'next': ujoin(app.hub.base_url, '/user-redirect/tree/top/')}
    )

    r = await get_page('/user-redirect/notebooks/test.ipynb', app, cookies=cookies)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    while '/spawn-pending/' in path:
        await asyncio.sleep(0.1)
        r = await async_requests.get(r.url, cookies=cookies)
        path = urlparse(r.url).path
    assert path == ujoin(app.base_url, f'/user/{name}/notebooks/test.ipynb')


async def test_user_redirect_hook(app, username):
    """
    Test proper behavior of user_redirect_hook
    """
    name = username
    cookies = await app.login_user(name)

    async def dummy_redirect(path, request, user, base_url):
        assert base_url == app.base_url
        assert path == 'redirect-to-terminal'
        assert request.uri == ujoin(
            base_url, 'hub', 'user-redirect', 'redirect-to-terminal'
        )
        url = ujoin(user.url, '/terminals/1')
        return url

    app.user_redirect_hook = dummy_redirect

    r = await get_page('/user-redirect/redirect-to-terminal', app)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/hub/login')
    query = urlparse(r.url).query
    assert query == urlencode(
        {'next': ujoin(app.hub.base_url, '/user-redirect/redirect-to-terminal')}
    )

    # We don't actually want to start the server by going through spawn - just want to make sure
    # the redirect is to the right place
    r = await get_page(
        '/user-redirect/redirect-to-terminal',
        app,
        cookies=cookies,
        allow_redirects=False,
    )
    r.raise_for_status()
    redirected_url = urlparse(r.headers['Location'])
    assert redirected_url.path == ujoin(app.base_url, 'user', username, 'terminals/1')


@pytest.mark.parametrize(
    "has_access", ["all", "user", (pytest.param("group", id="in-group")), False]
)
async def test_other_user_url(app, username, user, group, create_temp_role, has_access):
    """Test accessing /user/someonelse/ URLs when the server is not running

    Used to redirect to your own server,
    which produced inconsistent behavior depending on whether the server was running.
    """
    name = username
    cookies = await app.login_user(name)
    other_user = user
    requester = app.users[name]
    other_user_url = f"/user/{other_user.name}"
    if has_access:
        if has_access == "group":
            group.users.append(other_user.orm_user)
            app.db.commit()
            scopes = [f"access:servers!group={group.name}"]
        elif has_access == "all":
            scopes = ["access:servers"]
        elif has_access == "user":
            scopes = [f"access:servers!user={other_user.name}"]
        role = create_temp_role(scopes)
        roles.grant_role(app.db, requester, role)
        status = 424
    else:
        # 404 - access denied without revealing if the user exists
        status = 404

    r = await get_page(other_user_url, app, cookies=cookies, hub=False)
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, f'hub/user/{other_user.name}/')
    assert r.status_code == status

    r = await get_page(f'{other_user_url}/test.ipynb', app, cookies=cookies, hub=False)
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, f'hub/user/{other_user.name}/test.ipynb')
    assert r.status_code == status

    r = await get_page(f'{other_user_url}/test.ipynb', app, hub=False)
    r.raise_for_status()
    print(urlparse(r.url))
    path = urlparse(r.url).path
    assert path == ujoin(app.base_url, '/hub/login')
    query = urlparse(r.url).query
    assert query == urlencode(
        {'next': ujoin(app.base_url, f'/hub/user/{other_user.name}/test.ipynb')}
    )


@pytest.mark.parametrize(
    "url, token_in",
    [
        ("/home", "url"),
        ("/home", "header"),
        ("/login", "url"),
        ("/login", "header"),
    ],
)
async def test_page_with_token(app, user, url, token_in):
    token = user.new_api_token()
    if token_in == "url":
        url = url_concat(url, {"token": token})
        headers = {}
    elif token_in == "header":
        headers = {
            "Authorization": f"token {token}",
        }

    # request a page with ?token= in URL shouldn't be allowed
    r = await get_page(
        url,
        app,
        headers=headers,
        allow_redirects=False,
    )
    if "/hub/login" in r.url:
        cookies = {'_xsrf'}
        assert r.status_code == 200
    else:
        cookies = set()
        assert r.status_code == 302
        assert r.headers["location"].partition("?")[0].endswith("/hub/login")
    assert {c.name for c in r.cookies} == cookies


async def test_login_fail(app):
    name = 'wash'
    base_url = public_url(app)
    r = await async_requests.post(
        base_url + 'hub/login',
        data={'username': name, 'password': 'wrong'},
        allow_redirects=False,
    )
    assert set(r.cookies.keys()).issubset({"_xsrf"})


@pytest.mark.parametrize(
    "form_user, auth_user, form_password",
    [
        ("spiff", "spiff", " space man "),
        (" spiff ", "spiff", " space man "),
    ],
)
async def test_login_strip(app, form_user, auth_user, form_password):
    """Test that login form strips space form usernames, but not passwords"""
    form_data = {"username": form_user, "password": form_password}
    expected_auth = {"username": auth_user, "password": form_password}
    called_with = []

    async def mock_authenticate(handler, data):
        called_with.append(data)

    with mock.patch.object(app.authenticator, 'authenticate', mock_authenticate):
        r = await get_page('login', app)
        r.raise_for_status()
        cookies = r.cookies
        xsrf = cookies['_xsrf']
        page = BeautifulSoup(r.text, "html.parser")
        action_url = public_host(app) + page.find("form")["action"]
        xsrf_input = page.find("form").find("input", attrs={"name": "_xsrf"})
        form_data["_xsrf"] = xsrf_input["value"]
        await async_requests.post(
            action_url, data=form_data, allow_redirects=False, cookies=cookies
        )

    assert called_with == [expected_auth]


@pytest.mark.parametrize(
    'running, next_url, location, params',
    [
        # default URL if next not specified, for both running and not
        (True, '', '', None),
        (False, '', '', None),
        # next_url is respected
        (False, '/hub/admin', '/hub/admin', None),
        (False, '/user/other', '/user/other', None),
        (False, '/absolute', '/absolute', None),
        (False, '/has?query#andhash', '/has?query#andhash', None),
        # :// in query string or fragment
        (False, '/has?repo=https/host.git', '/has?repo=https/host.git', None),
        (False, '/has?repo=https://host.git', '/has?repo=https://host.git', None),
        (False, '/has#repo=https://host.git', '/has#repo=https://host.git', None),
        # next_url outside is not allowed
        (False, 'relative/path', '', None),
        (False, 'https://other.domain', '', None),
        (False, 'ftp://other.domain', '', None),
        (False, '//other.domain', '', None),
        (False, '///other.domain/triple', '', None),
        (False, '\\\\other.domain/backslashes', '', None),
        # params are handled correctly (ignored if ?next= specified)
        (
            True,
            '/hub/admin?left=1&right=2',
            'hub/admin?left=1&right=2',
            {"left": "abc"},
        ),
        (False, '/hub/admin', 'hub/admin', [('left', 1), ('right', 2)]),
        (True, '', '', {"keep": "yes"}),
        (False, '', '', {"keep": "yes"}),
    ],
)
async def test_login_redirect(app, running, next_url, location, params):
    cookies = await app.login_user('river')
    user = app.users['river']
    if location:
        location = ujoin(app.base_url, location)
    elif running:
        # location not specified,
        location = user.url
        if params:
            location = url_concat(location, params)
    else:
        # use default url
        location = ujoin(app.base_url, 'hub/spawn')
        if params:
            location = url_concat(location, params)

    url = 'login'
    if params:
        url = url_concat(url, params)
    if next_url:
        if next_url.startswith('/') and not (
            next_url.startswith("//") or urlparse(next_url).netloc
        ):
            next_url = ujoin(app.base_url, next_url, '')
        url = url_concat(url, dict(next=next_url))

    if running and not user.active:
        # ensure running
        await user.spawn()
    elif user.active and not running:
        # ensure not running
        await user.stop()
    r = await get_page(url, app, cookies=cookies, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 302
    assert r.headers["Location"] == location


@pytest.mark.parametrize(
    'location, next, extra_params',
    [
        (
            "{base_url}hub/spawn?a=5",
            None,
            {"a": "5"},
        ),  # no ?next= given, preserve params
        ("/x", "/x", {"a": "5"}),  # ?next=given, params ignored
        (
            "/x?b=10",
            "/x?b=10",
            {"a": "5"},
        ),  # ?next=given with params, additional params ignored
    ],
)
async def test_next_url(app, user, location, next, extra_params):
    params = {}
    if extra_params:
        params.update(extra_params)
    if next:
        params["next"] = next
    url = url_concat("/", params)
    cookies = await app.login_user("monster")

    # location can be a string template
    location = location.format(base_url=app.base_url)

    r = await get_page(url, app, cookies=cookies, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 302
    assert r.headers["Location"] == location


async def test_next_url_params_sequence(app, user):
    """Test each step of / -> login -> spawn

    and whether they preserve url params
    """
    params = {"xyz": "5"}
    # first request: root page, with params, not logged in
    r = await get_page("/?xyz=5", app, allow_redirects=False)
    r.raise_for_status()
    location = r.headers["Location"]

    # next page: login
    cookies = await app.login_user(user.name)
    assert location == url_concat(
        ujoin(app.base_url, "/hub/login"), {"next": ujoin(app.base_url, "/hub/?xyz=5")}
    )
    r = await async_requests.get(
        public_host(app) + location, cookies=cookies, allow_redirects=False
    )
    r.raise_for_status()
    location = r.headers["Location"]

    # after login, redirect back
    assert location == ujoin(app.base_url, "/hub/?xyz=5")
    r = await async_requests.get(
        public_host(app) + location, cookies=cookies, allow_redirects=False
    )
    r.raise_for_status()
    location = r.headers["Location"]
    assert location == ujoin(app.base_url, "/hub/spawn?xyz=5")


async def test_auto_login(app, request):
    class DummyLoginHandler(BaseHandler):
        def get(self):
            self.write('ok!')

    base_url = public_url(app) + '/'
    app.tornado_application.add_handlers(
        ".*$", [(ujoin(app.hub.base_url, 'dummy'), DummyLoginHandler)]
    )
    # no auto_login: end up at /hub/login
    r = await async_requests.get(base_url)
    assert r.url == url_concat(
        public_url(app, path="hub/login"), {"next": app.hub.base_url}
    )
    # enable auto_login: redirect from /hub/login to /hub/dummy
    authenticator = Authenticator(auto_login=True)
    authenticator.login_url = lambda base_url: ujoin(base_url, 'dummy')

    with mock.patch.dict(app.tornado_settings, {'authenticator': authenticator}):
        r = await async_requests.get(base_url)
    assert r.url == url_concat(
        public_url(app, path="hub/dummy"), {"next": app.hub.base_url}
    )


async def test_auto_login_logout(app):
    name = 'burnham'
    cookies = await app.login_user(name)
    s = AsyncSession()
    s.cookies = cookies

    with mock.patch.dict(
        app.tornado_settings, {'authenticator': Authenticator(auto_login=True)}
    ):
        r = await s.get(
            public_host(app) + app.tornado_settings['logout_url'], cookies=cookies
        )
    r.raise_for_status()
    logout_url = public_host(app) + app.tornado_settings['logout_url']
    assert r.url == logout_url
    assert list(s.cookies.keys()) == ["_xsrf"]
    # don't include logged-out user in page:
    try:
        idx = r.text.index(name)
    except ValueError:
        # not found, good!
        pass
    else:
        assert name not in r.text[idx - 100 : idx + 100]


async def test_logout(app):
    name = 'wash'
    cookies = await app.login_user(name)
    s = AsyncSession()
    s.cookies = cookies
    r = await s.get(
        public_host(app) + app.tornado_settings['logout_url'],
    )
    r.raise_for_status()
    login_url = public_host(app) + app.tornado_settings['login_url']
    assert r.url == login_url
    assert list(s.cookies.keys()) == ["_xsrf"]


@pytest.mark.parametrize('shutdown_on_logout', [True, False])
async def test_shutdown_on_logout(app, shutdown_on_logout):
    name = 'shutitdown'
    cookies = await app.login_user(name)
    s = AsyncSession()
    s.cookies = cookies
    user = app.users[name]

    # start the user's server
    await user.spawn()
    spawner = user.spawner

    # wait for any pending state to resolve
    for i in range(50):
        if not spawner.pending:
            break
        await asyncio.sleep(0.1)
    else:
        assert False, "Spawner still pending"
    assert spawner.active

    # logout
    with mock.patch.dict(
        app.tornado_settings, {'shutdown_on_logout': shutdown_on_logout}
    ):
        r = await s.get(
            public_host(app) + app.tornado_settings['logout_url'], cookies=cookies
        )
        r.raise_for_status()

    login_url = public_host(app) + app.tornado_settings['login_url']
    assert r.url == login_url
    assert list(s.cookies.keys()) == ["_xsrf"]

    # wait for any pending state to resolve
    for i in range(50):
        if not spawner.pending:
            break
        await asyncio.sleep(0.1)
    else:
        assert False, "Spawner still pending"

    assert spawner.ready == (not shutdown_on_logout)


async def test_login_no_allowed_adds_user(app):
    auth = app.authenticator
    mock_add_user = mock.Mock()
    with mock.patch.object(auth, 'add_user', mock_add_user):
        cookies = await app.login_user('jubal')

    user = app.users['jubal']
    assert mock_add_user.mock_calls == [mock.call(user)]


async def test_static_files(app):
    base_url = ujoin(public_host(app), app.hub.base_url)
    r = await async_requests.get(ujoin(base_url, 'logo'))
    r.raise_for_status()
    assert r.headers['content-type'] == 'image/png'
    r = await async_requests.get(
        ujoin(base_url, 'static', 'images', 'jupyterhub-80.png')
    )
    r.raise_for_status()
    assert r.headers['content-type'] == 'image/png'
    r = await async_requests.get(ujoin(base_url, 'static', 'css', 'style.min.css'))
    r.raise_for_status()
    assert r.headers['content-type'] == 'text/css'


async def test_token_auth(app):
    cookies = await app.login_user('token')
    r = await get_page('token', app, cookies=cookies)
    r.raise_for_status()
    assert r.status_code == 200


async def test_oauth_token_page(app):
    name = 'token'
    cookies = await app.login_user(name)
    user = app.users[orm.User.find(app.db, name)]
    client = orm.OAuthClient(identifier='token')
    app.db.add(client)
    oauth_token = orm.APIToken()
    app.db.add(oauth_token)
    oauth_token.oauth_client = client
    oauth_token.user = user
    app.db.commit()
    r = await get_page('token', app, cookies=cookies)
    r.raise_for_status()
    assert r.status_code == 200


@pytest.mark.parametrize("error_status", [503, 404])
async def test_proxy_error(app, error_status):
    r = await get_page('/error/%i' % error_status, app)
    assert r.status_code == 200


@pytest.mark.parametrize(
    "announcements", ["", "spawn", "spawn,home,login", "login,logout"]
)
async def test_announcements(app, announcements):
    """Test announcements on various pages"""
    # Default announcement - same on all pages
    ann01 = "ANNOUNCE01"
    template_vars = {"announcement": ann01}
    announcements = announcements.split(",")
    for name in announcements:
        template_vars["announcement_" + name] = "ANN_" + name

    def assert_announcement(name, text):
        if name in announcements:
            assert template_vars["announcement_" + name] in text
            assert ann01 not in text
        else:
            assert ann01 in text

    cookies = await app.login_user("jones")
    # make sure spawner isn't running
    # so we see the spawn form
    user = app.users["jones"]
    await user.stop()

    with mock.patch.dict(
        app.tornado_settings,
        {"template_vars": template_vars, "spawner_class": FormSpawner},
    ):
        r = await get_page("login", app)
        r.raise_for_status()
        assert_announcement("login", r.text)
        r = await get_page("spawn", app, cookies=cookies)
        r.raise_for_status()
        assert_announcement("spawn", r.text)
        r = await get_page("home", app, cookies=cookies)  # hub/home
        r.raise_for_status()
        assert_announcement("home", r.text)
        # need auto_login=True to get logout page
        auto_login = app.authenticator.auto_login
        app.authenticator.auto_login = True
        try:
            r = await get_page("logout", app, cookies=cookies)
        finally:
            app.authenticator.auto_login = auto_login
        r.raise_for_status()
        assert_announcement("logout", r.text)


@pytest.mark.parametrize(
    "params", ["", "redirect_uri=/noexist", "redirect_uri=ok&client_id=nosuchthing"]
)
async def test_bad_oauth_get(app, params):
    cookies = await app.login_user("authorizer")
    r = await get_page(
        "hub/api/oauth2/authorize?" + params, app, hub=False, cookies=cookies
    )
    assert r.status_code == 400


@pytest.mark.parametrize(
    "scopes, has_access",
    [
        (["users"], False),
        (["admin:users"], False),
        (["users", "admin:users", "admin:servers"], False),
        (["admin-ui"], True),
    ],
)
async def test_admin_page_access(app, scopes, has_access, create_user_with_scopes):
    user = create_user_with_scopes(*scopes)
    cookies = await app.login_user(user.name)
    home_resp = await get_page("/home", app, cookies=cookies)
    admin_resp = await get_page("/admin", app, cookies=cookies)
    assert home_resp.status_code == 200
    soup = BeautifulSoup(home_resp.text, "html.parser")
    nav = soup.find("div", id="thenavbar")
    links = [a["href"] for a in nav.find_all("a")]

    admin_url = app.base_url + "hub/admin"
    if has_access:
        assert admin_resp.status_code == 200
        assert admin_url in links
    else:
        assert admin_resp.status_code == 403
        assert admin_url not in links


async def test_oauth_page_scope_appearance(
    app, mockservice_url, create_user_with_scopes, create_temp_role
):
    service_role = create_temp_role(
        [
            'self',
            'read:users!user=gawain',
            'read:tokens',
            'read:groups!group=mythos',
        ]
    )
    service = mockservice_url
    user = create_user_with_scopes("access:services")
    roles.grant_role(app.db, user, service_role)
    oauth_client = (
        app.db.query(orm.OAuthClient)
        .filter_by(identifier=service.oauth_client_id)
        .one()
    )
    oauth_client.allowed_scopes = sorted(roles.roles_to_scopes([service_role]))
    app.db.commit()

    s = AsyncSession()
    s.cookies = await app.login_user(user.name)
    url = url_path_join(public_url(app, service) + 'owhoami/?arg=x')
    r = await s.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    scopes_block = soup.find('form')
    for scope in service_role.scopes:
        base_scope, _, filter_ = scope.partition('!')
        scope_def = scopes.scope_definitions[base_scope]
        assert scope_def['description'] in scopes_block.text
        if filter_:
            kind, _, name = filter_.partition('=')
            assert kind in scopes_block.text
            assert name in scopes_block.text


async def test_token_page(app):
    name = "cake"
    cookies = await app.login_user(name)
    r = await get_page("token", app, cookies=cookies)
    r.raise_for_status()
    assert urlparse(r.url).path.endswith('/hub/token')

    def extract_body(r):
        soup = BeautifulSoup(r.text, "html.parser")
        import re

        # trim empty lines
        return re.sub(r"(\n\s*)+", "\n", soup.body.find(class_="container").text)

    body = extract_body(r)
    assert "Request new API token" in body, body
    # no tokens yet, no lists
    assert "API Tokens" not in body, body
    assert "Authorized Applications" not in body, body

    # request an API token
    user = app.users[name]
    token = user.new_api_token(expires_in=60, note="my-test-token")
    app.db.commit()

    r = await get_page("token", app, cookies=cookies)
    r.raise_for_status()
    body = extract_body(r)
    assert "API Tokens" in body, body
    assert "my-test-token" in body, body
    # no oauth tokens yet, shouldn't have that section
    assert "Authorized Applications" not in body, body

    # spawn the user to trigger oauth, etc.
    # request an oauth token
    user.spawner.cmd = [sys.executable, '-m', 'jupyterhub.singleuser']
    r = await get_page("spawn", app, cookies=cookies)
    r.raise_for_status()

    # wait for the server to be running and visit it
    while not user.spawner.ready:
        await asyncio.sleep(0.1)
    r = await get_page("user/" + user.name, app, cookies=cookies)
    r.raise_for_status()

    r = await get_page("token", app, cookies=cookies)
    r.raise_for_status()
    body = extract_body(r)
    assert "API Tokens" in body, body
    assert f"Server at {user.base_url}" in body, body
    assert "Authorized Applications" in body, body


async def test_server_not_running_api_request(app):
    cookies = await app.login_user("bees")
    r = await get_page("user/bees/api/status", app, hub=False, cookies=cookies)
    assert r.status_code == 424
    assert r.headers["content-type"] == "application/json"
    message = r.json()['message']
    assert ujoin(app.base_url, "hub/spawn/bees") in message
    assert " /user/bees" in message


async def test_server_not_running_api_request_legacy_status(app):
    app.use_legacy_stopped_server_status_code = True
    cookies = await app.login_user("bees")
    r = await get_page("user/bees/api/status", app, hub=False, cookies=cookies)
    assert r.status_code == 503


async def test_health_check_request(app):
    r = await get_page('health', app)
    assert r.status_code == 200


async def test_pre_spawn_start_exc_no_form(app):
    exc = "Unhandled error starting server"

    # throw exception from pre_spawn_start
    async def mock_pre_spawn_start(user, spawner):
        raise Exception(exc)

    with mock.patch.object(app.authenticator, 'pre_spawn_start', mock_pre_spawn_start):
        cookies = await app.login_user('summer')
        # spawn page should thow a 500 error and show the pre_spawn_start error message
        r = await get_page('spawn', app, cookies=cookies)
        assert r.status_code == 500
        assert exc in r.text


async def test_pre_spawn_start_exc_options_form(app):
    exc = "pre_spawn_start error"

    # throw exception from pre_spawn_start
    async def mock_pre_spawn_start(user, spawner):
        raise Exception(exc)

    with mock.patch.dict(
        app.users.settings, {'spawner_class': FormSpawner}
    ), mock.patch.object(app.authenticator, 'pre_spawn_start', mock_pre_spawn_start):
        cookies = await app.login_user('spring')
        user = app.users['spring']
        # spawn page shouldn't throw any error until the spawn is started
        r = await get_page('spawn', app, cookies=cookies)
        assert r.url.endswith('/spawn')
        r.raise_for_status()
        assert FormSpawner.options_form in r.text
        # spawning the user server should throw the pre_spawn_start error
        with pytest.raises(Exception, match=str(exc)):
            await user.spawn()


@pytest.mark.parametrize(
    "scope, display, present",
    [
        ("access:services", True, True),
        ("access:services!service=SERVICE", True, True),
        ("access:services!service=SERVICE", False, False),
        ("access:services!service=other", True, False),
        ("", True, False),
    ],
)
async def test_services_nav_links(
    app, mockservice_url, create_user_with_scopes, scope, display, present
):
    service = mockservice_url
    service.display = display
    scopes = []
    if scope:
        scope = scope.replace("SERVICE", service.name)
        scopes.append(scope)
    user = create_user_with_scopes(*scopes)

    cookies = await app.login_user(user.name)
    r = await get_page("home", app, cookies=cookies)
    assert r.status_code == 200
    page = BeautifulSoup(r.text)
    nav = page.find("ul", class_="navbar-nav")
    # find service links
    nav_urls = [a["href"] for a in nav.find_all("a")]
    if present:
        assert service.href in nav_urls
    else:
        assert service.href not in nav_urls
