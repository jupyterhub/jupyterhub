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
    assert found.user is user
    assert found.service is None
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


def test_service_tokens(db):
    service = orm.Service(name='secret')
    db.add(service)
    db.commit()
    token = service.new_api_token()
    assert any(t.match(token) for t in service.api_tokens)
    service.new_api_token()
    assert len(service.api_tokens) == 2
    found = orm.APIToken.find(db, token=token)
    assert found.match(token)
    assert found.user is None
    assert found.service is service
    service2 = orm.Service(name='secret')
    db.add(service)
    db.commit()
    assert service2.id != service.id


def test_service_server(db):
    service = orm.Service(name='has_servers')
    db.add(service)
    db.commit()
    
    assert service.server is None
    server = service.server = orm.Server()
    assert service
    assert server.id is None
    db.commit()
    assert isinstance(server.id, int)
    

def test_token_find(db):
    service = db.query(orm.Service).first()
    user = db.query(orm.User).first()
    service_token = service.new_api_token()
    user_token = user.new_api_token()
    with pytest.raises(ValueError):
        orm.APIToken.find(db, 'irrelevant', kind='richard')
    # no kind, find anything
    found = orm.APIToken.find(db, token=user_token)
    assert found
    assert found.match(user_token)
    found = orm.APIToken.find(db, token=service_token)
    assert found
    assert found.match(service_token)

    # kind=user, only find user tokens
    found = orm.APIToken.find(db, token=user_token, kind='user')
    assert found
    assert found.match(user_token)
    found = orm.APIToken.find(db, token=service_token, kind='user')
    assert found is None

    # kind=service, only find service tokens
    found = orm.APIToken.find(db, token=service_token, kind='service')
    assert found
    assert found.match(service_token)
    found = orm.APIToken.find(db, token=user_token, kind='service')
    assert found is None


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


def test_groups(db):
    user = orm.User.find(db, name='aeofel')
    db.add(user)
    
    group = orm.Group(name='lives')
    db.add(group)
    db.commit()
    assert group.users == []
    assert user.groups == []
    group.users.append(user)
    db.commit()
    assert group.users == [user]
    assert user.groups == [group]
