"""mock utilities for testing"""
try:
    from unittest import mock
except ImportError:
    import mock

import getpass
import threading

from tornado.ioloop import IOLoop

from IPython.utils.py3compat import unicode_type

from ..spawner import LocalProcessSpawner
from ..app import JupyterHubApp
from ..auth import PAMAuthenticator
from .. import orm

def mock_authenticate(username, password, service='login'):
    # mimic simplepam's failure to handle unicode
    if isinstance(username, unicode_type):
        return False
    if isinstance(password, unicode_type):
        return False
    
    # just use equality for testing
    if password == username:
        return True


class MockSpawner(LocalProcessSpawner):
    
    def make_preexec_fn(self):
        # skip the setuid stuff
        return
    
    def _set_user_changed(self, name, old, new):
        pass

class MockPAMAuthenticator(PAMAuthenticator):
    def authenticate(self, *args, **kwargs):
        with mock.patch('simplepam.authenticate', mock_authenticate):
            return super(MockPAMAuthenticator, self).authenticate(*args, **kwargs)

class MockHubApp(JupyterHubApp):
    """HubApp with various mock bits"""
    # def start_proxy(self):
    #     pass
    def _authenticator_default(self):
        return '%s.%s' % (__name__, 'MockPAMAuthenticator')
    
    def _spawner_class_default(self):
        return '%s.%s' % (__name__, 'MockSpawner')
    
    def start(self, argv=None):
        evt = threading.Event()
        def _start():
            self.io_loop = IOLoop.current()
            # put initialize in start for SQLAlchemy threading reasons
            super(MockHubApp, self).initialize(argv=argv)

            # add some initial users - 1 admin, 1 non-admin
            admin = orm.User(name='admin', admin=True)
            user = orm.User(name='user')
            self.db.add(admin)
            self.db.add(user)
            self.db.commit()
            self.io_loop.add_callback(evt.set)
            super(MockHubApp, self).start()
        
        self._thread = threading.Thread(target=_start)
        self._thread.start()
        evt.wait(timeout=5)
    
    def stop(self):
        self.io_loop.add_callback(self.io_loop.stop)
        self._thread.join()

