"""py.test fixtures"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import logging

from pytest import fixture
from tornado import ioloop

from .. import orm
from ..utils import getuser_unicode

from .mocking import MockHubApp


# global db session object
_session_factory = None

@fixture
def db():
    """Get a db session"""

    global _session_factory
    if _session_factory is None:
        session = _session_factory()
        _session_factory = orm.new_session_factory(
            'sqlite:///:memory:',
            echo=True,
        )
        user = orm.User(
            name=getuser_unicode(),
            server=orm.Server(),
        )
        hub = orm.Hub(
            server=orm.Server(),
        )
        session.add(user)
        session.add(hub)
        session.commit()
        session.close()

    session = _session_factory()
    return session


@fixture
def io_loop():
    """Get the current IOLoop"""
    loop = ioloop.IOLoop()
    loop.make_current()
    return loop


@fixture(scope='module')
def app(request):
    app = MockHubApp.instance(log_level=logging.DEBUG)
    app.start([])
    request.addfinalizer(app.stop)
    return app
