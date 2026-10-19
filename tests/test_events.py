"""Tests for event ingestion routes, validation, and API endpoints."""

import copy
import time
from unittest.mock import AsyncMock, patch

from app.schemas.events import DestinationDispatchResult


def test_health_check_endpoint(client):
    """Verify GET /health returns safe operational status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ConversionBridge"
    assert "timestamp" in data
    # Ensure no secrets or tokens are exposed
    assert "token" not in data
    assert "secret" not in data


def test_destinations_status_endpoint(client):
    """Verify GET /api/v1/destinations/status returns redacted destination information."""
    response = client.get("/api/v1/destinations/status")
    assert response.status_code == 200
    statuses = response.json()
    assert isinstance(statuses, list)
    assert len(statuses) >= 2

    dest_names = [d["destination"] for d in statuses]
    assert "meta" in dest_names
    assert "ga4" in dest_names

    # Check for safe masking
    for d in statuses:
        details = d["details"]
        if details.get("token_preview"):
            assert "***" in details["token_preview"]
        if details.get("api_secret_preview"):
            assert "***" in details["api_secret_preview"]


def test_test_event_endpoint(client, sample_lead_payload):
    """Verify POST /api/v1/events/test validates payload and returns safe previews."""
    response = client.post("/api/v1/events/test", json=sample_lead_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["event_id"] == sample_lead_payload["event_id"]
    assert len(data["results"]) == 2

    for r in data["results"]:
        assert r["status"] == "test_validated"
        assert r["payload_preview"] is not None
        # Verify preview does not leak secrets
        preview_str = str(r["payload_preview"])
        assert "EAAG_TEST_ACCESS_TOKEN" not in preview_str


def test_live_event_ingestion(client, sample_lead_payload):
    """Verify POST /api/v1/events executes end-to-end event dispatching with mock adapters."""
    payload = copy.deepcopy(sample_lead_payload)
    payload["test_mode"] = False

    with (
        patch(
            "app.destinations.meta.MetaDestination.send_event",
            new_callable=AsyncMock,
        ) as mock_meta,
        patch(
            "app.destinations.ga4.GA4Destination.send_event",
            new_callable=AsyncMock,
        ) as mock_ga4,
    ):
        mock_meta.return_value = DestinationDispatchResult(
            destination="meta", status="sent", status_code=200, message="Accepted by Meta"
        )
        mock_ga4.return_value = DestinationDispatchResult(
            destination="ga4", status="sent", status_code=204, message="Accepted by GA4"
        )

        response = client.post("/api/v1/events", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 2
        assert all(r["status"] == "sent" for r in data["results"])


def test_missing_required_event_name(client, sample_lead_payload):
    """Verify rejection when event_name is missing."""
    payload = copy.deepcopy(sample_lead_payload)
    del payload["event_name"]
    response = client.post("/api/v1/events/test", json=payload)
    assert response.status_code == 422


def test_invalid_event_name_characters(client, sample_lead_payload):
    """Verify rejection when event_name contains forbidden HTML/script injection characters."""
    payload = copy.deepcopy(sample_lead_payload)
    payload["event_name"] = "<script>alert(1)</script>"
    response = client.post("/api/v1/events/test", json=payload)
    assert response.status_code == 422


def test_missing_required_event_id(client, sample_lead_payload):
    """Verify rejection when event_id is missing or whitespace."""
    payload = copy.deepcopy(sample_lead_payload)
    payload["event_id"] = "   "
    response = client.post("/api/v1/events/test", json=payload)
    assert response.status_code == 422


def test_invalid_timestamp_too_old(client, sample_lead_payload):
    """Verify rejection when event_time is older than 7 days."""
    payload = copy.deepcopy(sample_lead_payload)
    payload["event_time"] = int(time.time()) - (8 * 86400)  # 8 days ago
    response = client.post("/api/v1/events/test", json=payload)
    assert response.status_code == 422


def test_invalid_timestamp_in_future(client, sample_lead_payload):
    """Verify rejection when event_time is more than 24 hours in the future."""
    payload = copy.deepcopy(sample_lead_payload)
    payload["event_time"] = int(time.time()) + (2 * 86400)  # 2 days in future
    response = client.post("/api/v1/events/test", json=payload)
    assert response.status_code == 422


def test_invalid_action_source(client, sample_lead_payload):
    """Verify rejection of invalid action_source value."""
    payload = copy.deepcopy(sample_lead_payload)
    payload["action_source"] = "invalid_radio_source"
    response = client.post("/api/v1/events/test", json=payload)
    assert response.status_code == 422


def test_invalid_destination(client, sample_lead_payload):
    """Verify rejection of unsupported destination in destinations list."""
    payload = copy.deepcopy(sample_lead_payload)
    payload["destinations"] = ["unsupported_platform"]
    response = client.post("/api/v1/events/test", json=payload)
    assert response.status_code == 422


def test_oversized_payload_rejection(client, sample_lead_payload):
    """Verify rejection when Content-Length header exceeds MAX_PAYLOAD_SIZE_BYTES."""
    response = client.post(
        "/api/v1/events/test",
        json=sample_lead_payload,
        headers={"Content-Length": "600000"},  # > 512 KB
    )
    assert response.status_code == 413
