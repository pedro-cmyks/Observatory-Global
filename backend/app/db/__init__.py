"""Database package.

Two layers live here:

* ``pool`` (below) — the shared asyncpg pool for the v2 serving path. It is
  created in ``app.main_v2.startup()`` and assigned onto this module, so every
  router can ``from app import db`` and reach it as ``db.pool``.
* ``base`` / ``session`` / ``repositories`` / ``seeds`` / ``migrations`` — the
  older SQLAlchemy + psycopg2 layer, still imported by ``app.models`` and a
  handful of services.

``pool`` is declared here at import time rather than being conjured onto the
module at startup. That is what makes the ``if db.pool is None:`` degrade guards
in the routers real code instead of a latent ``AttributeError``, and it lets
tests use a plain ``monkeypatch.setattr(db, "pool", ...)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - annotation only; keeps this import free
    import asyncpg

# None until app.main_v2.startup() creates the pool (and if creation failed).
pool: Optional[asyncpg.Pool] = None
