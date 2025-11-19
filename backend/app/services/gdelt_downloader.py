"""
GDELT GKG File Downloader Service.

Downloads GDELT GKG v2.1 files from the GDELT 2.0 repository with caching,
retry logic, and automatic cleanup of old files.

Reference: ADR-0003-gdelt-parser-strategy.md
"""

import asyncio
import aiohttp
import json
import logging
import os
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

GDELT_BASE_URL = "http://data.gdeltproject.org/gdeltv2"
CACHE_DIR = Path("/tmp/gdelt")

# Retry configuration from ADR-0003
RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay_seconds": 5,
    "exponential_base": 2,
}


class GDELTDownloadError(Exception):
    """Raised when GDELT file download fails after all retries."""
    pass


class GDELTDownloader:
    """
    Downloads and caches GDELT GKG files.

    Handles:
    - Downloading ZIP files from GDELT 2.0 repository
    - Caching to avoid redundant downloads
    - Automatic cleanup of old files
    - Retry logic with exponential backoff
    - Fallback to previous 15-minute intervals

    Attributes:
        cache_dir: Directory for storing downloaded files.
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        """
        Initialize the GDELT downloader.

        Args:
            cache_dir: Path to cache directory. Defaults to /tmp/gdelt.
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_latest_timestamp(self) -> str:
        """
        Get timestamp for latest 15-minute interval.

        GDELT updates every 15 minutes at :00, :15, :30, :45.
        We subtract 15 minutes to account for GDELT's ~5 minute processing delay.

        Returns:
            Timestamp string in format YYYYMMDDHHmmss.
        """
        now = datetime.utcnow()
        # Round down to nearest 15 minutes
        minute = (now.minute // 15) * 15
        rounded = now.replace(minute=minute, second=0, microsecond=0)
        # Subtract 15 minutes (GDELT has processing delay)
        adjusted = rounded - timedelta(minutes=15)
        return adjusted.strftime("%Y%m%d%H%M%S")

    def get_previous_timestamp(self, timestamp: str) -> str:
        """
        Get the previous 15-minute timestamp.

        Args:
            timestamp: Current timestamp in format YYYYMMDDHHmmss.

        Returns:
            Previous timestamp string (15 minutes earlier).
        """
        dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        previous = dt - timedelta(minutes=15)
        return previous.strftime("%Y%m%d%H%M%S")

    async def download_file(self, timestamp: str) -> Path:
        """
        Download GKG file for given timestamp with retry logic.

        Implements exponential backoff: 5s -> 10s -> 20s

        Args:
            timestamp: Timestamp in format YYYYMMDDHHmmss.

        Returns:
            Path to the extracted CSV file.

        Raises:
            GDELTDownloadError: If download fails after all retry attempts.
        """
        zip_filename = f"{timestamp}.gkg.csv.zip"
        csv_filename = f"{timestamp}.gkg.csv"

        zip_path = self.cache_dir / zip_filename
        csv_path = self.cache_dir / csv_filename

        # Check if already cached
        if csv_path.exists():
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "source": "gdelt_downloader",
                "action": "cache_hit",
                "file": csv_filename,
                "cache_path": str(csv_path)
            }
            logger.info(json.dumps(log_data))
            return csv_path

        url = f"{GDELT_BASE_URL}/{zip_filename}"

        # Retry loop with exponential backoff
        last_error: Optional[Exception] = None
        for attempt in range(RETRY_CONFIG["max_attempts"]):
            start_time = time.time()

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                        response_time_ms = int((time.time() - start_time) * 1000)

                        if response.status == 200:
                            # Download and save ZIP file
                            content = await response.read()
                            zip_path.write_bytes(content)

                            # Extract CSV from ZIP
                            extracted_path = self._extract_zip(zip_path)

                            # Clean up ZIP file after extraction
                            zip_path.unlink()

                            # Log successful download
                            log_data = {
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "level": "INFO",
                                "source": "gdelt_downloader",
                                "action": "download_success",
                                "url": url,
                                "response_time_ms": response_time_ms,
                                "file_size_bytes": len(content),
                                "attempt": attempt + 1
                            }
                            logger.info(json.dumps(log_data))

                            return extracted_path

                        elif response.status == 404:
                            # File not available yet - don't retry, let caller handle
                            log_data = {
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "level": "WARNING",
                                "source": "gdelt_downloader",
                                "action": "file_not_found",
                                "url": url,
                                "status_code": 404,
                                "response_time_ms": response_time_ms
                            }
                            logger.warning(json.dumps(log_data))
                            raise GDELTDownloadError(f"File not found: {url}")

                        else:
                            # Other HTTP error - will retry
                            last_error = aiohttp.ClientResponseError(
                                response.request_info,
                                response.history,
                                status=response.status
                            )
                            log_data = {
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "level": "WARNING",
                                "source": "gdelt_downloader",
                                "action": "download_failed",
                                "url": url,
                                "status_code": response.status,
                                "response_time_ms": response_time_ms,
                                "attempt": attempt + 1,
                                "max_attempts": RETRY_CONFIG["max_attempts"]
                            }
                            logger.warning(json.dumps(log_data))

            except aiohttp.ClientError as e:
                response_time_ms = int((time.time() - start_time) * 1000)
                last_error = e
                log_data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": "WARNING",
                    "source": "gdelt_downloader",
                    "action": "network_error",
                    "url": url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "response_time_ms": response_time_ms,
                    "attempt": attempt + 1,
                    "max_attempts": RETRY_CONFIG["max_attempts"]
                }
                logger.warning(json.dumps(log_data))

            except asyncio.TimeoutError as e:
                response_time_ms = int((time.time() - start_time) * 1000)
                last_error = e
                log_data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": "WARNING",
                    "source": "gdelt_downloader",
                    "action": "timeout",
                    "url": url,
                    "response_time_ms": response_time_ms,
                    "attempt": attempt + 1,
                    "max_attempts": RETRY_CONFIG["max_attempts"]
                }
                logger.warning(json.dumps(log_data))

            # Exponential backoff before retry (except for 404)
            if attempt < RETRY_CONFIG["max_attempts"] - 1:
                delay = RETRY_CONFIG["initial_delay_seconds"] * (
                    RETRY_CONFIG["exponential_base"] ** attempt
                )
                log_data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": "INFO",
                    "source": "gdelt_downloader",
                    "action": "retry_wait",
                    "delay_seconds": delay,
                    "next_attempt": attempt + 2
                }
                logger.info(json.dumps(log_data))
                await asyncio.sleep(delay)

        # All retries exhausted
        error_msg = f"Failed to download {url} after {RETRY_CONFIG['max_attempts']} attempts"
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "ERROR",
            "source": "gdelt_downloader",
            "action": "download_exhausted",
            "url": url,
            "error": str(last_error) if last_error else "Unknown error",
            "total_attempts": RETRY_CONFIG["max_attempts"]
        }
        logger.error(json.dumps(log_data))
        raise GDELTDownloadError(error_msg)

    async def download_latest(self) -> Optional[Path]:
        """
        Download latest available GKG file.

        Tries the current 15-minute interval first, then falls back to
        the previous interval if not available (GDELT has ~5 min delay).

        Returns:
            Path to the extracted CSV file, or None if both attempts fail.
        """
        timestamp = self.get_latest_timestamp()

        try:
            return await self.download_file(timestamp)
        except GDELTDownloadError as e:
            # File not available, try previous 15-minute interval
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "source": "gdelt_downloader",
                "action": "fallback_to_previous",
                "original_timestamp": timestamp,
                "reason": str(e)
            }
            logger.info(json.dumps(log_data))

            previous_timestamp = self.get_previous_timestamp(timestamp)

            try:
                return await self.download_file(previous_timestamp)
            except GDELTDownloadError as e2:
                log_data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": "ERROR",
                    "source": "gdelt_downloader",
                    "action": "both_timestamps_failed",
                    "original_timestamp": timestamp,
                    "fallback_timestamp": previous_timestamp,
                    "error": str(e2)
                }
                logger.error(json.dumps(log_data))
                return None

    def cleanup_old_files(self, max_age_hours: int = 1) -> int:
        """
        Remove files older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours for cached files. Default is 1.

        Returns:
            Number of files deleted.
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        deleted_count = 0

        for file_path in self.cache_dir.iterdir():
            if file_path.is_file():
                # Check file modification time
                file_mtime = datetime.utcfromtimestamp(file_path.stat().st_mtime)

                if file_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1

                        log_data = {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "level": "INFO",
                            "source": "gdelt_downloader",
                            "action": "file_deleted",
                            "file": file_path.name,
                            "file_age_hours": (datetime.utcnow() - file_mtime).total_seconds() / 3600
                        }
                        logger.info(json.dumps(log_data))

                    except OSError as e:
                        log_data = {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "level": "ERROR",
                            "source": "gdelt_downloader",
                            "action": "delete_failed",
                            "file": file_path.name,
                            "error": str(e)
                        }
                        logger.error(json.dumps(log_data))

        if deleted_count > 0:
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "source": "gdelt_downloader",
                "action": "cleanup_complete",
                "files_deleted": deleted_count,
                "max_age_hours": max_age_hours
            }
            logger.info(json.dumps(log_data))

        return deleted_count

    def _extract_zip(self, zip_path: Path) -> Path:
        """
        Extract ZIP file and return path to CSV.

        Args:
            zip_path: Path to the ZIP file.

        Returns:
            Path to the extracted CSV file.

        Raises:
            zipfile.BadZipFile: If the ZIP file is corrupted.
            ValueError: If no CSV file found in the archive.
        """
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get the CSV filename from the archive
            csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]

            if not csv_files:
                raise ValueError(f"No CSV file found in {zip_path}")

            csv_filename = csv_files[0]
            zip_ref.extract(csv_filename, self.cache_dir)

            extracted_path = self.cache_dir / csv_filename

            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "source": "gdelt_downloader",
                "action": "zip_extracted",
                "zip_file": zip_path.name,
                "csv_file": csv_filename,
                "csv_size_bytes": extracted_path.stat().st_size
            }
            logger.info(json.dumps(log_data))

            return extracted_path

    def get_cached_files(self) -> list[Path]:
        """
        Get list of all cached CSV files sorted by modification time (newest first).

        Returns:
            List of paths to cached CSV files.
        """
        csv_files = list(self.cache_dir.glob("*.gkg.csv"))
        csv_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return csv_files

    def get_cache_stats(self) -> dict:
        """
        Get statistics about the current cache.

        Returns:
            Dictionary with cache statistics including file count and total size.
        """
        csv_files = self.get_cached_files()
        total_size = sum(f.stat().st_size for f in csv_files)

        return {
            "file_count": len(csv_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir),
            "files": [f.name for f in csv_files]
        }
