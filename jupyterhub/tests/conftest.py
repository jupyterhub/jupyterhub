"""py.test fixtures"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from pytest import fixture

from .. import orm

# global session object
_session = None

@fixture
def session():
    global _session
    if _session is None:
        _session = orm.new_session('sqlite:///:memory:', echo=True)
    return _session
