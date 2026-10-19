"""Event deduplication service providing cross-channel and destination-specific idempotency."""

from typing import Any

from ..storage.base import StorageBackend


class DeduplicationService:
    """Manages event deduplication across configurable time windows.

    Keys include the destination name so that an event accepted by one platform (e.g. GA4)
    does not accidentally suppress delivery to another platform (e.g. Meta).
    """

    def __init__(self, storage: StorageBackend, window_hours: int = 48):
        self.storage = storage
        self.window_seconds = window_hours * 3600

    def build_key(self, destination: str, event_name: str, event_id: str) -> str:
        """Create a normalized, collision-resistant storage key."""
        dest = destination.strip().lower()
        name = event_name.strip()
        eid = event_id.strip()
        return f"{dest}:{name}:{eid}"

    def is_duplicate(self, destination: str, event_name: str, event_id: str) -> bool:
        """Check whether this event was already dispatched to this destination within the window."""
        key = self.build_key(destination, event_name, event_id)
        return self.storage.is_duplicate(key, self.window_seconds)

    def record_dispatched(
        self,
        destination: str,
        event_name: str,
        event_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Mark this event as successfully dispatched to prevent duplicate retries."""
        key = self.build_key(destination, event_name, event_id)
        return self.storage.mark_processed(
            key=key,
            metadata=metadata or {},
            ttl_seconds=self.window_seconds,
        )
