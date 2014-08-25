"""Tests for the ORM bits"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from .. import db

try:
    unicode
except NameError:
    # py3
    unicode = str


def test_server(session):
    server = db.Server()
    session.add(server)
    session.commit()
    assert server.ip == u'localhost'
    assert server.base_url == '/'
    assert server.proto == 'http'
    assert isinstance(server.port, int)
    assert isinstance(server.cookie_name, unicode)
    assert isinstance(server.cookie_secret, bytes)
    assert server.url == 'http://localhost:%i/' % server.port


def test_proxy(session):
    proxy = db.Proxy(
        auth_token=u'abc-123',
        public_server=db.Server(
            ip=u'192.168.1.1',
            port=8000,
        ),
        api_server=db.Server(
            ip=u'127.0.0.1',
            port=8001,
        ),
    )
    session.add(proxy)
    session.commit()
    assert proxy.public_server.ip == u'192.168.1.1'
    assert proxy.api_server.ip == u'127.0.0.1'
    assert proxy.auth_token == u'abc-123'


def test_hub(session):
    hub = db.Hub(
        server=db.Server(
            ip = u'1.2.3.4',
            port = 1234,
            base_url='/hubtest/',
        ),
        
    )
    session.add(hub)
    session.commit()
    assert hub.server.ip == u'1.2.3.4'
    hub.server.port == 1234
    assert hub.api_url == u'http://1.2.3.4:1234/hubtest/api'


def test_user(session):
    user = db.User(name=u'kaylee',
        server=db.Server(),
        state={'pid': 4234},
    )
    session.add(user)
    session.commit()
    assert user.name == u'kaylee'
    assert user.server.ip == u'localhost'
    assert user.state == {'pid': 4234}


def test_tokens(session):
    user = db.User(name=u'inara')
    session.add(user)
    session.commit()
    token = user.new_cookie_token()
    session.add(token)
    session.commit()
    assert token in user.cookie_tokens
    session.add(user.new_cookie_token())
    session.add(user.new_cookie_token())
    session.add(user.new_api_token())
    session.commit()
    assert len(user.api_tokens) == 1
    assert len(user.cookie_tokens) == 3
    
