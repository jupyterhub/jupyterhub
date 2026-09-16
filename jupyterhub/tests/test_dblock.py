"""Tests for the database-level Hub lock (jupyterhub.dblock)"""

import asyncio
import os

import pytest
from sqlalchemy import create_engine, text

from jupyterhub.dblock import DatabaseLock

from .mocking import MockHub
from .utils import async_requests

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


# -- application integration ---------------------------------------------


@pytest.fixture
async def hub_pair(request):
    """Two independent (non-singleton) MockHub instances sharing one database"""

    hubs = []

    def make(**kwargs):
        # these hubs are initialized but never started, so there's no proxy to stop
        kwargs.setdefault("cleanup_proxy", False)
        hub = MockHub(**kwargs)
        hubs.append(hub)
        return hub

    yield make

    for hub in hubs:
        if getattr(hub, "db", None) is not None:
            # fully initialized
            await hub.cleanup()
        elif hub._db_lock is not None:
            # exited before init_db, as a fenced Hub does
            hub._db_lock.release()


def test_db_lock_disabled_by_default():
    hub = MockHub()
    assert hub.db_lock is False
    assert hub.db_lock_timeout == 0
    assert hub.db_lock_check_interval == 5


@pytest.mark.db
@needs_server_db
async def test_app_second_hub_exits_when_locked(hub_pair):
    a = hub_pair(db_lock=True, db_lock_timeout=0)
    await a.initialize([])
    assert a._db_lock.held

    b = hub_pair(db_lock=True, db_lock_timeout=0)
    with pytest.raises(SystemExit):
        await b.initialize([])
    assert not b._db_lock.held


@pytest.mark.db
@needs_server_db
async def test_app_second_hub_times_out(hub_pair):
    a = hub_pair(db_lock=True, db_lock_timeout=0)
    await a.initialize([])

    b = hub_pair(db_lock=True, db_lock_timeout=1.5)
    loop = asyncio.get_running_loop()
    tic = loop.time()
    with pytest.raises(SystemExit):
        await b.initialize([])
    assert loop.time() - tic >= 1.5


@pytest.mark.db
@needs_server_db
async def test_app_standby_takes_over(hub_pair):
    a = hub_pair(db_lock=True, db_lock_timeout=-1)
    await a.initialize([])

    b = hub_pair(db_lock=True, db_lock_timeout=-1)
    task = asyncio.ensure_future(b.initialize([]))
    await asyncio.sleep(2)
    # still waiting: no lock, no database session
    assert not task.done()
    assert not b._db_lock.held
    assert getattr(b, "db", None) is None

    # graceful shutdown of the active hub releases the lock
    await a.cleanup()
    assert not a._db_lock.held
    await asyncio.wait_for(task, timeout=15)
    assert b._db_lock.held
    assert b.db is not None


@pytest.mark.db
@needs_server_db
async def test_app_standby_serves_health(hub_pair):
    a = hub_pair(db_lock=True, db_lock_timeout=-1)
    await a.initialize([])

    b = hub_pair(db_lock=True, db_lock_timeout=-1)
    task = asyncio.ensure_future(b.initialize([]))
    await asyncio.sleep(1.5)
    assert not task.done()
    assert b._standby_server is not None
    hub_url = b.hub.bind_url.rstrip("/")

    # liveness: alive
    r = await async_requests.get(hub_url + "/health")
    assert r.status_code == 200
    # readiness: not serving
    r = await async_requests.get(hub_url + "/api/health")
    assert r.status_code == 503
    assert r.json()["status"] == "standby"
    r = await async_requests.get(hub_url + "/api/users")
    assert r.status_code == 503

    await a.cleanup()
    await asyncio.wait_for(task, timeout=15)
    # the standby server is gone, the port is free for the real one
    assert b._standby_server is None
    with pytest.raises(Exception):
        await async_requests.get(hub_url + "/health", timeout=1)


@pytest.mark.db
@needs_server_db
async def test_app_lock_check_reacquires_after_lost_connection(hub_pair):
    a = hub_pair(db_lock=True)
    await a.initialize([])
    # drop the lock connection behind the hub's back
    a._db_lock._drop_connection()
    a._check_db_lock()
    assert a._db_lock.held


@pytest.mark.db
@needs_server_db
async def test_app_lock_check_exits_if_lock_taken(hub_pair):
    a = hub_pair(db_lock=True)
    await a.initialize([])
    a._db_lock._drop_connection()
    other = DatabaseLock(TEST_DB_URL)
    try:
        assert other.try_acquire()
        with pytest.raises(SystemExit):
            a._check_db_lock()
    finally:
        other.release()
