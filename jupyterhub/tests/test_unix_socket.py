"""Test managing a ConfigurableHTTPProxy running on unix sockets."""

from urllib.parse import quote_plus

from traitlets.config import Config

from ..utils import async_fetch
from .mocking import MockHub
from .utils import auth_header


async def test_unix_socket_proxy(request, tmp_path):
    cfg = Config()
    proxy_sock = str(tmp_path / 'proxy.sock')
    api_sock = str(tmp_path / 'api.sock')

    auth_token = 'secret!'

    cfg.bind_url = f'http+unix://{quote_plus(proxy_sock)}'
    cfg.ConfigurableHTTPProxy.api_url = f'http+unix://{quote_plus(api_sock)}'
    cfg.ConfigurableHTTPProxy.should_start = True
    cfg.ConfigurableHTTPProxy.auth_token = auth_token

    app = MockHub.instance(config=cfg, bind_url=cfg.bind_url)
    # disable last_activity polling to avoid check_routes being called during the test,
    # which races with some of our test conditions
    app.last_activity_interval = 0

    def fin():
        MockHub.clear_instance()
        app.stop()

    request.addfinalizer(fin)

    await app.initialize([])
    await app.start()

    expected_args = [
        "configurable-http-proxy",
        "--socket",
        proxy_sock,
        "--api-socket",
        api_sock,
    ]
    assert app.proxy.proxy_process.args[:5] == expected_args

    # test proxy
    headers = {}
    headers.update(auth_header(app.db, 'admin'))
    r = await async_fetch(
        f'{cfg.bind_url}/hub/api/info',
        method="GET",
        headers=headers,
    )
    assert r.code == 200

    # test proxy api
    r = await async_fetch(
        f'{app.proxy.api_url}/api/routes',
        method="GET",
        headers={"Authorization": f'token {app.proxy.auth_token}'},
    )
    assert r.code == 200
