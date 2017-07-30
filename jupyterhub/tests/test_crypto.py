from binascii import b2a_hex, b2a_base64
import os

import pytest
from unittest.mock import patch

from .. import crypto
from ..crypto import encrypt, decrypt

keys = [('%i' % i).encode('ascii') * 32 for i in range(3)]
hex_keys = [ b2a_hex(key).decode('ascii') for key in keys ]
b64_keys = [ b2a_base64(key).decode('ascii').strip() for key in keys ]

@pytest.mark.parametrize("key_env, keys", [
    (hex_keys[0], [keys[0]]),
    (';'.join([b64_keys[0], hex_keys[1]]), keys[:2]),
    (';'.join([hex_keys[0], b64_keys[1], '']), keys[:2]),
    ('', []),
    (';', []),
])
def test_env_constructor(key_env, keys):
    with patch.dict(os.environ, {crypto.KEY_ENV: key_env}):
        ck = crypto.CryptKeeper()
        assert ck.keys == keys
        if keys:
            assert ck.fernet is not None
        else:
            assert ck.fernet is None


@pytest.mark.parametrize("key", [
    'a' * 44, # base64, not 32 bytes
    ('%44s' % 'notbase64'), # not base64
    b'x' * 64, # not hex
    b'short', # not 32 bytes
])
def test_bad_keys(key):
    ck = crypto.CryptKeeper()
    with pytest.raises(ValueError):
        ck.keys = [key]


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
def test_missing_crypto(crypt_keeper):
    with patch.object(crypto, 'cryptography', None):
        with pytest.raises(crypto.CryptographyUnavailable):
            yield encrypt({})

        with pytest.raises(crypto.CryptographyUnavailable):
            yield decrypt(b'whatever')


@pytest.mark.gen_test
def test_missing_keys(crypt_keeper):
    crypt_keeper.keys = []
    with pytest.raises(crypto.NoEncryptionKeys):
        yield encrypt({})

    with pytest.raises(crypto.NoEncryptionKeys):
        yield decrypt(b'whatever')

