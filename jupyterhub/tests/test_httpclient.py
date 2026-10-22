import pytest
from traitlets.config import Config

from jupyterhub.httpclient import JupyterHubHTTPClient, fetch
from jupyterhub.utils import url_path_join

from .utils import public_url


async def test_http_client_default(app):
    r = await fetch(url_path_join(public_url(app), "hub/api/"))
    assert r.status == 200


async def test_connector_options():
    JupyterHubHTTPClient.clear_instance()
    cfg = Config()
    cfg.JupyterHubHTTPClient.connector_options = {"limit": 10}
    client = JupyterHubHTTPClient.instance(config=cfg)
    s = client._session
    assert s.connector.limit == 10
    await client.close()


async def test_session_options():
    JupyterHubHTTPClient.clear_instance()
    cfg = Config()
    cfg.JupyterHubHTTPClient.session_options = {"headers": {"X-test-id": "abc"}}
    client = JupyterHubHTTPClient.instance(config=cfg)
    s = client._session
    assert s.headers["X-test-id"] == "abc"
    await client.close()


async def test_resolver_options():
    JupyterHubHTTPClient.clear_instance()
    cfg = Config()
    cfg.JupyterHubHTTPClient.resolver_options = {"nameservers": ["127.0.0.1"]}
    client = JupyterHubHTTPClient.instance(config=cfg)
    with pytest.raises(ValueError):
        # invalid to set resolver_options and not resolver_class
        s = client._session
    cfg.JupyterHubHTTPClient.resolver_class = "aiohttp.resolver.AsyncResolver"
    JupyterHubHTTPClient.clear_instance()
    client = JupyterHubHTTPClient.instance(config=cfg)
    s = client._session
    # private API to access aiodns.DNSResolver instance
    # TCPConnector -> AsyncResolver -> DNSResolver
    assert s.connector._resolver._resolver.nameservers == ["127.0.0.1"]
