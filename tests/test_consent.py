"""Tests for consent evaluation engine and privacy enforcement."""

import pytest

from app.schemas.events import ConsentPayload, EventRequest
from app.services.consent import ConsentEngine
from app.services.event_processor import EventProcessor
from app.storage.memory import MemoryStorage


def test_consent_all_granted():
    """Verify both advertising and analytics destinations are permitted when full consent is granted."""
    engine = ConsentEngine(fail_closed=True)
    consent = ConsentPayload(advertising=True, analytics=True)

    meta_ok, meta_reason = engine.evaluate(consent, "meta")
    assert meta_ok is True
    assert "granted" in meta_reason.lower()

    ga4_ok, ga4_reason = engine.evaluate(consent, "ga4")
    assert ga4_ok is True
    assert "granted" in ga4_reason.lower()


def test_consent_advertising_denied_analytics_granted():
    """Verify Meta is blocked when advertising consent is false, but GA4 is allowed."""
    engine = ConsentEngine(fail_closed=True)
    consent = ConsentPayload(advertising=False, analytics=True)

    meta_ok, meta_reason = engine.evaluate(consent, "meta")
    assert meta_ok is False
    assert "advertising consent is false" in meta_reason.lower()

    ga4_ok, _ = engine.evaluate(consent, "ga4")
    assert ga4_ok is True


def test_consent_analytics_denied_advertising_granted():
    """Verify GA4 is blocked when analytics consent is false, but Meta is allowed."""
    engine = ConsentEngine(fail_closed=True)
    consent = ConsentPayload(advertising=True, analytics=False)

    meta_ok, _ = engine.evaluate(consent, "meta")
    assert meta_ok is True

    ga4_ok, ga4_reason = engine.evaluate(consent, "ga4")
    assert ga4_ok is False
    assert "analytics consent is false" in ga4_reason.lower()


def test_consent_fail_closed_on_default_missing():
    """Verify both destinations fail closed when consent values default to False."""
    engine = ConsentEngine(fail_closed=True)
    consent = ConsentPayload()  # Defaults to False, False

    meta_ok, _ = engine.evaluate(consent, "meta")
    assert meta_ok is False

    ga4_ok, _ = engine.evaluate(consent, "ga4")
    assert ga4_ok is False


@pytest.mark.asyncio
async def test_event_processor_consent_filtering(sample_lead_payload):
    """Verify EventProcessor skips destination with skipped_consent status when consent is absent."""
    payload = dict(sample_lead_payload)
    payload["consent"] = {"analytics": True, "advertising": False}  # Deny Meta
    event = EventRequest(**payload)

    processor = EventProcessor(storage=MemoryStorage())
    response = await processor.process_event(event, test_mode=True)

    results_by_dest = {r.destination: r for r in response.results}
    assert results_by_dest["meta"].status == "skipped_consent"
    assert "advertising consent" in results_by_dest["meta"].message.lower()
    assert results_by_dest["ga4"].status == "test_validated"
