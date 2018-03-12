
import base64
from binascii import a2b_hex
from concurrent.futures import ThreadPoolExecutor
import json
import os

from traitlets.config import SingletonConfigurable, Config
from traitlets import (
    Any, Dict, Integer, List,
    default, observe, validate,
)

try:
    import cryptography
    from cryptography.fernet import Fernet, MultiFernet, InvalidToken
except ImportError:
    cryptography = None
    class InvalidToken(Exception):
        pass

from .utils import maybe_future

KEY_ENV = 'JUPYTERHUB_CRYPT_KEY'

class EncryptionUnavailable(Exception):
    pass

class CryptographyUnavailable(EncryptionUnavailable):
    def __str__(self):
        return "cryptography library is required for encryption"

class NoEncryptionKeys(EncryptionUnavailable):
    def __str__(self):
        return "Encryption keys must be specified in %s env" % KEY_ENV


def _validate_key(key):
    """Validate and return a 32B key

    Args:
    key (bytes): The key to be validated.
        Can be:
        - base64-encoded (44 bytes)
        - hex-encoded (64 bytes)
        - raw 32 byte key

    Returns:
    key (bytes): raw 32B key
    """
    if isinstance(key, str):
        key = key.encode('ascii')

    if len(key) == 44:
        try:
            key = base64.urlsafe_b64decode(key)
        except ValueError:
            pass

    elif len(key) == 64:
        try:
            # 64B could be 32B, hex-encoded
            return a2b_hex(key)
        except ValueError:
            # not 32B hex
            pass

    if len(key) != 32:
        raise ValueError("Encryption keys must be 32 bytes, hex or base64-encoded.")

    return key

class CryptKeeper(SingletonConfigurable):
    """Encapsulate encryption configuration

    Use via the encryption_config singleton below.
    """

    n_threads = Integer(max(os.cpu_count(), 1), config=True,
        help="The number of threads to allocate for encryption",
    )

    @default('config')
    def _config_default(self):
        # load application config by default
        from .app import JupyterHub
        if JupyterHub.initialized():
            return JupyterHub.instance().config
        else:
            return Config()

    executor = Any()
    def _executor_default(self):
        return ThreadPoolExecutor(self.n_threads)

    keys = List(config=True)
    def _keys_default(self):
        if KEY_ENV not in os.environ:
            return []
        # key can be a ;-separated sequence for key rotation.
        # First item in the list is used for encryption.
        return [ _validate_key(key) for key in os.environ[KEY_ENV].split(';') if key.strip() ]

    @validate('keys')
    def _ensure_bytes(self, proposal):
        # cast str to bytes
        return [ _validate_key(key) for key in proposal.value ]

    fernet = Any()
    def _fernet_default(self):
        if cryptography is None or not self.keys:
            return None
        return MultiFernet([Fernet(base64.urlsafe_b64encode(key)) for key in self.keys])

    @observe('keys')
    def _update_fernet(self, change):
        self.fernet = self._fernet_default()

    def check_available(self):
        if cryptography is None:
            raise CryptographyUnavailable()
        if not self.keys:
            raise NoEncryptionKeys()

    def _encrypt(self, data):
        """Actually do the encryption. Runs in a background thread.

        data is serialized to bytes with pickle.
        bytes are returned.
        """
        return self.fernet.encrypt(json.dumps(data).encode('utf8'))

    def encrypt(self, data):
        """Encrypt an object with cryptography"""
        self.check_available()
        return maybe_future(self.executor.submit(self._encrypt, data))

    def _decrypt(self, encrypted):
        decrypted = self.fernet.decrypt(encrypted)
        return json.loads(decrypted.decode('utf8'))

    def decrypt(self, encrypted):
        """Decrypt an object with cryptography"""
        self.check_available()
        return maybe_future(self.executor.submit(self._decrypt, encrypted))


def encrypt(data):
    """encrypt some data with the crypt keeper.

    data will be serialized with pickle.
    Returns a Future whose result will be bytes.
    """
    return CryptKeeper.instance().encrypt(data)

def decrypt(data):
    """decrypt some data with the crypt keeper

    Returns a Future whose result will be the decrypted, deserialized data.
    """
    return CryptKeeper.instance().decrypt(data)
