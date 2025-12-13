"""
Ingestion Supervisor for Observatory Global v3

Provides:
- Process locking to prevent duplicate ingestion processes
- Exponential backoff retry on failure
- Structured logging with batch metrics
- Clean shutdown handling
"""

import os
import sys
import time
import logging
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Any

LOCK_FILE = Path("/tmp/observatory_ingestion.lock")
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 30

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ingestion_supervisor")


class IngestionMetrics:
    """Track metrics for a single ingestion batch."""
    
    def __init__(self):
        self.batch_start: Optional[datetime] = None
        self.batch_end: Optional[datetime] = None
        self.rows_fetched: int = 0
        self.rows_inserted: int = 0
        self.rows_skipped: int = 0
        self.errors_by_source: dict = {}
        self.db_write_time_ms: int = 0
    
    def start_batch(self):
        """Mark the start of a new batch."""
        self.batch_start = datetime.now(timezone.utc)
        self.rows_fetched = 0
        self.rows_inserted = 0
        self.rows_skipped = 0
        self.errors_by_source = {}
        self.db_write_time_ms = 0
    
    def end_batch(self):
        """Mark the end of the batch."""
        self.batch_end = datetime.now(timezone.utc)
    
    def record_error(self, source: str, error: str):
        """Record an error for a specific source."""
        if source not in self.errors_by_source:
            self.errors_by_source[source] = []
        self.errors_by_source[source].append(error)
    
    @property
    def duration_seconds(self) -> float:
        """Get batch duration in seconds."""
        if not self.batch_start:
            return 0.0
        end = self.batch_end or datetime.now(timezone.utc)
        return (end - self.batch_start).total_seconds()
    
    def log_summary(self):
        """Log a summary of the batch metrics."""
        error_count = sum(len(errs) for errs in self.errors_by_source.values())
        logger.info(
            f"Batch completed: "
            f"fetched={self.rows_fetched}, "
            f"inserted={self.rows_inserted}, "
            f"skipped={self.rows_skipped}, "
            f"duration={self.duration_seconds:.2f}s, "
            f"db_write={self.db_write_time_ms}ms, "
            f"errors={error_count}"
        )
        if self.errors_by_source:
            for source, errors in self.errors_by_source.items():
                logger.warning(f"  Errors from {source}: {len(errors)}")


def acquire_lock() -> Any:
    """
    Acquire exclusive lock to prevent duplicate ingestion processes.
    
    Returns the lock file descriptor on success.
    Exits with code 1 if another process holds the lock.
    """
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(f"{os.getpid()}\n{datetime.now(timezone.utc).isoformat()}")
        lock_fd.flush()
        logger.info(f"Lock acquired, PID: {os.getpid()}")
        return lock_fd
    except BlockingIOError:
        # Check if the process holding the lock is still alive
        try:
            with open(LOCK_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    pid = int(content.split('\n')[0])
                    logger.error(f"Another ingestion process is running (PID: {pid}). Exiting.")
        except (ValueError, FileNotFoundError):
            logger.error("Another ingestion process is running. Exiting.")
        sys.exit(1)


def release_lock(lock_fd: Any):
    """Release the lock file."""
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            LOCK_FILE.unlink(missing_ok=True)
            logger.info("Lock released.")
        except Exception as e:
            logger.warning(f"Error releasing lock: {e}")


def run_with_backoff(
    ingest_func: Callable[[IngestionMetrics], Any],
    metrics: IngestionMetrics,
    max_retries: int = MAX_RETRIES,
    base_backoff: int = BASE_BACKOFF_SECONDS
) -> Any:
    """
    Run ingestion with exponential backoff on failure.
    
    Args:
        ingest_func: The ingestion function to run. Should accept IngestionMetrics.
        metrics: Metrics object to track batch stats.
        max_retries: Maximum number of retry attempts.
        base_backoff: Base wait time in seconds (doubles each retry).
    
    Returns:
        The result of the ingestion function.
    
    Raises:
        SystemExit with code 2 if max retries exceeded.
    """
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            metrics.start_batch()
            result = ingest_func(metrics)
            metrics.end_batch()
            metrics.log_summary()
            return result
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down gracefully...")
            raise
        except Exception as e:
            retries += 1
            last_error = e
            wait_time = base_backoff * (2 ** (retries - 1))
            
            logger.error(
                f"Ingestion failed (attempt {retries}/{max_retries}): {type(e).__name__}: {e}"
            )
            
            if retries < max_retries:
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.critical(f"Max retries ({max_retries}) exceeded. Ingestion failed.")
                logger.critical(f"Last error: {last_error}")
                sys.exit(2)
    
    return None


def run_continuous(
    ingest_func: Callable[[IngestionMetrics], Any],
    interval_seconds: int = 900  # 15 minutes
):
    """
    Run ingestion continuously with the specified interval.
    
    Args:
        ingest_func: The ingestion function to run.
        interval_seconds: Time between ingestion runs in seconds.
    """
    lock_fd = None
    
    try:
        lock_fd = acquire_lock()
        
        logger.info(f"Starting continuous ingestion (interval: {interval_seconds}s)")
        
        while True:
            metrics = IngestionMetrics()
            
            try:
                run_with_backoff(ingest_func, metrics)
            except SystemExit:
                raise
            except Exception as e:
                logger.error(f"Unexpected error in ingestion loop: {e}")
            
            logger.info(f"Sleeping for {interval_seconds} seconds...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        release_lock(lock_fd)


def run_once(ingest_func: Callable[[IngestionMetrics], Any]):
    """
    Run ingestion once (with retries) and exit.
    
    Args:
        ingest_func: The ingestion function to run.
    """
    lock_fd = None
    
    try:
        lock_fd = acquire_lock()
        
        logger.info("Starting single ingestion run")
        metrics = IngestionMetrics()
        run_with_backoff(ingest_func, metrics)
        logger.info("Ingestion completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        release_lock(lock_fd)


# Entry point for running with existing ingest_v2
if __name__ == "__main__":
    import asyncio
    
    # Add parent directories to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from app.services.ingest_v2 import run_ingestion as v2_ingest
    
    def wrapped_ingest(metrics: IngestionMetrics):
        """Wrapper to run async v2 ingestion."""
        asyncio.run(v2_ingest())
        # Note: v2_ingest doesn't use metrics yet, but we track timing
        return True
    
    # Check for --once flag
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once(wrapped_ingest)
    else:
        run_continuous(wrapped_ingest)
