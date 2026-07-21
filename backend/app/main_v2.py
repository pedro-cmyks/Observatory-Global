"""
Observatory Global v2 - Simplified Backend API

NO Docker orchestration
NO custom aggregation code
Direct async PostgreSQL queries to v2 schema
Hot-reload enabled with uvicorn --reload

SCHEMA SAFETY / TABLE MAPPINGS:
- /api/v2/trends, /api/v2/compare -> use signals_country_hourly, signals_theme_hourly, signals_source_hourly
- /api/v2/nodes (extended range)  -> uses country_daily_v2
- /api/v2/nodes (short range)     -> uses country_hourly_v2
- /api/v2/anomalies               -> uses country_baseline_stats
(Note: These tables DO exist in the live DB and are populated)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import os
import sys
import asyncio
from urllib.parse import urlsplit

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
except ImportError:
    pass

# Add parent directory to path for top-level package imports such as indicators/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db as _db
from app.services.thread_intelligence import DatabaseBusyError

app = FastAPI(
    title="Observatory Global v2",
    description="Simplified real-time global narrative tracking",
    version="2.0.0"
)

# Per-IP rate limiting (interim pre-accounts hardening — see
# docs/state/2026-07-06-security-audit.md). MUST be installed BEFORE CORS so
# CORSMiddleware stays outermost and 429 responses still carry CORS headers.
from app.rate_limit import install_rate_limiting
install_rate_limiting(app)

# CORS. Locked to ATLAS_CORS_ORIGINS (comma-separated) when set; otherwise
# falls back to open with a loud warning so a deploy is never silently
# broken, but the lock is a one-env-var flip for public launch.
_cors_origins_env = os.getenv("ATLAS_CORS_ORIGINS", "").strip()
if _cors_origins_env:
    _cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    print(f"🔒 CORS locked to: {_cors_origins}")
else:
    _cors_origins = ["*"]
    print("⚠️  ATLAS_CORS_ORIGINS unset — CORS open to '*'. Set it before public launch.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB-busy degradation (P1 incident class, 2026-07-12) ─────────────────────
# When the M1 batch jobs (embed cron / clustering / matview refresh / catchup)
# contend on the shared Supabase, serving queries hit statement timeouts and
# every affected endpoint returned a raw 500. Serve an honest 503 db_busy
# instead so clients can distinguish "service degraded, retry" from a bug.
# Handlers are registered on the app (Starlette ExceptionMiddleware, innermost)
# so the 503 flows back through rate-limit + CORS middleware normally.
import logging
from fastapi.responses import JSONResponse
from starlette.requests import Request as _StarletteRequest

_logger = logging.getLogger("atlas.api")


def _db_busy_response(request: _StarletteRequest, exc: Exception) -> JSONResponse:
    _logger.warning("db_busy on %s: %s: %s", request.url.path, type(exc).__name__, exc)
    return JSONResponse(
        {"reason": "db_busy", "detail": "database is busy — retry shortly"},
        status_code=503,
        headers={"Retry-After": "10"},
    )


async def _handle_db_busy(request: _StarletteRequest, exc: Exception) -> JSONResponse:
    return _db_busy_response(request, exc)


# Statement timeout ("canceling statement due to statement timeout") — the
# exact error class from the incident tracebacks.
app.add_exception_handler(asyncpg.exceptions.QueryCanceledError, _handle_db_busy)
# Pooler saturation / dropped connections during heavy batch windows.
app.add_exception_handler(asyncpg.exceptions.TooManyConnectionsError, _handle_db_busy)
app.add_exception_handler(asyncpg.exceptions.ConnectionDoesNotExistError, _handle_db_busy)
# Client-side command/pool timeout translated only inside a known database
# serving boundary. Generic TimeoutError remains a 500 and is never mislabeled.
app.add_exception_handler(DatabaseBusyError, _handle_db_busy)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _safe_netloc(url: str) -> str:
    """Return host:port for connection logs without exposing credentials."""
    parsed = urlsplit(url)
    host = parsed.hostname or "unknown"
    return f"{host}:{parsed.port}" if parsed.port else host


@app.on_event("startup")
async def startup():
    """Create async connection pool on startup, with retry for connection saturation."""
    for attempt in range(10):
        try:
            pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=int(os.getenv("ATLAS_DB_POOL_MIN", "2")),
                # Raised from 5 to reduce full-API DoS via connection exhaustion
                # (external-depth holds a conn ~25s). Keep under the Supabase
                # pooler cap; tune via env if the pooler rejects connections.
                max_size=int(os.getenv("ATLAS_DB_POOL_MAX", "10")),
            )
            app.state.pool = pool
            _db.pool = pool
            print(f"✅ Connected to database: {DATABASE_URL.split('@')[1]}")
            break
        except Exception as e:
            if attempt < 9:
                wait = (attempt + 1) * 5
                print(f"⚠️  DB connect attempt {attempt+1} failed ({e}), retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"❌ DB connect failed after 10 attempts: {e}")
                raise

    # Optional Redis connection for caching
    try:
        import redis.asyncio as aioredis
        app.state.redis = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await app.state.redis.ping()
        print(f"✅ Connected to Redis: {_safe_netloc(REDIS_URL)}")
    except Exception as e:
        print(f"⚠️  Redis unavailable (caching disabled): {e}")
        app.state.redis = None

    # AISStream background task for maritime vessel tracking
    from app.routers.geo import _aisstream_background
    app.state.aisstream_task = asyncio.create_task(_aisstream_background())


@app.on_event("shutdown")
async def shutdown():
    """Close connection pool on shutdown."""
    await app.state.pool.close()
    if hasattr(app.state, "redis") and app.state.redis:
        await app.state.redis.close()


# ── Routers ──────────────────────────────────────────────────────────────────
from app.routers import (
    stats, trends, signals, themes, search,
    geo, workspace, briefing, indicators, wiki, events, narratives, heat,
    nlp_corrections, threads, emergent, translate, waitlist, research,
    voice_mix, public_attention, telemetry, attention_threads, universe,
    dossier, delight, archive_search, investigation, attention_eclipse,
    corroborate, research_articles, edges, focus_timeline,
)

app.include_router(stats.router)
app.include_router(archive_search.router)
app.include_router(trends.router)
app.include_router(signals.router)
app.include_router(public_attention.router)
app.include_router(attention_threads.router)
app.include_router(attention_eclipse.router)
app.include_router(universe.router)
app.include_router(telemetry.router)
app.include_router(themes.router)
app.include_router(search.router)
app.include_router(geo.router)
app.include_router(workspace.router)
app.include_router(briefing.router)
app.include_router(indicators.router)
app.include_router(wiki.router)
app.include_router(events.router)
app.include_router(narratives.router)
app.include_router(heat.router)
app.include_router(nlp_corrections.router)
app.include_router(threads.router)
app.include_router(emergent.router)
app.include_router(translate.router)
app.include_router(waitlist.router)
app.include_router(research.router)
app.include_router(research_articles.router)
app.include_router(research_articles.leads_router)
app.include_router(investigation.router)
app.include_router(voice_mix.router)
app.include_router(dossier.router)
app.include_router(corroborate.router)
app.include_router(delight.router)
app.include_router(edges.router)
app.include_router(focus_timeline.router)
