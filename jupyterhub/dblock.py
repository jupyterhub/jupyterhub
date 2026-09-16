"""Database-level lock guaranteeing a single active Hub per database.

JupyterHub assumes that exactly one Hub process talks to a given database
(see :mod:`jupyterhub.orm`). Nothing enforces this, so accidentally starting
two Hubs against the same database (for example ``replicas: 2`` in
Kubernetes) silently corrupts state.

:class:`DatabaseLock` uses the database server's own session-scoped locking
primitives to make that assumption explicit:

- PostgreSQL: ``pg_try_advisory_lock``
- MySQL / MariaDB: ``GET_LOCK``

Both are released automatically by the server when the holding session ends,
so a crashed Hub can never leave a stale lock behind. SQLite has no notion of
concurrent servers and is treated as a no-op.

The lock is held on a dedicated connection for the lifetime of the process.
That connection is never handed to SQLAlchemy's pool, and it runs in
autocommit mode so it never sits idle in a transaction.
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import hashlib
import logging

from sqlalchemy import create_engine, exc, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

# A fixed 64-bit key for pg_try_advisory_lock. The lock is scoped to the
# database, so one constant is enough to fence Hubs sharing a database.
LOCK_NAME = "jupyterhub-hub-lock"
LOCK_KEY = int.from_bytes(
    hashlib.sha256(LOCK_NAME.encode()).digest()[:8], "big", signed=True
)

# pool arguments don't make sense for the single dedicated connection
_POOL_KWARGS = {
    "max_overflow",
    "pool_pre_ping",
    "pool_recycle",
    "pool_size",
    "pool_timeout",
    "pool_use_lifo",
    "poolclass",
}


class DatabaseLock:
    """Exclusive, session-scoped lock on a JupyterHub database.

    Parameters
    ----------
    db_url : str
        SQLAlchemy URL of the Hub database.
    db_kwargs : dict, optional
        Extra keyword arguments for :func:`sqlalchemy.create_engine`.
        Connection-pool arguments are ignored.
    log : logging.Logger, optional
    """

    def __init__(self, db_url, db_kwargs=None, log=None):
        self.db_url = db_url
        self.db_kwargs = {
            k: v for k, v in (db_kwargs or {}).items() if k not in _POOL_KWARGS
        }
        self.log = log or logging.getLogger(__name__)
        self._url = make_url(db_url)
        self._engine = None
        self._conn = None

    @property
    def dialect(self):
        """Backend name, e.g. 'postgresql', 'mysql', 'sqlite'"""
        return self._url.get_backend_name()

    @property
    def supported(self):
        """Whether this database backend supports server-side locking"""
        return self.dialect in ("postgresql", "mysql", "mariadb")

    @property
    def held(self):
        """Whether we currently hold an open lock connection"""
        return self._conn is not None and not self._conn.closed

    # -- SQL per backend --------------------------------------------------

    def _mysql_lock_name(self):
        # MySQL named locks are server-wide, not per database
        return f"jupyterhub:{self._url.database}"

    def _acquire_sql(self):
        if self.dialect == "postgresql":
            return text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}
        else:
            return text("SELECT GET_LOCK(:name, 0)"), {"name": self._mysql_lock_name()}

    def _release_sql(self):
        if self.dialect == "postgresql":
            return text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY}
        else:
            return text("SELECT RELEASE_LOCK(:name)"), {"name": self._mysql_lock_name()}

    def _pid_sql(self):
        if self.dialect == "postgresql":
            return text("SELECT pg_backend_pid()")
        else:
            return text("SELECT CONNECTION_ID()")

    # -- connection management --------------------------------------------

    def _connect(self):
        if self._engine is None:
            self._engine = create_engine(
                self.db_url, poolclass=NullPool, **self.db_kwargs
            )
        if self._conn is None or self._conn.closed:
            # autocommit: never leave the lock session idle in a transaction
            self._conn = self._engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
            )
        return self._conn

    def _drop_connection(self):
        conn, self._conn = self._conn, None
        if conn is None:
            return
        try:
            conn.close()
        except Exception:
            pass

    # -- public API -------------------------------------------------------

    def try_acquire(self):
        """Try to acquire the lock without waiting.

        Returns True if the lock is held by this object after the call,
        False if another session holds it.

        Raises the underlying database error if the database is unreachable,
        so misconfiguration surfaces at startup instead of being mistaken for
        a held lock.
        """
        if not self.supported:
            self.log.debug(
                "Database backend %r does not support locking; "
                "assuming a single Hub",
                self.dialect,
            )
            return True
        conn = self._connect()
        sql, params = self._acquire_sql()
        try:
            result = conn.execute(sql, params).scalar()
        except exc.DBAPIError:
            self._drop_connection()
            raise
        # postgres returns bool, mysql returns 1/0/NULL
        return bool(result)

    def check(self):
        """Check that the connection holding the lock is still alive.

        If this returns False the server has already released our lock and
        another Hub may have acquired it.
        """
        if not self.supported:
            return True
        if not self.held:
            return False
        try:
            self._conn.execute(text("SELECT 1")).scalar()
        except exc.DBAPIError as e:
            self.log.warning("Database lock connection lost: %s", e.orig or e)
            self._drop_connection()
            return False
        return True

    def backend_pid(self):
        """Server-side id of the session holding the lock (for diagnostics)"""
        if not self.supported or not self.held:
            return None
        return self._conn.execute(self._pid_sql()).scalar()

    def release(self):
        """Release the lock and close the dedicated connection.

        Safe to call multiple times.
        """
        if self.held and self.supported:
            sql, params = self._release_sql()
            try:
                self._conn.execute(sql, params)
            except exc.DBAPIError:
                # closing the connection releases the lock anyway
                pass
        self._drop_connection()
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
