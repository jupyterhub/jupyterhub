"""Test managing a ConfigurableHTTPProxy running on unix sockets."""

from urllib.parse import quote

import pytest
from traitlets.config import Config

from ..httpclient import fetch
from .mocking import MockHub
from .utils import auth_header


@pytest.fixture
async def new_hub():
    apps = []

    async def _new_hub(config):
        app = MockHub.instance(config=config)
        app.last_activity_interval = 0
        apps.append(app)
        await app.initialize([])
        await app.start()

        async def noop():
            return

        app.shutdown_cancel_tasks = noop
        return app

    yield _new_hub
    for app in apps:
        await app.stop()
    MockHub.clear_instance()


async def test_unix_socket_proxy(new_hub, tmp_path):
    cfg = Config()
    proxy_sock = str(tmp_path / 'proxy.sock')
    api_sock = str(tmp_path / 'api.sock')

    auth_token = 'secret!'

    cfg.JupyterHub.bind_url = f'http+unix://{quote(proxy_sock, safe="")}'
    cfg.ConfigurableHTTPProxy.api_url = f'http+unix://{quote(api_sock, safe="")}'
    cfg.ConfigurableHTTPProxy.should_start = True
    cfg.ConfigurableHTTPProxy.auth_token = auth_token

    app = await new_hub(config=cfg)

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
    r = await fetch(
        f'{cfg.JupyterHub.bind_url}/hub/api/info',
        method="GET",
        headers=headers,
    )
    assert r.status == 200

    # test proxy api
    r = await fetch(
        f'{app.proxy.api_url}/api/routes',
        method="GET",
        headers={"Authorization": f'token {app.proxy.auth_token}'},
    )
    assert r.status == 200
