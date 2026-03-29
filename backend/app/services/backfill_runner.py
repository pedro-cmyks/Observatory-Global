#!/usr/bin/env python3
"""
GDELT Historical Backfill Runner for Observatory Global.

Fetches historical GDELT GKG data from official archives.
GDELT provides 15-minute update files at predictable URLs.

Usage:
    python3 -m backend.app.services.backfill_runner start --from 2025-12-30 --to 2026-01-13
    python3 -m backend.app.services.backfill_runner status
    python3 -m backend.app.services.backfill_runner stop

Rate limiting: ~1 req/sec (60 files/hour = 15 hours of data per hour)
Checkpoint: resumes from last successful file
Idempotent: ON CONFLICT DO NOTHING in DB
"""

import asyncio
import aiohttp
import asyncpg
import csv
import io
import json
import logging
import os
import signal
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Add parent directories for imports
PROJECT_ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.ingest_v2 import parse_gkg_row, insert_signals, update_countries
from app.config.crisis_themes import (
    is_crisis_theme, get_crisis_themes, calculate_crisis_score,
    calculate_severity, get_event_type
)

# Increase CSV field size limit for GDELT
csv.field_size_limit(10 * 1024 * 1024)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory")
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
CHECKPOINT_FILE = CHECKPOINT_DIR / "backfill.json"
LOG_DIR = PROJECT_ROOT / "logs"
PID_FILE = PROJECT_ROOT / ".run" / "backfill.pid"

# GDELT Archive URL pattern
# Format: http://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip
GDELT_ARCHIVE_URL = "http://data.gdeltproject.org/gdeltv2/{timestamp}.gkg.csv.zip"

# Rate limiting
DEFAULT_RATE = 1.0  # seconds between requests

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_gdelt_timestamps(from_date: datetime, to_date: datetime) -> list[str]:
    """
    Generate all GDELT 15-minute timestamps between two dates.
    GDELT publishes files at :00, :15, :30, :45 of each hour.
    """
    timestamps = []
    current = from_date.replace(minute=0, second=0, microsecond=0)
    
    while current <= to_date:
        for minute in [0, 15, 30, 45]:
            ts = current.replace(minute=minute)
            if from_date <= ts <= to_date:
                timestamps.append(ts.strftime("%Y%m%d%H%M%S"))
        current += timedelta(hours=1)
    
    return timestamps


def load_checkpoint() -> dict:
    """Load checkpoint from file."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
        except:
            pass
    return {
        "last_completed_timestamp": None,
        "total_files_processed": 0,
        "total_signals_inserted": 0,
        "started_at": None,
        "last_updated_at": None,
        "from_date": None,
        "to_date": None,
        "status": "idle"
    }


def save_checkpoint(checkpoint: dict):
    """Save checkpoint to file."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)


async def download_and_parse_historical_gkg(session: aiohttp.ClientSession, timestamp: str) -> list[dict]:
    """Download and parse a historical GDELT GKG file."""
    url = GDELT_ARCHIVE_URL.format(timestamp=timestamp)
    signals = []
    skipped = 0
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 404:
                logger.debug(f"File not found: {timestamp}")
                return []
            if resp.status != 200:
                logger.warning(f"Failed to download {timestamp}: HTTP {resp.status}")
                return []
            
            data = await resp.read()
    except asyncio.TimeoutError:
        logger.warning(f"Timeout downloading {timestamp}")
        return []
    except Exception as e:
        logger.warning(f"Error downloading {timestamp}: {e}")
        return []
    
    # Unzip and parse
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for filename in zf.namelist():
                if filename.endswith('.csv'):
                    with zf.open(filename) as f:
                        reader = csv.reader(
                            io.TextIOWrapper(f, encoding='utf-8', errors='replace'),
                            delimiter='\t'
                        )
                        for line_num, row in enumerate(reader, start=1):
                            try:
                                signal = parse_gkg_row(row)
                                if signal:
                                    signals.append(signal)
                            except Exception as e:
                                skipped += 1
                                continue
    except zipfile.BadZipFile:
        logger.warning(f"Bad zip file: {timestamp}")
        return []
    except Exception as e:
        logger.warning(f"Error processing {timestamp}: {e}")
        return []
    
    return signals


async def run_backfill(from_date: str, to_date: str, rate: float = DEFAULT_RATE):
    """
    Main backfill function.
    
    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        rate: Seconds between requests
    """
    # Parse dates
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(
        hour=23, minute=45, tzinfo=timezone.utc
    )
    
    # Generate all timestamps
    all_timestamps = generate_gdelt_timestamps(from_dt, to_dt)
    logger.info(f"Backfill range: {from_date} to {to_date} ({len(all_timestamps)} files)")
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    last_completed = checkpoint.get("last_completed_timestamp")
    
    # Find resume point
    start_idx = 0
    if last_completed and last_completed in all_timestamps:
        start_idx = all_timestamps.index(last_completed) + 1
        logger.info(f"Resuming from checkpoint: {last_completed} (file {start_idx}/{len(all_timestamps)})")
    
    remaining_timestamps = all_timestamps[start_idx:]
    if not remaining_timestamps:
        logger.info("All files already processed!")
        return
    
    # Update checkpoint
    checkpoint["from_date"] = from_date
    checkpoint["to_date"] = to_date
    checkpoint["started_at"] = checkpoint.get("started_at") or datetime.now(timezone.utc).isoformat()
    checkpoint["status"] = "running"
    save_checkpoint(checkpoint)
    
    # Save PID
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    # Setup graceful shutdown
    shutdown_requested = False
    def handle_shutdown(signum, frame):
        nonlocal shutdown_requested
        logger.info("Shutdown requested, finishing current file...")
        shutdown_requested = True
    
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Connect to database
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
    
    try:
        async with aiohttp.ClientSession() as session:
            for i, ts in enumerate(remaining_timestamps):
                if shutdown_requested:
                    logger.info("Shutting down gracefully...")
                    break
                
                absolute_idx = start_idx + i
                logger.info(f"[{absolute_idx + 1}/{len(all_timestamps)}] Processing {ts}...")
                
                # Download and parse
                signals = await download_and_parse_historical_gkg(session, ts)
                
                if signals:
                    # Insert
                    inserted = await insert_signals(pool, signals)
                    checkpoint["total_signals_inserted"] = checkpoint.get("total_signals_inserted", 0) + inserted
                    logger.info(f"  -> {len(signals)} parsed, {inserted} inserted")
                else:
                    logger.info(f"  -> No signals (file may not exist)")
                
                # Update checkpoint
                checkpoint["last_completed_timestamp"] = ts
                checkpoint["total_files_processed"] = checkpoint.get("total_files_processed", 0) + 1
                save_checkpoint(checkpoint)
                
                # Rate limit
                await asyncio.sleep(rate)
        
        # Update countries after backfill
        logger.info("Updating countries table...")
        await update_countries(pool)
        
        # Refresh materialized view
        logger.info("Refreshing aggregates...")
        async with pool.acquire() as conn:
            await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY country_hourly_v2")
        
        # Mark complete if not interrupted
        if not shutdown_requested:
            checkpoint["status"] = "completed"
            save_checkpoint(checkpoint)
            logger.info("Backfill completed!")
        else:
            checkpoint["status"] = "paused"
            save_checkpoint(checkpoint)
            logger.info("Backfill paused (can be resumed)")
    
    finally:
        await pool.close()
        if PID_FILE.exists():
            PID_FILE.unlink()


def show_status():
    """Show backfill status."""
    checkpoint = load_checkpoint()
    
    print("\n=== GDELT Backfill Status ===")
    print(f"Status: {checkpoint.get('status', 'idle')}")
    print(f"Range: {checkpoint.get('from_date')} to {checkpoint.get('to_date')}")
    print(f"Last completed: {checkpoint.get('last_completed_timestamp')}")
    print(f"Files processed: {checkpoint.get('total_files_processed', 0)}")
    print(f"Signals inserted: {checkpoint.get('total_signals_inserted', 0)}")
    print(f"Started: {checkpoint.get('started_at')}")
    print(f"Last updated: {checkpoint.get('last_updated_at')}")
    
    # Check if running
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            print(f"Process running: PID {pid}")
        except (ProcessLookupError, ValueError):
            print("Process: not running (stale PID file)")
    else:
        print("Process: not running")
    
    print()


def stop_backfill():
    """Stop the backfill process."""
    if not PID_FILE.exists():
        print("Backfill is not running")
        return
    
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to PID {pid}")
    except ProcessLookupError:
        print("Process not found (removing stale PID file)")
        PID_FILE.unlink()
    except Exception as e:
        print(f"Error stopping: {e}")


def reset_checkpoint():
    """Reset checkpoint to start fresh."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("Checkpoint reset")
    else:
        print("No checkpoint to reset")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="GDELT Historical Backfill Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start backfill")
    start_parser.add_argument("--from", dest="from_date", required=True, help="Start date (YYYY-MM-DD)")
    start_parser.add_argument("--to", dest="to_date", required=True, help="End date (YYYY-MM-DD)")
    start_parser.add_argument("--rate", type=float, default=1.0, help="Seconds between requests (default: 1.0)")
    
    # Status command
    subparsers.add_parser("status", help="Show backfill status")
    
    # Stop command
    subparsers.add_parser("stop", help="Stop backfill")
    
    # Reset command
    subparsers.add_parser("reset", help="Reset checkpoint")
    
    args = parser.parse_args()
    
    if args.command == "start":
        asyncio.run(run_backfill(args.from_date, args.to_date, args.rate))
    elif args.command == "status":
        show_status()
    elif args.command == "stop":
        stop_backfill()
    elif args.command == "reset":
        reset_checkpoint()


if __name__ == "__main__":
    main()
