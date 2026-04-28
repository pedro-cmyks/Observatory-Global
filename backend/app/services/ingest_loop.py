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


async def main():
    from app.services.ingest_v2 import run_ingestion

    log.info("Ingestion loop starting (interval=%ds)", INTERVAL_SECONDS)

    gdelt_cycle = 0  # Counts GDELT cycles

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

        # ── Wikipedia Pageviews: every 96th cycle (~24 hours) ──
        if gdelt_cycle % 96 == 1:  # Run on first cycle and then every ~24h
            try:
                log.info("Wikipedia pageviews ingestion starting...")
                from app.services.ingest_wiki import run_wiki_ingestion
                await run_wiki_ingestion()
                log.info("Wikipedia pageviews ingestion complete.")
            except Exception:
                log.exception("Wikipedia pageviews ingestion failed — continuing")

        log.info("Sleeping %ds.", INTERVAL_SECONDS)
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
