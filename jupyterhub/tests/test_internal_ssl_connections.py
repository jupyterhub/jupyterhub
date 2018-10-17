"""Tests for jupyterhub internal_ssl connections"""

import time
from subprocess import check_output
import sys
from urllib.parse import urlparse

import pytest

import jupyterhub
from tornado import gen
from unittest import mock
from requests.exceptions import SSLError

from .utils import async_requests
from .test_api import add_user

ssl_enabled = True


@gen.coroutine
def wait_for_spawner(spawner, timeout=10):
    """Wait for an http server to show up

    polling at shorter intervals for early termination
    """
    deadline = time.monotonic() + timeout
    def wait():
        return spawner.server.wait_up(timeout=1, http=True)
    while time.monotonic() < deadline:
        status = yield spawner.poll()
        assert status is None
        try:
            yield wait()
        except TimeoutError:
            continue
        else:
            break
    yield wait()


@pytest.mark.gen_test
def test_connection_hub_wrong_certs(app):
    """Connecting to the internal hub url fails without correct certs"""
    with pytest.raises(SSLError):
        kwargs = {'verify': False}
        r = yield async_requests.get(app.hub.url, **kwargs)
        r.raise_for_status()


@pytest.mark.gen_test
def test_connection_proxy_api_wrong_certs(app):
    """Connecting to the proxy api fails without correct certs"""
    with pytest.raises(SSLError):
        kwargs = {'verify': False}
        r = yield async_requests.get(app.proxy.api_url, **kwargs)
        r.raise_for_status()


@pytest.mark.gen_test
def test_connection_notebook_wrong_certs(app):
    """Connecting to a notebook fails without correct certs"""
    with mock.patch.dict(
            app.config.LocalProcessSpawner,
            {'cmd': [sys.executable, '-m', 'jupyterhub.tests.mocksu']}
        ):
        user = add_user(app.db, app, name='foo')
        yield user.spawn()
        yield wait_for_spawner(user.spawner)
        spawner = user.spawner
        status = yield spawner.poll()
        assert status is None

        with pytest.raises(SSLError):
            kwargs = {'verify': False}
            r = yield async_requests.get(spawner.server.url, **kwargs)
            r.raise_for_status()
