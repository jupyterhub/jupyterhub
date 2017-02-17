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
    """Get a db session"""
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
    """Get the current IOLoop"""
    loop = ioloop.IOLoop()
    loop.make_current()
    return loop


@fixture(scope='module')
def app(request):
    """Mock a jupyterhub app for testing"""
    mocked_app = MockHub.instance(log_level=logging.DEBUG)
    mocked_app.start([])


    def fin():
        MockHub.clear_instance()
        mocked_app.stop()
    request.addfinalizer(fin)
    return mocked_app


# mock services for testing.
# Shorter intervals, etc.
class MockServiceSpawner(jupyterhub.services.service._ServiceSpawner):
    poll_interval = 1


def _mockservice(request, app, url=False):
    name = 'mock-service'
    spec = {
        'name': name,
        'command': mockservice_cmd,
        'admin': True,
    }
    if url:
        spec['url'] = 'http://127.0.0.1:%i' % random_port(),

    with mock.patch.object(jupyterhub.services.service, '_ServiceSpawner', MockServiceSpawner):
        app.services = [{
            'name': name,
            'command': mockservice_cmd,
            'url': 'http://127.0.0.1:%i' % random_port(),
            'admin': True,
        }]
        app.init_services()
        app.io_loop.add_callback(app.proxy.add_all_services, app._service_map)
        assert name in app._service_map
        service = app._service_map[name]
        app.io_loop.add_callback(service.start)
        request.addfinalizer(service.stop)
        for i in range(20):
            if not getattr(service, 'proc', False):
                time.sleep(0.2)
        # ensure process finishes starting
        with raises(TimeoutExpired):
            service.proc.wait(1)
    return service


@fixture
def mockservice(request, app):
    """Mock a service with no external service url"""
    yield _mockservice(request, app, url=False)


@fixture
def mockservice_url(request, app):
    """Mock a service with its own url to test external services"""
    yield _mockservice(request, app, url=True)


@fixture
def no_patience(app):
    """Set slow-spawning timeouts to zero"""
    with mock.patch.dict(app.tornado_application.settings,
                         {'slow_spawn_timeout': 0,
                          'slow_stop_timeout': 0}):
        yield
