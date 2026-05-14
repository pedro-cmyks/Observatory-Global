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

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
except ImportError:
    pass

# Add parent directory to path for indicator imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import indicator modules
try:
    from indicators.source_diversity import calculate_source_diversity, DIVERSITY_TOOLTIP
    from indicators.source_quality import calculate_source_quality, get_allowlist, get_denylist, QUALITY_TOOLTIP
    from indicators.normalized_volume import calculate_normalized_volume, VOLUME_TOOLTIP
    INDICATORS_AVAILABLE = True
except ImportError:
    INDICATORS_AVAILABLE = False

from app import db as _db

app = FastAPI(
    title="Observatory Global v2",
    description="Simplified real-time global narrative tracking",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@app.on_event("startup")
async def startup():
    """Create async connection pool on startup, with retry for connection saturation."""
    for attempt in range(10):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
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
        print(f"✅ Connected to Redis: {REDIS_URL}")
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
    geo, workspace, briefing, indicators, wiki, events, narratives,
)

app.include_router(stats.router)
app.include_router(trends.router)
app.include_router(signals.router)
app.include_router(themes.router)
app.include_router(search.router)
app.include_router(geo.router)
app.include_router(workspace.router)
app.include_router(briefing.router)
app.include_router(indicators.router)
app.include_router(wiki.router)
app.include_router(events.router)
app.include_router(narratives.router)
