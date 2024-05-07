"""Test a proxy being started before the Hub"""

import json
import os
from contextlib import contextmanager
from subprocess import Popen
from urllib.parse import quote, urlparse

import pytest
from traitlets import TraitError
from traitlets.config import Config

from ..utils import random_port, wait_for_http_server
from ..utils import url_path_join as ujoin
from .mocking import MockHub
from .test_api import add_user, api_request
from .utils import skip_if_ssl


@pytest.fixture
def disable_check_routes(app):
    # disable periodic check_routes while we are testing
    app._periodic_callbacks["last_activity"].stop()
    try:
        yield
    finally:
        app._periodic_callbacks["last_activity"].start()


@skip_if_ssl
@pytest.mark.flaky(reruns=2)
async def test_external_proxy(request):
    auth_token = 'secret!'
    proxy_ip = '127.0.0.1'
    proxy_port = random_port()
    cfg = Config()
    cfg.ConfigurableHTTPProxy.auth_token = auth_token
    cfg.ConfigurableHTTPProxy.api_url = 'http://%s:%i' % (proxy_ip, proxy_port)
    cfg.ConfigurableHTTPProxy.should_start = False

    app = MockHub.instance(config=cfg)
    # disable last_activity polling to avoid check_routes being called during the test,
    # which races with some of our test conditions
    app.last_activity_interval = 0

    def fin():
        MockHub.clear_instance()
        app.http_server.stop()

    request.addfinalizer(fin)

    # configures and starts proxy process
    env = os.environ.copy()
    env['CONFIGPROXY_AUTH_TOKEN'] = auth_token
    cmd = [
        'configurable-http-proxy',
        '--ip',
        app.ip,
        '--port',
        str(app.port),
        '--api-ip',
        proxy_ip,
        '--api-port',
        str(proxy_port),
        '--log-level=debug',
    ]
    if app.subdomain_host:
        cmd.append('--host-routing')
    proxy = Popen(cmd, env=env)

    def _cleanup_proxy():
        if proxy.poll() is None:
            proxy.terminate()
            proxy.wait(timeout=10)

    request.addfinalizer(_cleanup_proxy)

    def wait_for_proxy():
        return wait_for_http_server('http://%s:%i' % (proxy_ip, proxy_port))

    await wait_for_proxy()

    await app.initialize([])
    await app.start()
    assert app.proxy.proxy_process is None

    # test if api service has a root route '/'
    routes = await app.proxy.get_all_routes()
    assert list(routes.keys()) == [app.hub.routespec]

    # add user to the db and start a single user server
    name = 'river'
    add_user(app.db, app, name=name)
    r = await api_request(
        app, 'users', name, 'server', method='post', bypass_proxy=True
    )
    r.raise_for_status()

    routes = await app.proxy.get_all_routes()
    # sets the desired path result
    user_path = ujoin(app.base_url, 'user/river') + '/'
    print(app.base_url, user_path)
    host = ''
    if app.subdomain_host:
        host = f'{name}.{urlparse(app.subdomain_host).hostname}'
    user_spec = host + user_path
    assert sorted(routes.keys()) == [app.hub.routespec, user_spec]

    # teardown the proxy and start a new one in the same place
    proxy.terminate()
    proxy.wait(timeout=10)
    proxy = Popen(cmd, env=env)
    await wait_for_proxy()

    routes = await app.proxy.get_all_routes()

    assert list(routes.keys()) == []

    # poke the server to update the proxy
    r = await api_request(app, 'proxy', method='post', bypass_proxy=True)
    r.raise_for_status()

    # check that the routes are correct
    routes = await app.proxy.get_all_routes()
    assert sorted(routes.keys()) == [app.hub.routespec, user_spec]

    # teardown the proxy, and start a new one with different auth and port
    proxy.terminate()
    proxy.wait(timeout=10)
    new_auth_token = 'different!'
    env['CONFIGPROXY_AUTH_TOKEN'] = new_auth_token
    proxy_port = random_port()
    cmd = [
        'configurable-http-proxy',
        '--ip',
        app.ip,
        '--port',
        str(app.port),
        '--api-ip',
        proxy_ip,
        '--api-port',
        str(proxy_port),
        '--default-target',
        'http://%s:%i' % (app.hub_ip, app.hub_port),
    ]
    if app.subdomain_host:
        cmd.append('--host-routing')
    proxy = Popen(cmd, env=env)
    await wait_for_proxy()

    # tell the hub where the new proxy is
    new_api_url = f'http://{proxy_ip}:{proxy_port}'
    r = await api_request(
        app,
        'proxy',
        method='patch',
        data=json.dumps({'api_url': new_api_url, 'auth_token': new_auth_token}),
        bypass_proxy=True,
    )
    r.raise_for_status()
    assert app.proxy.api_url == new_api_url

    assert app.proxy.auth_token == new_auth_token

    # check that the routes are correct
    routes = await app.proxy.get_all_routes()
    assert sorted(routes.keys()) == [app.hub.routespec, user_spec]


@pytest.mark.parametrize("username", ['zoe', '50fia', '秀樹', '~TestJH', 'has@'])
async def test_check_routes(app, username, disable_check_routes):
    proxy = app.proxy
    test_user = add_user(app.db, app, name=username)
    r = await api_request(app, f'users/{username}/server', method='post')
    r.raise_for_status()

    # check a valid route exists for user
    routes = await app.proxy.get_all_routes()
    before = sorted(routes)
    assert test_user.proxy_spec in before

    # check if a route is removed when user deleted
    await app.proxy.check_routes(app.users, app._service_map)
    await proxy.delete_user(test_user)
    routes = await app.proxy.get_all_routes()
    during = sorted(routes)
    assert test_user.proxy_spec not in during

    # check if a route exists for user
    await app.proxy.check_routes(app.users, app._service_map)
    routes = await app.proxy.get_all_routes()
    after = sorted(routes)
    assert test_user.proxy_spec in after

    # check that before and after state are the same
    assert before == after


@pytest.mark.parametrize(
    "routespec",
    [
        '/has%20space/foo/',
        '/missing-trailing/slash',
        '/has/@/',
        '/has/' + quote('üñîçø∂é'),
        'host.name/path/',
        'other.host/path/no/slash',
    ],
)
async def test_extra_routes(app, routespec):
    proxy = app.proxy
    # When using host_routing, it's up to the admin to
    # provide routespecs that have a domain in them.
    # We don't explicitly validate that here.
    if app.subdomain_host and routespec.startswith("/"):
        routespec = 'example.com/' + routespec
    elif not app.subdomain_host and not routespec.startswith("/"):
        pytest.skip("requires subdomains")
    validated_routespec = routespec
    if not routespec.endswith("/"):
        validated_routespec = routespec + "/"
    target = 'http://localhost:9999/test'
    proxy.extra_routes = {routespec: target}

    await proxy.check_routes(app.users, app._service_map)

    routes = await app.proxy.get_all_routes()
    print(routes)
    assert validated_routespec in routes
    assert routes[validated_routespec]['target'] == target
    assert routes[validated_routespec]['data']['extra']


@pytest.mark.parametrize(
    "needs_subdomain, routespec, expected",
    [
        (False, "/prefix/", "/prefix/"),
        (False, "/prefix", "/prefix/"),
        (False, "prefix/", ValueError),
        (True, "/prefix/", ValueError),
        (True, "example.com/prefix/", "example.com/prefix/"),
        (True, "example.com/prefix", "example.com/prefix/"),
        (False, 100, TraitError),
    ],
)
def test_extra_routes_validate_routespec(
    request, app, needs_subdomain, routespec, expected
):
    save_host = app.subdomain_host
    request.addfinalizer(lambda: setattr(app, "subdomain_host", save_host))
    if needs_subdomain:
        app.subdomain_host = "localhost.jovyan.org"
    else:
        app.subdomain_host = ""

    proxy = app.proxy

    extra_routes = {routespec: "https://127.0.0.1"}
    if isinstance(expected, type) and issubclass(expected, BaseException):
        with pytest.raises(expected):
            proxy.extra_routes = extra_routes
        return
    proxy.extra_routes = extra_routes
    assert list(proxy.extra_routes) == [expected]


@pytest.mark.parametrize(
    "target, expected",
    [
        ("http://host", "http://host"),
        ("https://host", "https://host"),
        ("/missing-host", ValueError),
        ("://missing-scheme", ValueError),
        (100, TraitError),
    ],
)
def test_extra_routes_validate_target(app, target, expected):
    proxy = app.proxy
    routespec = "/prefix/"
    if app.subdomain_host:
        routespec = f"host.tld{routespec}"
    extra_routes = {routespec: target}
    if isinstance(expected, type) and issubclass(expected, BaseException):
        with pytest.raises(expected):
            proxy.extra_routes = extra_routes
        return
    proxy.extra_routes = extra_routes
    assert list(proxy.extra_routes.values()) == [expected]


@pytest.mark.parametrize(
    "routespec",
    [
        '/has%20space/foo/',
        '/missing-trailing/slash',
        '/has/@/',
        '/has/' + quote('üñîçø∂é'),
        'host.name/path/',
        'other.host/path/no/slash',
    ],
)
async def test_add_get_delete(app, routespec, disable_check_routes):
    arg = routespec
    if not routespec.endswith('/'):
        routespec = routespec + '/'

    # host-routes when not host-routing raises an error
    # and vice versa
    expect_value_error = bool(app.subdomain_host) ^ (not routespec.startswith('/'))

    @contextmanager
    def context():
        if expect_value_error:
            with pytest.raises(ValueError):
                yield
        else:
            yield

    proxy = app.proxy
    target = 'https://localhost:1234'
    with context():
        await proxy.add_route(arg, target, {})
    routes = await proxy.get_all_routes()
    if not expect_value_error:
        assert routespec in routes.keys()
    with context():
        route = await proxy.get_route(arg)
        assert route == {
            'target': target,
            'routespec': routespec,
            'data': route.get('data'),
        }
    with context():
        await proxy.delete_route(arg)
    with context():
        route = await proxy.get_route(arg)
        assert route is None


@pytest.mark.parametrize("test_data", [None, 'notjson', json.dumps([])])
async def test_proxy_patch_bad_request_data(app, test_data):
    r = await api_request(app, 'proxy', method='patch', data=test_data)
    assert r.status_code == 400
