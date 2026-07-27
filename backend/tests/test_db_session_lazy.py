"""`app.db.session` must not touch the database at import time.

The module builds a `db_manager` singleton at import. It used to connect inside
__init__, so `import app.db.session` opened a psycopg2 ThreadedConnectionPool —
importing the module was enough to dial the database, and any importer without a
reachable DB blocked or failed before running a line of its own code.

These tests pin the lazy contract: constructing is free, the pool appears on
first cursor, and it is built exactly once even under concurrent first use.
"""
from __future__ import annotations

import threading

import pytest

from app.db import session as db_session


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def cursor(self, cursor_factory=None):
        return _FakeCursor()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class _FakePool:
    def __init__(self, *args, **kwargs):
        self.checked_out = 0
        self.returned = 0
        self.closed = False
        self.conn = _FakeConn()

    def getconn(self):
        self.checked_out += 1
        return self.conn

    def putconn(self, conn):
        self.returned += 1

    def closeall(self):
        self.closed = True


@pytest.fixture
def manager(monkeypatch):
    """A manager with no pool yet and ThreadedConnectionPool stubbed out."""
    built: list[_FakePool] = []

    def fake_pool_ctor(*args, **kwargs):
        p = _FakePool(*args, **kwargs)
        built.append(p)
        return p

    monkeypatch.setattr(db_session.psycopg2.pool, "ThreadedConnectionPool", fake_pool_ctor)
    mgr = db_session.db_manager
    monkeypatch.setattr(mgr, "_pool", None, raising=False)
    yield mgr, built
    # never leave a stub pool on the process-wide singleton
    mgr._pool = None


def test_importing_the_module_does_not_connect():
    """The regression this file exists for: import must be side-effect free."""
    assert db_session.db_manager._pool is None, (
        "importing app.db.session opened a connection pool"
    )


def test_constructing_the_manager_does_not_connect(monkeypatch):
    def boom(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("constructing DatabaseSessionManager connected")

    monkeypatch.setattr(db_session.psycopg2.pool, "ThreadedConnectionPool", boom)
    monkeypatch.setattr(db_session.db_manager, "_pool", None, raising=False)
    assert db_session.DatabaseSessionManager() is db_session.db_manager


def test_pool_is_built_on_first_cursor(manager):
    mgr, built = manager
    assert built == []

    with mgr.get_cursor():
        pass

    assert len(built) == 1
    assert built[0].checked_out == 1
    assert built[0].returned == 1
    assert built[0].conn.committed is True


def test_pool_is_built_only_once_across_cursors(manager):
    mgr, built = manager
    for _ in range(3):
        with mgr.get_cursor():
            pass
    assert len(built) == 1, "pool rebuilt on a later cursor"
    assert built[0].checked_out == 3


def test_failure_rolls_back_and_returns_the_connection(manager):
    mgr, built = manager
    with pytest.raises(ValueError):
        with mgr.get_cursor():
            raise ValueError("boom")

    conn = built[0].conn
    assert conn.rolled_back is True
    assert conn.committed is False
    assert built[0].returned == 1, "connection leaked on the error path"


def test_close_lets_a_later_cursor_rebuild(manager):
    mgr, built = manager
    with mgr.get_cursor():
        pass
    mgr.close()
    assert built[0].closed is True
    assert mgr._pool is None

    with mgr.get_cursor():
        pass
    assert len(built) == 2, "get_cursor after close must not reuse a closed pool"


def test_concurrent_first_use_builds_exactly_one_pool(manager):
    """Without the lock in _ensure_pool, racing threads each build a pool and
    one is orphaned — connections leak with no owner to close them."""
    mgr, built = manager
    start = threading.Barrier(8)
    errors: list[BaseException] = []

    def worker():
        try:
            start.wait(timeout=5)
            with mgr.get_cursor():
                pass
        except BaseException as exc:  # pragma: no cover - surfaced by assert
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, errors
    assert len(built) == 1, f"{len(built)} pools built under concurrent first use"
