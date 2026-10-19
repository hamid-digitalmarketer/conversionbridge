"""Core event processing service coordinating validation, consent, deduplication, and dispatch."""

import asyncio
import logging

from ..config import settings
from ..destinations.base import BaseDestination
from ..destinations.ga4 import GA4Destination
from ..destinations.meta import MetaDestination
from ..schemas.events import DestinationDispatchResult, EventRequest, EventResponse
from ..storage.base import StorageBackend
from ..storage.firestore import FirestoreStorage
from ..storage.memory import MemoryStorage
from .consent import ConsentEngine
from .deduplication import DeduplicationService
from .validation import EventValidator

logger = logging.getLogger(__name__)


class EventProcessor:
    """Orchestrates event intake, privacy gating, deduplication, and multi-channel delivery."""

    def __init__(
        self,
        storage: StorageBackend | None = None,
        consent_engine: ConsentEngine | None = None,
        destinations: dict[str, BaseDestination] | None = None,
    ):
        if storage is None:
            if settings.STORAGE_BACKEND.lower() == "firestore":
                storage = FirestoreStorage(collection_name=settings.FIRESTORE_COLLECTION)
            else:
                storage = MemoryStorage()

        self.storage = storage
        self.consent_engine = consent_engine or ConsentEngine(
            fail_closed=settings.DEFAULT_CONSENT_FAIL_CLOSED
        )
        self.dedup_service = DeduplicationService(
            storage=self.storage,
            window_hours=settings.DEDUPLICATION_WINDOW_HOURS,
        )

        if destinations is None:
            self.destinations: dict[str, BaseDestination] = {
                "meta": MetaDestination(),
                "ga4": GA4Destination(),
            }
        else:
            self.destinations = destinations

    async def _process_single_destination(
        self, destination_name: str, event: EventRequest, test_mode: bool
    ) -> DestinationDispatchResult:
        """Evaluate consent, deduplication, and transmit event to a single destination."""
        adapter = self.destinations.get(destination_name)
        if not adapter:
            return DestinationDispatchResult(
                destination=destination_name,
                status="failed",
                message=f"Unsupported or unregistered destination: '{destination_name}'",
                event_id=event.event_id,
            )

        # 1. Consent Evaluation (Privacy Gate)
        is_permitted, reason = self.consent_engine.evaluate(event.consent, destination_name)
        if not is_permitted:
            logger.info(
                "Event '%s' blocked for destination '%s': %s",
                event.event_id,
                destination_name,
                reason,
            )
            return DestinationDispatchResult(
                destination=destination_name,
                status="skipped_consent",
                message=reason,
                event_id=event.event_id,
            )

        # 2. Deduplication Check (Bypassed in test_mode)
        is_testing = test_mode or event.test_mode
        if not is_testing:
            if self.dedup_service.is_duplicate(
                destination=destination_name,
                event_name=event.event_name,
                event_id=event.event_id,
            ):
                logger.info(
                    "Duplicate event suppressed: '%s' for destination '%s'",
                    event.event_id,
                    destination_name,
                )
                return DestinationDispatchResult(
                    destination=destination_name,
                    status="skipped_duplicate",
                    message="Duplicate event suppressed within deduplication window",
                    event_id=event.event_id,
                )

        # 3. Transmit or Simulate Delivery
        result = await adapter.send_event(event, test_mode=is_testing)

        # 4. Record as Processed upon success (if not testing)
        if not is_testing and result.status == "sent":
            self.dedup_service.record_dispatched(
                destination=destination_name,
                event_name=event.event_name,
                event_id=event.event_id,
                metadata={"status_code": result.status_code},
            )

        return result

    async def process_event(self, event: EventRequest, test_mode: bool = False) -> EventResponse:
        """Process an inbound EventRequest across all requested destinations."""
        # Deep validation
        _is_valid, validation_warnings = EventValidator.validate_request(event)
        if validation_warnings:
            logger.debug("Validation hints for event '%s': %s", event.event_id, validation_warnings)

        # Concurrently dispatch to all target destinations
        tasks = [
            self._process_single_destination(dest, event, test_mode=test_mode)
            for dest in event.destinations
        ]
        results: list[DestinationDispatchResult] = await asyncio.gather(*tasks)

        # Success if at least one destination was accepted, tested, or purposefully skipped due to consent/dedup
        # (Only mark overall success=False if all attempts threw errors or failed)
        overall_success = not all(r.status == "failed" for r in results)

        return EventResponse(
            success=overall_success,
            event_id=event.event_id,
            event_name=event.event_name,
            results=results,
        )
