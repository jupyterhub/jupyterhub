"""Tests for the database-level Hub lock (jupyterhub.dblock)"""

import os

import pytest
from sqlalchemy import create_engine, text

from jupyterhub.dblock import DatabaseLock

TEST_DB_URL = os.environ.get("JUPYTERHUB_TEST_DB_URL", "")

needs_server_db = pytest.mark.skipif(
    not TEST_DB_URL.startswith(("postgresql", "mysql")),
    reason="requires JUPYTERHUB_TEST_DB_URL pointing at postgresql or mysql",
)
needs_postgres = pytest.mark.skipif(
    not TEST_DB_URL.startswith("postgresql"),
    reason="requires JUPYTERHUB_TEST_DB_URL pointing at postgresql",
)


def test_sqlite_is_noop(tmp_path):
    lock = DatabaseLock(f"sqlite:///{tmp_path}/hub.sqlite")
    assert lock.supported is False
    assert lock.try_acquire() is True
    assert lock.check() is True
    lock.release()
    # release is idempotent
    lock.release()


@pytest.mark.db
@needs_server_db
def test_second_lock_blocked_until_release():
    a = DatabaseLock(TEST_DB_URL)
    b = DatabaseLock(TEST_DB_URL)
    assert a.supported is True
    try:
        assert a.try_acquire() is True
        # re-acquiring on the same connection is fine
        assert a.try_acquire() is True
        assert b.try_acquire() is False
        assert a.check() is True
        a.release()
        assert b.try_acquire() is True
    finally:
        a.release()
        b.release()


@pytest.mark.db
@needs_postgres
def test_lost_connection_detected_and_reacquired():
    a = DatabaseLock(TEST_DB_URL)
    b = DatabaseLock(TEST_DB_URL)
    try:
        assert a.try_acquire() is True
        pid = a.backend_pid()
        assert pid
        # simulate the database dropping our session (failover, idle timeout, ...)
        with create_engine(TEST_DB_URL).connect() as conn:
            conn.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
        assert a.check() is False
        # the lock is gone with the session, so another Hub can take it
        assert b.try_acquire() is True
    finally:
        a.release()
        b.release()
