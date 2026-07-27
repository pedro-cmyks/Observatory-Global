"""
Database Session Management

Handles PostgreSQL database connections using psycopg2 connection pooling.
Designed to be thread-safe and efficient.
"""

import logging
import threading
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseSessionManager:
    """
    Manages a pool of database connections.
    """
    _instance = None
    _pool = None
    _pool_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseSessionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Deliberately does NOT connect.

        `db_manager` at the bottom of this module is constructed at import time,
        so connecting here made `import app.db.session` dial the database —
        any importer (a test, a script, a tooling probe) blocked or failed on the
        import itself, before it could touch a single line of its own code. The
        pool is built on first use instead; see `_ensure_pool`.
        """

    def _ensure_pool(self):
        """Build the pool on first use.

        Double-checked under a lock: `get_cursor` is called from multiple
        threads, and without it two callers racing the first cursor would each
        build a ThreadedConnectionPool and one would be orphaned.
        """
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None:
                    self._initialize_pool()
        return self._pool

    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise

    @contextmanager
    def get_cursor(self) -> Generator[RealDictCursor, None, None]:
        """
        Get a database cursor from the pool.
        Yields a RealDictCursor (results accessible by column name).
        Automatically handles commit/rollback and putting connection back in pool.
        """
        conn = None
        conn_pool = self._ensure_pool()
        try:
            conn = conn_pool.getconn()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                conn_pool.putconn(conn)

    def close(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            # Drop the reference so a later get_cursor rebuilds instead of
            # handing out connections from a closed pool.
            self._pool = None
            logger.info("Database connection pool closed")

# Global instance
db_manager = DatabaseSessionManager()

def get_db():
    """Dependency for FastAPI endpoints (if needed directly)."""
    return db_manager
