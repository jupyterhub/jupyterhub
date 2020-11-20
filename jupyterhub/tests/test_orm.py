"""Tests for the ORM bits"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import os
import socket
from datetime import datetime
from datetime import timedelta
from unittest import mock

import pytest
from tornado import gen

from .. import crypto
from .. import objects
from .. import orm
from ..emptyclass import EmptyClass
from ..user import User
from .mocking import MockSpawner


def assert_not_found(db, ORMType, id):
    """Assert that an item with a given id is not found"""
    assert db.query(ORMType).filter(ORMType.id == id).first() is None


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

    server.connect_url = 'http://hub-url:%i/connect' % server.port
    assert server.host == 'http://hub-url:%i' % server.port

    server.bind_url = 'http://127.0.0.1/'
    assert server.port == 80

    check_connect_url = objects.Server(connect_url='http://127.0.0.1:80')
    assert check_connect_url.connect_url == 'http://127.0.0.1:80/'
    check_connect_url = objects.Server(connect_url='http://127.0.0.1:80/')
    assert check_connect_url.connect_url == 'http://127.0.0.1:80/'


def test_user(db):
    orm_user = orm.User(name='kaylee')
    db.add(orm_user)
    db.commit()
    user = User(orm_user)
    spawner = user.spawners['']
    spawner.orm_spawner.state = {'pid': 4234}
    assert user.name == 'kaylee'
    assert user.orm_spawners[''].state == {'pid': 4234}

    found = orm.User.find(db, 'kaylee')
    assert found.name == user.name
    found = orm.User.find(db, 'badger')
    assert found is None


def test_user_escaping(db):
    orm_user = orm.User(name='company\\user@company.com,\"quoted\"')
    db.add(orm_user)
    db.commit()
    user = User(orm_user)
    assert user.name == 'company\\user@company.com,\"quoted\"'
    assert user.escaped_name == 'company%5Cuser@company.com%2C%22quoted%22'
    assert user.json_escaped_name == 'company\\\\user@company.com,\\\"quoted\\\"'


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


def test_token_expiry(db):
    user = orm.User(name='parker')
    db.add(user)
    db.commit()
    now = datetime.utcnow()
    token = user.new_api_token(expires_in=60)
    orm_token = orm.APIToken.find(db, token=token)
    assert orm_token
    assert orm_token.expires_at is not None
    # approximate range
    assert orm_token.expires_at > now + timedelta(seconds=50)
    assert orm_token.expires_at < now + timedelta(seconds=70)
    the_future = mock.patch(
        'jupyterhub.orm.APIToken.now', lambda: now + timedelta(seconds=70)
    )
    with the_future:
        found = orm.APIToken.find(db, token=token)
    assert found is None
    # purging shouldn't delete non-expired tokens
    orm.APIToken.purge_expired(db)
    assert orm.APIToken.find(db, token=token)
    with the_future:
        orm.APIToken.purge_expired(db)
    assert orm.APIToken.find(db, token=token) is None
    # after purging, make sure we aren't in the user token list
    assert orm_token not in user.api_tokens


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
    server_id = server.id

    # deleting service should delete its server
    db.delete(service)
    db.commit()
    assert_not_found(db, orm.Server, server_id)


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


async def test_spawn_fails(db):
    orm_user = orm.User(name='aeofel')
    db.add(orm_user)
    db.commit()

    class BadSpawner(MockSpawner):
        async def start(self):
            raise RuntimeError("Split the party")

    user = User(
        orm_user, {'spawner_class': BadSpawner, 'config': None, 'statsd': EmptyClass()}
    )

    with pytest.raises(RuntimeError) as exc:
        await user.spawn()
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
    db.delete(user)
    db.commit()
    assert group.users == []


async def test_auth_state(db):
    orm_user = orm.User(name='eve')
    db.add(orm_user)
    db.commit()
    user = User(orm_user)

    ck = crypto.CryptKeeper.instance()

    # starts empty
    assert user.encrypted_auth_state is None

    # can't set auth_state without keys
    state = {'key': 'value'}
    ck.keys = []
    with pytest.raises(crypto.EncryptionUnavailable):
        await user.save_auth_state(state)

    assert user.encrypted_auth_state is None
    # saving/loading None doesn't require keys
    await user.save_auth_state(None)
    current = await user.get_auth_state()
    assert current is None

    first_key = os.urandom(32)
    second_key = os.urandom(32)
    ck.keys = [first_key]
    await user.save_auth_state(state)
    assert user.encrypted_auth_state is not None
    decrypted_state = await user.get_auth_state()
    assert decrypted_state == state

    # can't read auth_state without keys
    ck.keys = []
    auth_state = await user.get_auth_state()
    assert auth_state is None

    # key rotation works
    db.rollback()
    ck.keys = [second_key, first_key]
    decrypted_state = await user.get_auth_state()
    assert decrypted_state == state

    new_state = {'key': 'newvalue'}
    await user.save_auth_state(new_state)
    db.commit()

    ck.keys = [first_key]
    db.rollback()
    # can't read anymore with new-key after encrypting with second-key
    decrypted_state = await user.get_auth_state()
    assert decrypted_state is None

    await user.save_auth_state(new_state)
    decrypted_state = await user.get_auth_state()
    assert decrypted_state == new_state

    ck.keys = []
    db.rollback()

    decrypted_state = await user.get_auth_state()
    assert decrypted_state is None


def test_spawner_delete_cascade(db):
    user = orm.User(name='spawner-delete')
    db.add(user)
    db.commit()

    spawner = orm.Spawner(user=user)
    db.commit()
    spawner.server = server = orm.Server()
    db.commit()
    db.delete(spawner)
    server_id = server.id

    # delete the user
    db.delete(spawner)
    db.commit()

    # verify that server gets deleted
    assert_not_found(db, orm.Server, server_id)
    assert user.orm_spawners == {}


def test_user_delete_cascade(db):
    user = orm.User(name='db-delete')
    oauth_client = orm.OAuthClient(identifier='db-delete-client')
    db.add(user)
    db.add(oauth_client)
    db.commit()

    # create a bunch of objects that reference the User
    # these should all be deleted automatically when the user goes away
    user.new_api_token()
    api_token = user.api_tokens[0]
    spawner = orm.Spawner(user=user)
    db.commit()
    spawner.server = server = orm.Server()
    oauth_code = orm.OAuthCode(client=oauth_client, user=user)
    db.add(oauth_code)
    oauth_token = orm.OAuthAccessToken(
        client=oauth_client, user=user, grant_type=orm.GrantType.authorization_code
    )
    db.add(oauth_token)
    db.commit()

    # record all of the ids
    spawner_id = spawner.id
    server_id = server.id
    api_token_id = api_token.id
    oauth_code_id = oauth_code.id
    oauth_token_id = oauth_token.id

    # delete the user
    db.delete(user)
    db.commit()

    # verify that everything gets deleted
    assert_not_found(db, orm.APIToken, api_token_id)
    assert_not_found(db, orm.Spawner, spawner_id)
    assert_not_found(db, orm.Server, server_id)
    assert_not_found(db, orm.OAuthCode, oauth_code_id)
    assert_not_found(db, orm.OAuthAccessToken, oauth_token_id)


def test_oauth_client_delete_cascade(db):
    user = orm.User(name='oauth-delete')
    oauth_client = orm.OAuthClient(identifier='oauth-delete-client')
    db.add(user)
    db.add(oauth_client)
    db.commit()

    # create a bunch of objects that reference the User
    # these should all be deleted automatically when the user goes away
    oauth_code = orm.OAuthCode(client=oauth_client, user=user)
    db.add(oauth_code)
    oauth_token = orm.OAuthAccessToken(
        client=oauth_client, user=user, grant_type=orm.GrantType.authorization_code
    )
    db.add(oauth_token)
    db.commit()
    assert user.oauth_tokens == [oauth_token]

    # record all of the ids
    oauth_code_id = oauth_code.id
    oauth_token_id = oauth_token.id

    # delete the user
    db.delete(oauth_client)
    db.commit()

    # verify that everything gets deleted
    assert_not_found(db, orm.OAuthCode, oauth_code_id)
    assert_not_found(db, orm.OAuthAccessToken, oauth_token_id)
    assert user.oauth_tokens == []
    assert user.oauth_codes == []


def test_delete_token_cascade(db):
    user = orm.User(name='mobs')
    db.add(user)
    db.commit()
    user.new_api_token()
    api_token = user.api_tokens[0]
    db.delete(api_token)
    db.commit()
    assert user.api_tokens == []


def test_group_delete_cascade(db):
    user1 = orm.User(name='user1')
    user2 = orm.User(name='user2')
    group1 = orm.Group(name='group1')
    group2 = orm.Group(name='group2')
    db.add(user1)
    db.add(user2)
    db.add(group1)
    db.add(group2)
    db.commit()
    # add user to group via user.groups works
    user1.groups.append(group1)
    db.commit()
    assert user1 in group1.users

    # add user to group via groups.users works
    group1.users.append(user2)
    db.commit()
    assert user1 in group1.users
    assert user2 in group1.users
    assert group1 in user1.groups
    assert group1 in user2.groups

    # fill out the connections (no new concept)
    group2.users.append(user1)
    group2.users.append(user2)
    db.commit()
    assert user1 in group1.users
    assert user2 in group1.users
    assert user1 in group2.users
    assert user2 in group2.users
    assert group1 in user1.groups
    assert group1 in user2.groups
    assert group2 in user1.groups
    assert group2 in user2.groups

    # now start deleting
    # 1. remove group via user.groups
    user1.groups.remove(group2)
    db.commit()
    assert user1 not in group2.users
    assert group2 not in user1.groups

    # 2. remove user via group.users
    group1.users.remove(user2)
    db.commit()
    assert user2 not in group1.users
    assert group1 not in user2.groups

    # 3. delete group object
    db.delete(group2)
    db.commit()
    assert group2 not in user1.groups
    assert group2 not in user2.groups

    # 4. delete user object
    db.delete(user1)
    db.commit()
    assert user1 not in group1.users


def test_expiring_api_token(app, user):
    db = app.db
    token = orm.APIToken.new(expires_in=30, user=user)
    orm_token = orm.APIToken.find(db, token, kind='user')
    assert orm_token

    # purge_expired doesn't delete non-expired
    orm.APIToken.purge_expired(db)
    found = orm.APIToken.find(db, token)
    assert found is orm_token

    with mock.patch.object(
        orm.APIToken, 'now', lambda: datetime.utcnow() + timedelta(seconds=60)
    ):
        found = orm.APIToken.find(db, token)
        assert found is None
        assert orm_token in db.query(orm.APIToken)
        orm.APIToken.purge_expired(db)
        assert orm_token not in db.query(orm.APIToken)


def test_expiring_oauth_token(app, user):
    db = app.db
    token = "abc123"
    now = orm.OAuthAccessToken.now
    client = orm.OAuthClient(identifier="xxx", secret="yyy")
    db.add(client)
    orm_token = orm.OAuthAccessToken(
        token=token,
        grant_type=orm.GrantType.authorization_code,
        client=client,
        user=user,
        expires_at=now() + 30,
    )
    db.add(orm_token)
    db.commit()

    found = orm.OAuthAccessToken.find(db, token)
    assert found is orm_token
    # purge_expired doesn't delete non-expired
    orm.OAuthAccessToken.purge_expired(db)
    found = orm.OAuthAccessToken.find(db, token)
    assert found is orm_token

    with mock.patch.object(orm.OAuthAccessToken, 'now', lambda: now() + 60):
        found = orm.OAuthAccessToken.find(db, token)
        assert found is None
        assert orm_token in db.query(orm.OAuthAccessToken)
        orm.OAuthAccessToken.purge_expired(db)
        assert orm_token not in db.query(orm.OAuthAccessToken)


def test_expiring_oauth_code(app, user):
    db = app.db
    code = "abc123"
    now = orm.OAuthCode.now
    orm_code = orm.OAuthCode(code=code, expires_at=now() + 30)
    db.add(orm_code)
    db.commit()

    found = orm.OAuthCode.find(db, code)
    assert found is orm_code
    # purge_expired doesn't delete non-expired
    orm.OAuthCode.purge_expired(db)
    found = orm.OAuthCode.find(db, code)
    assert found is orm_code

    with mock.patch.object(orm.OAuthCode, 'now', lambda: now() + 60):
        found = orm.OAuthCode.find(db, code)
        assert found is None
        assert orm_code in db.query(orm.OAuthCode)
        orm.OAuthCode.purge_expired(db)
        assert orm_code not in db.query(orm.OAuthCode)
