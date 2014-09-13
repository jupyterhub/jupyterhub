"""py.test fixtures"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import getpass

from pytest import fixture
from tornado import ioloop

from .. import orm

from .mocking import MockHubApp


# global db session object
_db = None

@fixture
def db():
    """Get a db session"""
    global _db
    if _db is None:
        _db = orm.new_session('sqlite:///:memory:', echo=True)
        user = orm.User(
            name=getpass.getuser(),
            server=orm.Server(),
        )
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
    ioloop.IOLoop.clear_current()
    return ioloop.IOLoop.current()



@fixture
def app(request):
    app = MockHubApp()
    app.start([])
    request.addfinalizer(app.stop)
    return app
