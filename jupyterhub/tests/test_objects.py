"""Tests for basic object-wrappers"""

import socket
import pytest

from jupyterhub.objects import Server


@pytest.mark.parametrize(
    'bind_url, attrs',
    [
        (
            'http://abc:123',
            {
                'ip': 'abc',
                'port': 123,
                'host': 'http://abc:123',
                'url': 'http://abc:123/x/',
            }
        ),
        (
            'https://abc',
            {
                'ip': 'abc',
                'port': 443,
                'proto': 'https',
                'host': 'https://abc:443',
                'url': 'https://abc:443/x/',
            }
        ),
    ]
)
def test_bind_url(bind_url, attrs):
    s = Server(bind_url=bind_url, base_url='/x/')
    for attr, value in attrs.items():
        assert getattr(s, attr) == value


_hostname = socket.gethostname()


@pytest.mark.parametrize(
    'ip, port, attrs',
    [
        (
            '', 123,
            {
                'ip': '',
                'port': 123,
                'host': 'http://{}:123'.format(_hostname),
                'url': 'http://{}:123/x/'.format(_hostname),
                'bind_url': 'http://*:123/x/',
            }
        ),
        (
            '127.0.0.1', 999,
            {
                'ip': '127.0.0.1',
                'port': 999,
                'host': 'http://127.0.0.1:999',
                'url': 'http://127.0.0.1:999/x/',
                'bind_url': 'http://127.0.0.1:999/x/',
            }
        ),
    ]
)
def test_ip_port(ip, port, attrs):
    s = Server(ip=ip, port=port, base_url='/x/')
    for attr, value in attrs.items():
        assert getattr(s, attr) == value
