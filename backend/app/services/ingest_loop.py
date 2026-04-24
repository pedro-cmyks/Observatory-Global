"""
Production ingestion loop — runs ingest_v2.run_ingestion() every 15 minutes.
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
    while True:
        try:
            log.info("Cycle start %s", datetime.utcnow().isoformat())
            await run_ingestion()
            log.info("Cycle complete. Sleeping %ds.", INTERVAL_SECONDS)
        except Exception:
            log.exception("Ingestion cycle failed — retrying in 60s")
            await asyncio.sleep(60)
            continue
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
