"""
Ticker-Genius Disk Cache Module
===============================
M2 Core: SQLite-based caching for HTTP responses and data.

Features:
- WAL mode for concurrent access
- Schema versioning with safe migration
- Automatic cleanup of old entries
- Thread-safe operations
"""

from __future__ import annotations

import re
import sqlite3
import time
import logging
import threading
from contextlib import contextmanager
from typing import Optional, Generator

from tickergenius.__version__ import __cache_version__

logger = logging.getLogger("tickergenius.cache")


class DiskCache:
    """
    SQLite-based cache with schema versioning.

    Tables:
    - http_cache: HTTP response caching (key, timestamp, body)
    - data_cache: General data caching (key, timestamp, blob)
    - meta: Schema version tracking
    """

    SCHEMA_VERSION = __cache_version__

    def __init__(self, db_path: str, cleanup_days: int = 7):
        """
        Initialize cache.

        Args:
            db_path: Path to SQLite database file
            cleanup_days: Days to keep old entries (default: 7)
        """
        self.db_path = db_path
        self.cleanup_days = cleanup_days
        self._lock = threading.Lock()
        self._init_db()

    def _is_safe_identifier(self, name: str) -> bool:
        """Validate identifier to prevent SQL injection."""
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name)) and len(name) < 64

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA busy_timeout=30000;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            yield conn
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def _init_db(self) -> None:
        """Initialize database with schema."""
        with self._lock:
            with self._connect() as conn:
                # Enable WAL mode
                try:
                    conn.execute("PRAGMA journal_mode=WAL;")
                except Exception:
                    pass

                # Create tables
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS http_cache (
                        k TEXT PRIMARY KEY,
                        ts INTEGER NOT NULL,
                        body TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS data_cache (
                        k TEXT PRIMARY KEY,
                        ts INTEGER NOT NULL,
                        blob BLOB
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)

                # Check/update schema version
                cur = conn.execute(
                    "SELECT value FROM meta WHERE key = 'schema_version'"
                )
                row = cur.fetchone()
                stored_version = row[0] if row else None

                if stored_version != self.SCHEMA_VERSION:
                    if stored_version:
                        logger.info(
                            f"Cache schema upgrade: {stored_version} -> {self.SCHEMA_VERSION}"
                        )
                    conn.execute(
                        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                        ("schema_version", self.SCHEMA_VERSION),
                    )

                conn.commit()

        # Initial cleanup
        self._cleanup_old_entries()

    def _cleanup_old_entries(self) -> None:
        """Remove entries older than cleanup_days."""
        try:
            cutoff = int(time.time()) - (self.cleanup_days * 86400)
            with self._connect() as conn:
                conn.execute("DELETE FROM http_cache WHERE ts < ?", (cutoff,))
                conn.execute("DELETE FROM data_cache WHERE ts < ?", (cutoff,))
                conn.commit()
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")

    # =========================================================================
    # HTTP Cache Methods
    # =========================================================================

    def set_http(self, key: str, body: str) -> None:
        """
        Store HTTP response in cache.

        Args:
            key: Cache key (usually hashed URL)
            body: Response body text
        """
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO http_cache (k, ts, body) VALUES (?, ?, ?)",
                    (key, int(time.time()), body),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"HTTP cache write failed: {e}")

    def get_http(self, key: str, ttl: Optional[int] = None) -> Optional[str]:
        """
        Retrieve HTTP response from cache.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds. None = default (7 days), 0 = no expiry

        Returns:
            Cached body or None if not found/expired
        """
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT ts, body FROM http_cache WHERE k = ?", (key,)
                )
                row = cur.fetchone()
                if not row:
                    return None

                ts, body = row

                # Check expiry
                if ttl is None:
                    ttl = self.cleanup_days * 86400
                if ttl > 0 and (time.time() - ts) > ttl:
                    return None

                return body
        except Exception:
            return None

    # =========================================================================
    # Data Cache Methods (Binary)
    # =========================================================================

    def set_data(self, key: str, data: bytes) -> None:
        """
        Store binary data in cache.

        Args:
            key: Cache key
            data: Binary data
        """
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO data_cache (k, ts, blob) VALUES (?, ?, ?)",
                    (key, int(time.time()), sqlite3.Binary(data)),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Data cache write failed: {e}")

    def get_data(self, key: str, ttl: Optional[int] = None) -> Optional[bytes]:
        """
        Retrieve binary data from cache.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            Cached data or None if not found/expired
        """
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT ts, blob FROM data_cache WHERE k = ?", (key,)
                )
                row = cur.fetchone()
                if not row:
                    return None

                ts, blob = row

                if ttl is None:
                    ttl = self.cleanup_days * 86400
                if ttl > 0 and (time.time() - ts) > ttl:
                    return None

                return blob
        except Exception:
            return None

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def delete(self, key: str) -> None:
        """Delete entry from both caches."""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM http_cache WHERE k = ?", (key,))
                conn.execute("DELETE FROM data_cache WHERE k = ?", (key,))
                conn.commit()
        except Exception:
            pass

    def clear_all(self) -> None:
        """Clear all cache entries."""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM http_cache")
                conn.execute("DELETE FROM data_cache")
                conn.commit()
            logger.info("Cache cleared")
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            with self._connect() as conn:
                http_count = conn.execute(
                    "SELECT COUNT(*) FROM http_cache"
                ).fetchone()[0]
                data_count = conn.execute(
                    "SELECT COUNT(*) FROM data_cache"
                ).fetchone()[0]
                return {
                    "http_entries": http_count,
                    "data_entries": data_count,
                    "schema_version": self.SCHEMA_VERSION,
                }
        except Exception:
            return {"error": "Failed to get stats"}


def start_cache_cleanup_thread(
    cache: DiskCache, interval_hours: int = 6
) -> threading.Thread:
    """
    Start background thread for periodic cache cleanup.

    Args:
        cache: DiskCache instance
        interval_hours: Hours between cleanup runs

    Returns:
        Started daemon thread
    """
    def _periodic_cleanup():
        while True:
            try:
                time.sleep(interval_hours * 3600)
                cache._cleanup_old_entries()
                logger.debug("Periodic cache cleanup completed")
            except Exception as e:
                logger.warning(f"Cache cleanup failed: {e}")

    thread = threading.Thread(
        target=_periodic_cleanup,
        daemon=True,
        name="CacheCleanup"
    )
    thread.start()
    logger.info(f"Cache cleanup thread started (interval: {interval_hours}h)")
    return thread
