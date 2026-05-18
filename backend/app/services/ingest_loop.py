"""
Production ingestion loop — runs ingest_v2.run_ingestion() every 15 minutes.
Also runs Google Trends every 30 minutes and Wikipedia daily.
Designed for Docker/Fly.io: no PID files, no macOS dependencies.
"""
import asyncio
import logging
import os
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ingest] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

INTERVAL_SECONDS = int(os.getenv("INGEST_INTERVAL_SECONDS", "900"))  # 15 min default
NLP_ENRICH_LIMIT = int(os.getenv("NLP_ENRICH_LIMIT", "100"))
# When the standalone nlp_worker process group is live, set NLP_INLINE_ENABLED=false
# so this loop stops processing rows and avoids double-writes.
NLP_INLINE_ENABLED = os.getenv("NLP_INLINE_ENABLED", "true").lower() != "false"


async def _nlp_background(limit: int) -> None:
    try:
        log.info("NLP enrichment starting (limit=%d)...", limit)
        from enrichment.nlp_pipeline import run_nlp_enrichment
        await run_nlp_enrichment(limit=limit)
        log.info("NLP enrichment complete.")
    except Exception:
        log.exception("NLP enrichment failed")


async def main():
    from app.services.ingest_v2 import run_ingestion

    log.info("Ingestion loop starting (interval=%ds)", INTERVAL_SECONDS)

    gdelt_cycle = 0  # Counts GDELT cycles
    nlp_task: asyncio.Task | None = None

    while True:
        gdelt_cycle += 1

        # ── GDELT GKG & Events: every cycle (15 min) ──
        try:
            log.info("GDELT cycle %d start %s", gdelt_cycle, datetime.utcnow().isoformat())
            await run_ingestion()

            # Now run events ingestion right after GKG
            from app.services.ingest_events import run_events_ingestion
            await run_events_ingestion()

            log.info("GDELT cycle complete.")
        except Exception:
            log.exception("GDELT ingestion cycle failed — continuing")

        # ── NLP enrichment: background task, non-blocking (Wave 4 ADR-0003) ──
        # When the standalone nlp_worker process is live, set NLP_INLINE_ENABLED=false
        # so this branch becomes a no-op and the worker owns the NLP path (issue #163).
        if NLP_INLINE_ENABLED:
            if nlp_task is None or nlp_task.done():
                nlp_task = asyncio.create_task(_nlp_background(limit=NLP_ENRICH_LIMIT))
            else:
                log.info("NLP still running from previous cycle — skipping.")
        else:
            log.debug("Inline NLP disabled (NLP_INLINE_ENABLED=false) — worker handles it.")

        # ── Google Trends: every 2nd cycle (~30 min) ──
        if gdelt_cycle % 2 == 0:
            try:
                log.info("Google Trends ingestion starting...")
                from app.services.ingest_trends import run_trends_ingestion
                await run_trends_ingestion()
                log.info("Google Trends ingestion complete.")
            except Exception:
                log.exception("Google Trends ingestion failed — continuing")

        # ── ACLED Conflicts: every 4th cycle (~60 min) ──
        if gdelt_cycle % 4 == 0:
            try:
                log.info("ACLED Conflict ingestion starting...")
                from app.services.ingest_acled import run_acled_ingestion
                await run_acled_ingestion()
                log.info("ACLED Conflict ingestion complete.")
            except Exception:
                log.exception("ACLED ingestion failed — continuing")

        # ── RSS Curated Feeds: every 4th cycle (~60 min) ──
        if gdelt_cycle % 4 == 0:
            try:
                log.info("RSS curated feeds ingestion starting...")
                from app.services.ingest_rss import run_rss_ingestion
                await run_rss_ingestion()
                log.info("RSS ingestion complete.")
            except Exception:
                log.exception("RSS ingestion failed — continuing")

        # ── ReliefWeb/OCHA Humanitarian Feeds: every 4th cycle (~60 min) ──
        if gdelt_cycle % 4 == 0:
            try:
                log.info("ReliefWeb humanitarian feeds ingestion starting...")
                from app.services.ingest_reliefweb import run_reliefweb_ingestion
                await run_reliefweb_ingestion()
                log.info("ReliefWeb ingestion complete.")
            except Exception:
                log.exception("ReliefWeb ingestion failed — continuing")

        # ── NewsData.io Multilingual: every 4th cycle (~60 min) ──
        if gdelt_cycle % 4 == 0:
            try:
                log.info("NewsData.io multilingual ingestion starting...")
                from app.services.ingest_newsdata import run_newsdata_ingestion
                await run_newsdata_ingestion()
                log.info("NewsData.io ingestion complete.")
            except Exception:
                log.exception("NewsData.io ingestion failed — continuing")

        # ── Reddit Social Signals: every 4th cycle (~60 min) ──
        if gdelt_cycle % 4 == 0:
            try:
                log.info("Reddit social signals ingestion starting...")
                from app.services.ingest_reddit import run_reddit_ingestion
                await run_reddit_ingestion()
                log.info("Reddit ingestion complete.")
            except Exception:
                log.exception("Reddit ingestion failed — continuing")

        # ── MediaStack ES/PT: every 8th cycle (~2 hours) ──
        if gdelt_cycle % 8 == 0:
            try:
                log.info("MediaStack ES/PT ingestion starting...")
                from app.services.ingest_mediastack import run_mediastack_ingestion
                await run_mediastack_ingestion()
                log.info("MediaStack ingestion complete.")
            except Exception:
                log.exception("MediaStack ingestion failed — continuing")

        # ── NewsAPI.org Targeted Crisis: every 8th cycle (~2 hours) ──
        if gdelt_cycle % 8 == 4:  # offset from MediaStack to spread load
            try:
                log.info("NewsAPI.org targeted crisis ingestion starting...")
                from app.services.ingest_newsapi import run_newsapi_ingestion
                await run_newsapi_ingestion()
                log.info("NewsAPI.org ingestion complete.")
            except Exception:
                log.exception("NewsAPI.org ingestion failed — continuing")

        # ── Wikipedia Pageviews: every 96th cycle (~24 hours) ──
        if gdelt_cycle % 96 == 1:  # Run on first cycle and then every ~24h
            try:
                log.info("Wikipedia pageviews ingestion starting...")
                from app.services.ingest_wiki import run_wiki_ingestion
                await run_wiki_ingestion()
                log.info("Wikipedia pageviews ingestion complete.")
            except Exception:
                log.exception("Wikipedia pageviews ingestion failed — continuing")

        # ── Atlas composite heat refresh: every cycle (~15 min) ──
        # country_heat_v2 materialised view (migration 017). Refresh CONCURRENTLY
        # so we never block readers. Skip on any failure — the previous snapshot
        # remains valid until the next attempt.
        try:
            import asyncpg as _asyncpg
            _db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
            if _db_url:
                _conn = await _asyncpg.connect(_db_url)
                try:
                    try:
                        await _conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY country_heat_v2")
                    except Exception:
                        await _conn.execute("REFRESH MATERIALIZED VIEW country_heat_v2")
                    log.info("country_heat_v2 refreshed.")
                finally:
                    await _conn.close()
        except Exception:
            log.exception("country_heat_v2 refresh failed — continuing")

        # ── Data retention cleanup: every 672nd cycle (~7 days) ──
        if gdelt_cycle % 672 == 2:
            try:
                import asyncpg, os as _os
                db_url = _os.environ.get("DATABASE_URL") or _os.environ.get("SUPABASE_DB_URL")
                if db_url:
                    log.info("Retention cleanup starting (deleting unprocessed signals >90 days)...")
                    _conn = await asyncpg.connect(db_url)
                    result = await _conn.execute("""
                        DELETE FROM signals_v2
                        WHERE nlp_processed_at IS NULL
                          AND created_at < NOW() - INTERVAL '90 days'
                    """)
                    await _conn.close()
                    log.info("Retention cleanup complete: %s", result)
            except Exception:
                log.exception("Retention cleanup failed — continuing")

        log.info("Sleeping %ds.", INTERVAL_SECONDS)
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
