
from concurrent.futures import ThreadPoolExecutor
import json
import os

from traitlets.config import SingletonConfigurable, Config
from traitlets import Any, Dict, Integer, List, default, validate

try:
    import privy
except ImportError:
    privy = None


KEY_ENV = 'JUPYTERHUB_CRYPT_KEY'

class EncryptionUnavailable(Exception):
    pass

class PrivyUnavailable(EncryptionUnavailable):
    def __str__(self):
        return "privy library is required for encryption"

class NoEncryptionKeys(EncryptionUnavailable):
    def __str__(self):
        return "Encryption keys must be specified in %s env" % KEY_ENV

class CryptKeeper(SingletonConfigurable):
    """Encapsulate encryption configuration

    Use via the encryption_config singleton below.
    """

    privy_kwargs = Dict({'server': True},
        help="""Keyword arguments to pass to privy.hide.
        
        For example, to 
        """
    )

    n_threads = Integer(max(os.cpu_count(), 1),
        help="The number of threads to allocate for encryption",
        config=True,
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
        return [ k.encode('ascii') for k in os.environ[KEY_ENV].split(';') if k.strip() ]

    @validate('keys')
    def _ensure_bytes(self, proposal):
        # cast str to bytes
        return [ (k.encode('ascii') if isinstance(k, str) else k) for k in proposal.value ]

    def check_available(self):
        if privy is None:
            raise PrivyUnavailable()
        if not self.keys:
            raise NoEncryptionKeys()

    def _encrypt(self, data):
        """Actually do the encryption. Runs in a background thread.
        
        data is serialized to bytes with pickle.
        bytes are returned.
        """
        return privy.hide(json.dumps(data).encode('utf8'), self.keys[0], **self.privy_kwargs).encode('ascii')

    def encrypt(self, data):
        """Encrypt an object with privy"""
        self.check_available()
        return self.executor.submit(self._encrypt, data)

    def _decrypt(self, encrypted):
        for key in self.keys:
            try:
                decrypted = privy.peek(encrypted, key)
            except ValueError as e:
                continue
            else:
                break
        else:
            raise ValueError("Failed to decrypt %r" % encrypted)
        return json.loads(decrypted.decode('utf8'))

    def decrypt(self, encrypted):
        """Decrypt an object with privy"""
        self.check_available()
        return self.executor.submit(self._decrypt, encrypted)


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
    