"""Abstract storage backend interface for event deduplication."""

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """Abstract base class defining persistent or in-memory deduplication storage."""

    @abstractmethod
    def is_duplicate(self, key: str, window_seconds: int) -> bool:
        """Check if an event key has already been processed within the given window."""
        pass

    @abstractmethod
    def mark_processed(
        self,
        key: str,
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int = 172800,  # 48 hours default
    ) -> bool:
        """Record an event key as processed with an expiration TTL.

        Returns True if newly recorded, or False if already existed.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored deduplication records (used in tests)."""
        pass
