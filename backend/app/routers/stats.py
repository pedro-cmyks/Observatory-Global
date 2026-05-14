import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter
from app import db

router = APIRouter()

@router.get("/api/v2/stats")
async def get_system_stats():
    """
    System-wide database statistics.
    Shows total signals, time range, and ingestion health.
    """
    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 3000")

        async def safe_fetchval(query: str, default=0):
            try:
                value = await conn.fetchval(query)
                return default if value is None else value
            except Exception as e:
                print(f"⚠️  /api/v2/stats partial metric failed: {e}")
                return default

        # Avoid a full COUNT(*) over multi-million-row signals_v2. reltuples is approximate
        # but fast, and the dashboard only needs a coverage badge + rough system state.
        total_signals = await safe_fetchval("""
            SELECT COALESCE(reltuples::bigint, 0)
            FROM pg_class
            WHERE oid = 'signals_v2'::regclass
        """)
        oldest_signal = await safe_fetchval("""
            SELECT timestamp
            FROM signals_v2
            WHERE timestamp IS NOT NULL
            ORDER BY timestamp ASC
            LIMIT 1
        """, None)
        newest_signal = await safe_fetchval("""
            SELECT timestamp
            FROM signals_v2
            WHERE timestamp IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
        """, None)
        signals_1h = await safe_fetchval("""
            SELECT COUNT(*) FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '1 hour'
        """)
        signals_24h = await safe_fetchval("""
            SELECT COALESCE(SUM(signal_count), 0)::bigint
            FROM country_hourly_v2
            WHERE hour > NOW() - INTERVAL '24 hours'
        """)
        signals_7d = await safe_fetchval("""
            SELECT COALESCE(SUM(signal_count), 0)::bigint
            FROM country_hourly_v2
            WHERE hour > NOW() - INTERVAL '7 days'
        """)
        unique_countries = await safe_fetchval("""
            SELECT COUNT(DISTINCT country_code)
            FROM country_hourly_v2
            WHERE hour > NOW() - INTERVAL '24 hours'
        """)
        unique_sources = await safe_fetchval("""
            SELECT COUNT(DISTINCT source_name)
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)

        recent = await safe_fetchval("""
            SELECT COUNT(*) FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '2 hours'
        """)
        
        ingestion_status = "healthy" if recent > 100 else "stalled" if recent == 0 else "low"
        
        return {
            "database": {
                "total_signals": total_signals,
                "total_signals_estimated": True,
                "signals_1h": signals_1h,
                "signals_24h": signals_24h,
                "signals_7d": signals_7d,
                "unique_countries": unique_countries,
                "unique_sources": unique_sources,
                "oldest_signal": oldest_signal.isoformat() if oldest_signal else None,
                "newest_signal": newest_signal.isoformat() if newest_signal else None
            },
            "ingestion": {
                "status": ingestion_status,
                "signals_last_2h": recent
            },
            "retention": {
                "policy": "90 days raw (configurable)",
                "note": "Check data_lifecycle_config table for settings"
            }
        }


@router.get("/health")
async def health():
    """
    Health check endpoint with database connectivity and ingestion metrics.
    
    Returns:
        - status: 'healthy', 'degraded', or 'error'
        - db_ok: database connectivity status
        - last_ingest_ts: timestamp of most recent signal
        - ingest_lag_minutes: minutes since last ingestion
        - rows_ingested_last_15m: signals ingested in last 15 minutes
        - error_count_last_15m: placeholder for error tracking
    """
    try:
        async with db.pool.acquire(timeout=5) as conn:
            await conn.execute("SET statement_timeout = 5000")
            db_ok = True
            try:
                await conn.fetchval("SELECT 1", timeout=3.0)
            except Exception:
                db_ok = False

            # Total signals from materialized view (instant)
            view_result = await conn.fetchrow("""
                SELECT SUM(signal_count) as total_signals
                FROM country_hourly_v2
            """, timeout=5.0)
            total_signals = int(view_result['total_signals'] or 0) if view_result else 0

            # Actual last insert time and recent count from signals_v2 index (O(1) on timestamp idx)
            ingest_result = await conn.fetchrow("""
                SELECT
                    MAX(timestamp) as last_ts,
                    COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '30 minutes') as rows_30m
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '2 hours'
            """, timeout=5.0)

            last_ingest_ts = ingest_result['last_ts'] if ingest_result else None
            rows_ingested_last_15m = int(ingest_result['rows_30m'] or 0) if ingest_result else 0

            ingest_lag_minutes = None
            if last_ingest_ts:
                ts = last_ingest_ts.replace(tzinfo=timezone.utc) if last_ingest_ts.tzinfo is None else last_ingest_ts
                ingest_lag_minutes = (datetime.now(timezone.utc) - ts).total_seconds() / 60

            if not db_ok:
                status = "error"
            elif ingest_lag_minutes is None or ingest_lag_minutes > 90:
                status = "degraded"
            else:
                status = "healthy"

            return {
                "status": status,
                "db_ok": db_ok,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "last_ingest_ts": last_ingest_ts.isoformat() if last_ingest_ts else None,
                "ingest_lag_minutes": round(ingest_lag_minutes, 1) if ingest_lag_minutes else None,
                "rows_ingested_last_15m": rows_ingested_last_15m,
                "total_signals": total_signals,
                "error_count_last_15m": 0
            }
    except asyncio.TimeoutError:
        return {
            "status": "degraded",
            "db_ok": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "pool busy",
            "last_ingest_ts": None,
            "ingest_lag_minutes": None,
            "rows_ingested_last_15m": 0,
            "total_signals": 0,
            "error_count_last_15m": 0
        }
    except Exception as e:
        return {
            "status": "error",
            "db_ok": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": str(e),
            "last_ingest_ts": None,
            "ingest_lag_minutes": None,
            "rows_ingested_last_15m": 0,
            "total_signals": 0,
            "error_count_last_15m": 0
        }

# =============================================================================
# GOOGLE TRENDS API
# =============================================================================

@router.get("/")
async def root():
    """API root with available endpoints."""
    return {
        "name": "Observatory Global v2",
        "version": "2.0.0",
        "endpoints": {
            "nodes": "/api/v2/nodes?hours=24",
            "heatmap": "/api/v2/heatmap?hours=24",
            "flows": "/api/v2/flows?hours=24",
            "country": "/api/v2/country/{code}?hours=24",
            "health": "/health"
        },
        "docs": "/docs"
    }

# =============================================================================
# AIRCRAFT TRACKING (OpenSky Network – OAuth2 client_credentials)
# =============================================================================

# Aircraft callsign classification
# Military: known NATO/country prefixes; Government: VIP/state flights
_MIL_PREFIXES = {
    # US military
    "RCH", "PAT", "REACH", "DUKE", "VALOR", "ZEUS", "TOPCAT",
    "VENUS", "NAVY", "USAF", "ARMY",
    # UK
    "RAF", "RRR",
    # Germany
    "GAF", "GAFMED",
    # France
    "FAF", "CTM",
    # Israel
    "IAF",
    # NATO
    "NATO", "NATOEX",
    # Russia
    "RFF",
    # Other common military
    "MAGMA", "COBRA", "VIPER", "GHOST",
}
_GOV_PREFIXES = {"SAM", "AF1", "AF2", "EXEC", "VENUS0", "SPAR", "CAPS", "IRON"}
_ICAO24_MIL_RANGES = {
    # US DoD range AE0000–AFFFFF (partial)
    "ae", "af",
    # UK military 43
    "43",
}
