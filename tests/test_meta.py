"""Tests for Meta Conversions API (CAPI) destination adapter."""

import hashlib
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.destinations.meta import MetaDestination
from app.schemas.events import EventRequest


def test_meta_payload_transformation(sample_lead_payload):
    """Verify Meta user_data hashing and unhashed context parameters."""
    event = EventRequest(**sample_lead_payload)
    adapter = MetaDestination()
    payload = adapter.transform_payload(event)

    assert "data" in payload
    assert len(payload["data"]) == 1
    item = payload["data"][0]

    assert item["event_name"] == "Lead"
    assert item["event_id"] == event.event_id
    assert item["action_source"] == "website"

    user_data = item["user_data"]
    # Email must be SHA-256 hashed
    expected_em_hash = hashlib.sha256(b"test.user@example.com").hexdigest()
    assert user_data["em"] == [expected_em_hash]

    # Phone must have non-digits stripped and hashed
    expected_ph_hash = hashlib.sha256(b"15551234567").hexdigest()
    assert user_data["ph"] == [expected_ph_hash]

    # First name and last name hashed
    assert user_data["fn"] == [hashlib.sha256(b"john").hexdigest()]
    assert user_data["ln"] == [hashlib.sha256(b"doe").hexdigest()]

    # Context fields must be UNHASHED per Meta documentation
    assert user_data["fbp"] == "fb.1.1729300000.1234567890"
    assert user_data["fbc"] == "fb.1.1729300000.IwARtest"


def test_meta_prehashed_data_not_double_hashed(sample_lead_payload):
    """Verify that if customer data is already SHA-256 hashed, it is not double-hashed."""
    payload = dict(sample_lead_payload)
    already_hashed_email = hashlib.sha256(b"prehashed@domain.com").hexdigest()
    payload["user_data"]["email"] = already_hashed_email

    event = EventRequest(**payload)
    adapter = MetaDestination()
    wire_payload = adapter.transform_payload(event)

    # Must remain identical to the pre-hashed string
    assert wire_payload["data"][0]["user_data"]["em"] == [already_hashed_email]


@pytest.mark.asyncio
async def test_meta_test_mode_simulation(sample_lead_payload):
    """Verify test_mode does not make external HTTP requests."""
    event = EventRequest(**sample_lead_payload)
    adapter = MetaDestination()

    result = await adapter.send_event(event, test_mode=True)
    assert result.status == "test_validated"
    assert result.status_code == 200
    assert result.payload_preview is not None


@pytest.mark.asyncio
async def test_meta_live_success_dispatch(sample_lead_payload):
    """Verify live HTTP 200 response from Meta Graph API returns sent status."""
    payload = dict(sample_lead_payload)
    payload["test_mode"] = False
    event = EventRequest(**payload)
    adapter = MetaDestination()

    mock_resp = httpx.Response(
        status_code=200,
        json={"events_received": 1, "fbtrace_id": "FBT12345678"},
        request=httpx.Request("POST", "https://graph.facebook.com"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await adapter.send_event(event, test_mode=False)

        assert result.status == "sent"
        assert result.status_code == 200
        assert "events_received: 1" in result.message


@pytest.mark.asyncio
async def test_meta_api_rejection_error(sample_lead_payload):
    """Verify handling of Meta API error response (e.g. invalid parameter)."""
    payload = dict(sample_lead_payload)
    payload["test_mode"] = False
    event = EventRequest(**payload)
    adapter = MetaDestination()

    mock_resp = httpx.Response(
        status_code=400,
        headers={"content-type": "application/json"},
        json={"error": {"message": "Invalid Parameter", "type": "OAuthException", "code": 100}},
        request=httpx.Request("POST", "https://graph.facebook.com"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await adapter.send_event(event, test_mode=False)

        assert result.status == "failed"
        assert result.status_code == 400
        assert "Invalid Parameter" in result.message


@pytest.mark.asyncio
async def test_meta_timeout_handling(sample_lead_payload):
    """Verify handling of network timeouts."""
    payload = dict(sample_lead_payload)
    payload["test_mode"] = False
    event = EventRequest(**payload)
    adapter = MetaDestination()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")
        result = await adapter.send_event(event, test_mode=False)

        assert result.status == "failed"
        assert "timed out" in result.message.lower()
