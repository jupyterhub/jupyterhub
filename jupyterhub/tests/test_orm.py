"""Tests for the ORM bits"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import socket

import pytest
from tornado import gen

from .. import orm
from .. import objects
from .. import crypto
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

    # test wrapper
    server = objects.Server(orm_server=server)
    assert server.host == 'http://%s:%i' % (socket.gethostname(), server.port)
    assert server.url == server.host + '/'
    assert server.bind_url == 'http://*:%i/' % server.port
    server.ip = '127.0.0.1'
    assert server.host == 'http://127.0.0.1:%i' % server.port
    assert server.url == server.host + '/'

    server.connect_ip = 'hub'
    assert server.host == 'http://hub:%i' % server.port
    assert server.url == server.host + '/'


def test_user(db):
    user = User(orm.User(name='kaylee'))
    db.add(user)
    db.commit()
    spawner = user.spawners['']
    spawner.orm_spawner.state = {'pid': 4234}
    assert user.name == 'kaylee'
    assert user.orm_spawners[''].state == {'pid': 4234}

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
    algo, rounds, salt, checksum = found.hashed.split(':')
    assert algo == orm.APIToken.algorithm
    assert rounds == '1'
    assert len(salt) == orm.APIToken.generated_salt_bytes * 2

    found = orm.APIToken.find(db, 'something else')
    assert found is None

    secret = 'super-secret-preload-token'
    token = user.new_api_token(secret, generated=False)
    assert token == secret
    assert len(user.api_tokens) == 3
    found = orm.APIToken.find(db, token=token)
    assert found.match(secret)
    algo, rounds, salt, _ = found.hashed.split(':')
    assert algo == orm.APIToken.algorithm
    assert rounds == str(orm.APIToken.rounds)
    assert len(salt) == 2 * orm.APIToken.salt_bytes

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


@pytest.mark.gen_test
def test_spawn_fails(db):
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
    
    with pytest.raises(RuntimeError) as exc:
        yield user.spawn()
    assert user.spawners[''].server is None
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


@pytest.mark.gen_test
def test_auth_state(db):
    user = User(orm.User(name='eve'))
    db.add(user.orm_user)
    db.commit()
    
    ck = crypto.CryptKeeper.instance()

    # starts empty
    assert user.encrypted_auth_state is None
    
    # can't set auth_state without keys
    state = {'key': 'value'}
    ck.keys = []
    with pytest.raises(crypto.EncryptionUnavailable):
        yield user.save_auth_state(state)

    assert user.encrypted_auth_state is None
    # saving/loading None doesn't require keys
    yield user.save_auth_state(None)
    current = yield user.get_auth_state()
    assert current is None

    first_key = os.urandom(32)
    second_key = os.urandom(32)
    ck.keys = [first_key]
    yield user.save_auth_state(state)
    assert user.encrypted_auth_state is not None
    decrypted_state = yield user.get_auth_state()
    assert decrypted_state == state
    
    # can't read auth_state without keys
    ck.keys = []
    auth_state = yield user.get_auth_state()
    assert auth_state is None

    # key rotation works
    db.rollback()
    ck.keys = [second_key, first_key]
    decrypted_state = yield user.get_auth_state()
    assert decrypted_state == state

    new_state = {'key': 'newvalue'}
    yield user.save_auth_state(new_state)
    db.commit()

    ck.keys = [first_key]
    db.rollback()
    # can't read anymore with new-key after encrypting with second-key
    decrypted_state = yield user.get_auth_state()
    assert decrypted_state is None

    yield user.save_auth_state(new_state)
    decrypted_state = yield user.get_auth_state()
    assert decrypted_state == new_state

    ck.keys = []
    db.rollback()

    decrypted_state = yield user.get_auth_state()
    assert decrypted_state is None

