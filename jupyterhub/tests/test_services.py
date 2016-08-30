"""Tests for services"""

from binascii import hexlify
from contextlib import contextmanager
import os
from subprocess import Popen, TimeoutExpired
import sys
from threading import Event
import time
try:
    from unittest import mock
except ImportError:
    import mock
from urllib.parse import unquote

import pytest
from tornado import gen
from tornado.ioloop import IOLoop


import jupyterhub.services.service
from .test_pages import get_page
from ..utils import url_path_join, wait_for_http_server

here = os.path.dirname(os.path.abspath(__file__))
mockservice_py = os.path.join(here, 'mockservice.py')
mockservice_cmd = [sys.executable, mockservice_py]

from ..utils import random_port

@contextmanager
def external_service(app, name='mockservice'):
    env = {
        'JUPYTERHUB_API_TOKEN': hexlify(os.urandom(5)),
        'JUPYTERHUB_SERVICE_NAME': name,
        'JUPYTERHUB_API_URL': url_path_join(app.hub.server.url, 'api/'),
        'JUPYTERHUB_SERVICE_URL': 'http://127.0.0.1:%i' % random_port(),
    }
    p = Popen(mockservice_cmd, env=env)
    IOLoop().run_sync(lambda : wait_for_http_server(env['JUPYTERHUB_SERVICE_URL']))
    try:
        yield env
    finally:
        p.terminate()


# mock services for testing.
# Shorter intervals, etc.
class MockServiceSpawner(jupyterhub.services.service._ServiceSpawner):
    poll_interval = 1

@pytest.yield_fixture
def mockservice(request, app):
    name = 'mock-service'
    with mock.patch.object(jupyterhub.services.service, '_ServiceSpawner', MockServiceSpawner):
        app.services = [{
            'name': name,
            'command': mockservice_cmd,
            'url': 'http://127.0.0.1:%i' % random_port(),
            'admin': True,
        }]
        app.init_services()
        app.io_loop.add_callback(app.proxy.add_all_services, app._service_map)
        assert name in app._service_map
        service = app._service_map[name]
        app.io_loop.add_callback(service.start)
        request.addfinalizer(service.stop)
        for i in range(20):
            if not getattr(service, 'proc', False):
                time.sleep(0.2)
        # ensure process finishes starting
        with pytest.raises(TimeoutExpired):
            service.proc.wait(1)
        yield service


def test_managed_service(app, mockservice):
    service = mockservice
    proc = service.proc
    first_pid = proc.pid
    assert proc.poll() is None
    # shut it down:
    proc.terminate()
    proc.wait(10)
    assert proc.poll() is not None
    # ensure Hub notices and brings it back up:
    for i in range(20):
        if service.proc is not proc:
            break
        else:
            time.sleep(0.2)
    
    assert service.proc.pid != first_pid
    assert service.proc.poll() is None


def test_proxy_service(app, mockservice, io_loop):
    name = mockservice.name
    routes = io_loop.run_sync(app.proxy.get_routes)
    assert unquote(mockservice.proxy_path) in routes
    io_loop.run_sync(mockservice.server.wait_up)
    path = '/services/{}/foo'.format(name)
    r = get_page(path, app, hub=False, allow_redirects=False)
    r.raise_for_status()
    assert r.status_code == 200
    assert r.text.endswith(path)


@pytest.mark.now
def test_external_service(app, io_loop):
    name = 'external'
    with external_service(app, name=name) as env:
        app.services = [{
            'name': name,
            'admin': True,
            'url': env['JUPYTERHUB_SERVICE_URL'],
            'api_token': env['JUPYTERHUB_API_TOKEN'],
        }]
        app.init_services()
        app.init_api_tokens()
        evt = Event()
        @gen.coroutine
        def add_services():
            yield app.proxy.add_all_services(app._service_map)
            evt.set()
        app.io_loop.add_callback(add_services)
        assert evt.wait(10)
        path = '/services/{}/api/users'.format(name)
        r = get_page(path, app, hub=False, allow_redirects=False)
        print(r.headers, r.status_code)
        r.raise_for_status()
        assert r.status_code == 200
        resp = r.json()
        assert isinstance(resp, list)
        assert len(resp) >= 1
        assert isinstance(resp[0], dict)
        assert 'name' in resp[0]
