"""mock utilities for testing"""

import os
import sys
from tempfile import NamedTemporaryFile
import threading

try:
    from unittest import mock
except ImportError:
    import mock

from tornado.ioloop import IOLoop

from six import text_type

from ..spawner import LocalProcessSpawner
from ..app import JupyterHubApp
from ..auth import PAMAuthenticator, Authenticator
from .. import orm

def mock_authenticate(username, password, service='login'):
    # mimic simplepam's failure to handle unicode
    if isinstance(username, text_type):
        return False
    if isinstance(password, text_type):
        return False
    
    # just use equality for testing
    if password == username:
        return True


class MockSpawner(LocalProcessSpawner):
    
    def make_preexec_fn(self, *a, **kw):
        # skip the setuid stuff
        return
    
    def _set_user_changed(self, name, old, new):
        pass
    
    def user_env(self, env):
        return env
    
    def _cmd_default(self):
        return [sys.executable, '-m', 'jupyterhub.tests.mocksu']


class MockPAMAuthenticator(PAMAuthenticator):
    def system_user_exists(self, user):
        # skip the add-system-user bit
        return not user.name.startswith('dne')
    
    def authenticate(self, *args, **kwargs):
        with mock.patch('simplepam.authenticate', mock_authenticate):
            return super(MockPAMAuthenticator, self).authenticate(*args, **kwargs)

class MockHubApp(JupyterHubApp):
    """HubApp with various mock bits"""

    db_file = None

    def _ip_default(self):
        return 'localhost'
    
    def _authenticator_class_default(self):
        return MockPAMAuthenticator
    
    def _spawner_class_default(self):
        return MockSpawner
    
    def _admin_users_default(self):
        return {'admin'}

    def start(self, argv=None):
        self.db_file = NamedTemporaryFile()
        self.db_url = 'sqlite:///' + self.db_file.name
        evt = threading.Event()
        def _start():
            self.io_loop = IOLoop.current()
            # put initialize in start for SQLAlchemy threading reasons
            super(MockHubApp, self).initialize(argv=argv)

            # add an initial user
            user = orm.User(name='user')
            self.db.add(user)
            self.db.commit()
            self.io_loop.add_callback(evt.set)
            super(MockHubApp, self).start()
        
        self._thread = threading.Thread(target=_start)
        self._thread.start()
        evt.wait(timeout=5)
    
    def stop(self):
        self.db_file.close()
        self.io_loop.add_callback(self.io_loop.stop)
        self._thread.join()
