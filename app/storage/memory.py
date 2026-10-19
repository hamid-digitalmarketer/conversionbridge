"""In-memory storage implementation for local development and unit tests."""

import threading
import time
from typing import Any

from .base import StorageBackend


class MemoryStorage(StorageBackend):
    """Thread-safe in-memory storage for deduplication.

    Note: In multi-instance serverless deployments (such as Firebase Functions),
    memory is isolated per instance. Use FirestoreStorage for distributed production deployments.
    """

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _cleanup_expired(self, now: float) -> None:
        """Purge records past their expiration time."""
        expired = [k for k, v in self._store.items() if v.get("expires_at", 0) <= now]
        for k in expired:
            del self._store[k]

    def is_duplicate(self, key: str, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            self._cleanup_expired(now)
            record = self._store.get(key)
            if not record:
                return False
            # Check if within window
            created_at = record.get("created_at", 0)
            return (now - created_at) < window_seconds

    def mark_processed(
        self,
        key: str,
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int = 172800,
    ) -> bool:
        now = time.time()
        with self._lock:
            self._cleanup_expired(now)
            if key in self._store:
                return False
            self._store[key] = {
                "created_at": now,
                "expires_at": now + ttl_seconds,
                "metadata": metadata or {},
            }
            return True

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
