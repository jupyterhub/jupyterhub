import os

import pytest
from unittest.mock import patch

from .. import crypto
from ..crypto import encrypt, decrypt

@pytest.mark.parametrize("key_env, keys", [
    ("secret", [b'secret']),
    ("secret1;secret2", [b'secret1', b'secret2']),
    ("secret1;secret2;", [b'secret1', b'secret2']),
    ("", []),
])
def test_env_constructor(key_env, keys):
    with patch.dict(os.environ, {crypto.KEY_ENV: key_env}):
        ck = crypto.CryptKeeper()
        assert ck.keys == keys

@pytest.fixture
def crypt_keeper():
    """Fixture configuring and returning the global CryptKeeper instance"""
    ck = crypto.CryptKeeper.instance()
    save_keys = ck.keys
    ck.keys = [os.urandom(32), os.urandom(32)]
    try:
        yield ck
    finally:
        ck.keys = save_keys

@pytest.mark.gen_test
def test_roundtrip(crypt_keeper):
    data = {'key': 'value'}
    encrypted = yield encrypt(data)
    decrypted = yield decrypt(encrypted)
    assert decrypted == data

@pytest.mark.gen_test
def test_missing_privy(crypt_keeper):
    with patch.object(crypto, 'privy', None):
        with pytest.raises(crypto.PrivyUnavailable):
            yield encrypt({})

        with pytest.raises(crypto.PrivyUnavailable):
            yield decrypt(b'whatever')

@pytest.mark.gen_test
def test_missing_keys(crypt_keeper):
    crypt_keeper.keys = []
    with pytest.raises(crypto.NoEncryptionKeys):
        yield encrypt({})

    with pytest.raises(crypto.NoEncryptionKeys):
        yield decrypt(b'whatever')

