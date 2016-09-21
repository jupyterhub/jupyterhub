"""Tests for services"""

from binascii import hexlify
from contextlib import contextmanager
import os
from subprocess import Popen
import sys
from threading import Event
import time

import requests
from tornado import gen
from tornado.ioloop import IOLoop


from .mocking import public_url
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


def test_proxy_service(app, mockservice_url, io_loop):
    service = mockservice_url
    name = service.name
    routes = io_loop.run_sync(app.proxy.get_routes)
    url = public_url(app, service) + '/foo'
    r = requests.get(url, allow_redirects=False)
    path = '/services/{}/foo'.format(name)
    r.raise_for_status()
    assert r.status_code == 200
    assert r.text.endswith(path)


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
        service = app._service_map[name]
        url = public_url(app, service) + '/api/users'
        path = '/services/{}/api/users'.format(name)
        r = requests.get(url, allow_redirects=False)
        r.raise_for_status()
        assert r.status_code == 200
        resp = r.json()
        assert isinstance(resp, list)
        assert len(resp) >= 1
        assert isinstance(resp[0], dict)
        assert 'name' in resp[0]


