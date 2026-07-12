"""DB-busy degradation (P1 incident class, 2026-07-12).

When M1 batch jobs contend on the shared Supabase, serving queries die with
statement timeouts (asyncpg QueryCanceledError) or pool/command TimeoutError.
These must surface as an honest 503 {"reason": "db_busy"} — never a raw 500 —
and the response must flow back through the rate-limit + CORS middleware.

Tests run against the REAL app (real middleware stack + exception handlers);
TestClient without a context manager never fires startup, so no DB is needed.
"""

import asyncio

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.main_v2 import app

# Test-only routes that simulate the incident failure modes.


@app.get("/__test__/statement-timeout")
async def _raise_statement_timeout():
    raise asyncpg.exceptions.QueryCanceledError(
        "canceling statement due to statement timeout"
    )


@app.get("/__test__/pool-timeout")
async def _raise_pool_timeout():
    raise TimeoutError()


@app.get("/__test__/asyncio-timeout")
async def _raise_asyncio_timeout():
    raise asyncio.TimeoutError()


@app.get("/__test__/conn-gone")
async def _raise_conn_gone():
    raise asyncpg.exceptions.ConnectionDoesNotExistError(
        "connection was closed in the middle of operation"
    )


client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "path",
    [
        "/__test__/statement-timeout",
        "/__test__/pool-timeout",
        "/__test__/asyncio-timeout",
        "/__test__/conn-gone",
    ],
)
def test_db_timeouts_return_503_db_busy(path):
    r = client.get(path)
    assert r.status_code == 503, f"{path} -> {r.status_code} (want 503, not raw 500)"
    body = r.json()
    assert body["reason"] == "db_busy"
    assert r.headers.get("retry-after") == "10"


def test_db_busy_passes_through_cors_middleware():
    # The 503 must be readable cross-origin (CORS is the outermost middleware).
    r = client.get(
        "/__test__/statement-timeout",
        headers={"origin": "https://observatorio-global.vercel.app"},
    )
    assert r.status_code == 503
    # CORS fallback is "*" when ATLAS_CORS_ORIGINS is unset in the test env;
    # either way the header must be present.
    assert r.headers.get("access-control-allow-origin") is not None
