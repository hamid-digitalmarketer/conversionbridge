"""Tests for Google Analytics 4 (GA4) Measurement Protocol adapter."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.config import settings
from app.destinations.ga4 import GA4Destination
from app.schemas.events import EventRequest


def test_ga4_payload_transformation(sample_lead_payload):
    """Verify GA4 payload structure, standard event name mapping, and client_id."""
    event = EventRequest(**sample_lead_payload)
    adapter = GA4Destination()
    payload = adapter.transform_payload(event)

    assert "client_id" in payload
    assert payload["client_id"] == "123456789.1729300000"
    assert "timestamp_micros" in payload
    assert payload["timestamp_micros"] == int(event.event_time * 1_000_000)

    # non_personalized_ads is False when advertising consent is True
    assert payload["non_personalized_ads"] is False

    assert "events" in payload
    assert len(payload["events"]) == 1
    ga4_event = payload["events"][0]

    # "Lead" mapped to standard GA4 "generate_lead"
    assert ga4_event["name"] == "generate_lead"
    params = ga4_event["params"]
    assert params["event_id"] == event.event_id
    assert params["value"] == 150.0
    assert params["currency"] == "USD"


def test_ga4_custom_event_name_sanitization(sample_lead_payload):
    """Verify non-standard event names are converted to safe snake_case."""
    payload = dict(sample_lead_payload)
    payload["event_name"] = "Book Free Strategy Session 2026!"
    event = EventRequest(**payload)
    adapter = GA4Destination()
    wire = adapter.transform_payload(event)

    event_name = wire["events"][0]["name"]
    assert "!" not in event_name
    assert " " not in event_name
    assert len(event_name) <= 40


@pytest.mark.asyncio
async def test_ga4_test_mode_simulation(sample_lead_payload):
    """Verify test_mode does not make external HTTP requests."""
    event = EventRequest(**sample_lead_payload)
    adapter = GA4Destination()

    result = await adapter.send_event(event, test_mode=True)
    assert result.status == "test_validated"
    assert result.status_code == 200
    assert result.payload_preview is not None


@pytest.mark.asyncio
async def test_ga4_live_success_dispatch(sample_lead_payload):
    """Verify live HTTP 204 No Content response from GA4 Measurement Protocol returns sent."""
    payload = dict(sample_lead_payload)
    payload["test_mode"] = False
    event = EventRequest(**payload)
    adapter = GA4Destination()

    mock_resp = httpx.Response(
        status_code=204,
        request=httpx.Request("POST", "https://www.google-analytics.com/mp/collect"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await adapter.send_event(event, test_mode=False)

        assert result.status == "sent"
        assert result.status_code == 204
        assert "HTTP 204" in result.message


@pytest.mark.asyncio
async def test_ga4_debug_mode_handling(sample_lead_payload):
    """Verify debug mode endpoint handling and validation message inspection."""
    payload = dict(sample_lead_payload)
    payload["test_mode"] = False
    event = EventRequest(**payload)
    adapter = GA4Destination()

    # Temporarily activate debug mode
    with patch.object(settings, "GA4_DEBUG_MODE", True):
        mock_resp = httpx.Response(
            status_code=200,
            json={"validationMessages": []},
            request=httpx.Request("POST", "https://www.google-analytics.com/debug/mp/collect"),
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await adapter.send_event(event, test_mode=False)

            assert result.status == "sent"
            assert result.status_code == 200


@pytest.mark.asyncio
async def test_ga4_timeout_handling(sample_lead_payload):
    """Verify handling of GA4 request timeouts."""
    payload = dict(sample_lead_payload)
    payload["test_mode"] = False
    event = EventRequest(**payload)
    adapter = GA4Destination()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("GA4 server timed out")
        result = await adapter.send_event(event, test_mode=False)

        assert result.status == "failed"
        assert "timed out" in result.message.lower()
