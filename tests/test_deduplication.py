"""Tests for event deduplication and persistence logic."""

import time

import pytest

from app.schemas.events import EventRequest
from app.services.deduplication import DeduplicationService
from app.services.event_processor import EventProcessor
from app.storage.memory import MemoryStorage


def test_deduplication_basic_flow(memory_storage):
    """Verify first event passes and immediate second event is recognized as duplicate."""
    dedup = DeduplicationService(storage=memory_storage, window_hours=48)

    # Initial check should be clean
    assert dedup.is_duplicate("meta", "Lead", "evt_1001") is False

    # Mark as processed
    recorded = dedup.record_dispatched("meta", "Lead", "evt_1001")
    assert recorded is True

    # Immediate second check must be duplicate
    assert dedup.is_duplicate("meta", "Lead", "evt_1001") is True


def test_destination_isolation_in_deduplication(memory_storage):
    """Verify deduplication for Meta does NOT suppress an event for GA4."""
    dedup = DeduplicationService(storage=memory_storage, window_hours=48)

    # Process for Meta
    dedup.record_dispatched("meta", "Lead", "shared_event_999")

    # Meta is duplicate
    assert dedup.is_duplicate("meta", "Lead", "shared_event_999") is True

    # GA4 has NOT seen this event yet, so it must not be duplicate
    assert dedup.is_duplicate("ga4", "Lead", "shared_event_999") is False


def test_deduplication_window_expiry(memory_storage):
    """Verify events outside the deduplication window are allowed."""
    dedup = DeduplicationService(storage=memory_storage, window_hours=1)

    # Record event with simulated timestamp 2 hours in the past
    key = dedup.build_key("meta", "Lead", "expired_event_1")
    memory_storage._store[key] = {
        "created_at": time.time() - 7200,  # 2 hours ago
        "expires_at": time.time() - 3600,
        "metadata": {},
    }

    # Window is 1 hour, so 2-hour-old record is no longer active
    assert dedup.is_duplicate("meta", "Lead", "expired_event_1") is False


@pytest.mark.asyncio
async def test_event_processor_duplicate_suppression(sample_lead_payload):
    """Verify EventProcessor suppresses duplicate event on repeated live submission."""
    storage = MemoryStorage()
    processor = EventProcessor(storage=storage)

    # Pre-record event in storage for Meta
    storage.mark_processed(
        key="meta:Lead:" + sample_lead_payload["event_id"],
        metadata={},
        ttl_seconds=3600,
    )

    payload = dict(sample_lead_payload)
    payload["test_mode"] = False
    event = EventRequest(**payload)

    response = await processor.process_event(event, test_mode=False)
    results_by_dest = {r.destination: r for r in response.results}

    # Meta must be skipped due to deduplication
    assert results_by_dest["meta"].status == "skipped_duplicate"
    assert "duplicate" in results_by_dest["meta"].message.lower()
