"""Google Cloud Firestore storage backend for production serverless deployments."""

import logging
import time
from typing import Any

from .base import StorageBackend

logger = logging.getLogger(__name__)


class FirestoreStorage(StorageBackend):
    """Production-grade Firestore deduplication backend.

    Supports atomic transactions across concurrent serverless function instances
    and leverages Firestore TTL policies for automatic document cleanup.
    """

    def __init__(self, collection_name: str = "conversionbridge_events"):
        self.collection_name = collection_name
        self._client = None
        self._fallback_memory = None

    def _get_client(self):
        """Lazy-initialize the Firestore client."""
        if self._client is None and self._fallback_memory is None:
            try:
                import firebase_admin
                from firebase_admin import firestore

                # Initialize default app if not already initialized
                if not firebase_admin._apps:
                    firebase_admin.initialize_app()
                self._client = firestore.client()
                logger.info("Firestore client initialized for collection: %s", self.collection_name)
            except Exception as e:
                logger.warning(
                    "Unable to initialize Google Cloud Firestore client (%s). "
                    "Falling back to in-memory deduplication storage.",
                    e,
                )
                from .memory import MemoryStorage

                self._fallback_memory = MemoryStorage()
        return self._client

    def is_duplicate(self, key: str, window_seconds: int) -> bool:
        client = self._get_client()
        if client is None:
            return self._fallback_memory.is_duplicate(key, window_seconds)

        now = time.time()
        try:
            doc_ref = client.collection(self.collection_name).document(key)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            data = doc.to_dict()
            created_at = data.get("created_at", 0)
            return (now - created_at) < window_seconds
        except Exception as e:
            logger.error("Firestore error checking duplicate for key '%s': %s", key, e)
            return False

    def mark_processed(
        self,
        key: str,
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int = 172800,
    ) -> bool:
        client = self._get_client()
        if client is None:
            return self._fallback_memory.mark_processed(key, metadata, ttl_seconds)

        now = time.time()
        doc_ref = client.collection(self.collection_name).document(key)

        try:
            # Atomic creation: fails if document already exists
            doc_ref.create(
                {
                    "created_at": now,
                    "expires_at": now + ttl_seconds,
                    "metadata": metadata or {},
                }
            )
            return True
        except Exception as e:
            # Already exists (e.g. google.api_core.exceptions.AlreadyExists)
            logger.debug("Firestore document already exists for key '%s': %s", key, e)
            return False

    def clear(self) -> None:
        client = self._get_client()
        if client is None:
            self._fallback_memory.clear()
            return
        try:
            docs = client.collection(self.collection_name).limit(500).stream()
            for doc in docs:
                doc.reference.delete()
        except Exception as e:
            logger.warning("Error clearing Firestore collection: %s", e)
