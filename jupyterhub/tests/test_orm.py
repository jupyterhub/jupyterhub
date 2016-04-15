"""Tests for the ORM bits"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import pytest
from tornado import gen

from .. import orm
from ..user import User
from .mocking import MockSpawner


def test_server(db):
    server = orm.Server()
    db.add(server)
    db.commit()
    assert server.ip == ''
    assert server.base_url == '/'
    assert server.proto == 'http'
    assert isinstance(server.port, int)
    assert isinstance(server.cookie_name, str)
    assert server.host == 'http://127.0.0.1:%i' % server.port
    assert server.url == server.host + '/'
    assert server.bind_url == 'http://*:%i/' % server.port
    server.ip = '127.0.0.1'
    assert server.host == 'http://127.0.0.1:%i' % server.port
    assert server.url == server.host + '/'


def test_proxy(db):
    proxy = orm.Proxy(
        auth_token='abc-123',
        public_server=orm.Server(
            ip='192.168.1.1',
            port=8000,
        ),
        api_server=orm.Server(
            ip='127.0.0.1',
            port=8001,
        ),
    )
    db.add(proxy)
    db.commit()
    assert proxy.public_server.ip == '192.168.1.1'
    assert proxy.api_server.ip == '127.0.0.1'
    assert proxy.auth_token == 'abc-123'


def test_hub(db):
    hub = orm.Hub(
        server=orm.Server(
            ip = '1.2.3.4',
            port = 1234,
            base_url='/hubtest/',
        ),
        
    )
    db.add(hub)
    db.commit()
    assert hub.server.ip == '1.2.3.4'
    hub.server.port == 1234
    assert hub.api_url == 'http://1.2.3.4:1234/hubtest/api'


def test_user(db):
    user = orm.User(name='kaylee',
        server=orm.Server(),
        state={'pid': 4234},
    )
    db.add(user)
    db.commit()
    assert user.name == 'kaylee'
    assert user.server.ip == ''
    assert user.state == {'pid': 4234}

    found = orm.User.find(db, 'kaylee')
    assert found.name == user.name
    found = orm.User.find(db, 'badger')
    assert found is None


def test_tokens(db):
    user = orm.User(name='inara')
    db.add(user)
    db.commit()
    token = user.new_api_token()
    assert any(t.match(token) for t in user.api_tokens)
    user.new_api_token()
    assert len(user.api_tokens) == 2
    found = orm.APIToken.find(db, token=token)
    assert found.match(token)
    found = orm.APIToken.find(db, 'something else')
    assert found is None

    secret = 'super-secret-preload-token'
    token = user.new_api_token(secret)
    assert token == secret
    assert len(user.api_tokens) == 3

    # raise ValueError on collision
    with pytest.raises(ValueError):
        user.new_api_token(token)
    assert len(user.api_tokens) == 3


def test_spawn_fails(db, io_loop):
    orm_user = orm.User(name='aeofel')
    db.add(orm_user)
    db.commit()
    
    class BadSpawner(MockSpawner):
        @gen.coroutine
        def start(self):
            raise RuntimeError("Split the party")
    
    user = User(orm_user, {
        'spawner_class': BadSpawner,
        'config': None,
    })
    
    with pytest.raises(Exception) as exc:
        io_loop.run_sync(user.spawn)
    assert user.server is None
    assert not user.running

