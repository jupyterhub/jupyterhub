"""py.test fixtures"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import logging
from getpass import getuser
from subprocess import TimeoutExpired
import time
from unittest import mock

from pytest import fixture, raises
from tornado import ioloop

from .. import orm
from ..utils import random_port

from .mocking import MockHub
from .test_services import mockservice_cmd

import jupyterhub.services.service


# global db session object
_db = None


@fixture
def db():
    """Get a global db session. Create if it does not exist."""
    global _db
    if _db is None:
        _db = orm.new_session_factory('sqlite:///:memory:')()
        user = orm.User(
            name=getuser(),
        )
        user.servers.append(orm.Server())
        hub = orm.Hub(
            server=orm.Server(),
        )
        _db.add(user)
        _db.add(hub)
        _db.commit()
    return _db


@fixture
def io_loop():
    """Create a Tornado IOLoop and make it current."""
    loop = ioloop.IOLoop()
    loop.make_current()
    return loop


@fixture(scope='module')
def app(request):
    """Start a Hub.

    The mock multi-user hub, `MockHub`, is a `traitlets.config.Application`
    singleton object.
    """
    app = MockHub.instance(log_level=logging.DEBUG)
    app.start([])

    def fin():
        """Clean up steps for hub at termination"""
        MockHub.clear_instance()
        app.stop()
    request.addfinalizer(fin)
    return app



class MockServiceSpawner(jupyterhub.services.service.ServiceSpawner):
    """Mock services for testing. For example, shorter poll intervals."""
    poll_interval = 1

_mock_service_counter = 0

def _mockservice(request, app, url=False):
    """Create a mock service."""
    name = 'mock-service'
    service_properties = {
        'name': name,
        'command': mockservice_cmd,
        'admin': True,
    }
    if url:
        service_properties['url'] = 'http://127.0.0.1:{}'.format(random_port())

    with mock.patch.object(jupyterhub.services.service, '_ServiceSpawner',
            MockServiceSpawner):
        app.services = [{
            'name': name,
            'command': mockservice_cmd,
            'url': 'http://127.0.0.1:{}'.format(random_port()),
            'admin': True,
        }]
        app.init_services()
        app.io_loop.add_callback(app.proxy.add_all_services, app._service_map)
        assert name in app._service_map

        service = app._service_map[name]
        app.io_loop.add_callback(service.start)
        def cleanup():
            service.stop()
            app.services[:] = []
            app._service_map.clear()
        request.addfinalizer(cleanup)
        for i in range(20):
            if not getattr(service, 'proc', False):
                time.sleep(0.2)

        # ensure process finishes starting
        with raises(TimeoutExpired):
            service.proc.wait(1)

    return service


@fixture
def mockservice(request, app):
    """Mock a hub managed service."""
    yield _mockservice(request, app, url=False)


@fixture
def mockservice_url(request, app):
    """Mock an externally managed service."""
    yield _mockservice(request, app, url=True)


@fixture
def no_patience(app):
    """Set slow-spawning and stopping timeouts to zero."""
    with mock.patch.dict(app.tornado_application.settings,
            {'slow_spawn_timeout': 0, 'slow_stop_timeout': 0}):
        yield
