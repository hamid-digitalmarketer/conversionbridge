"""Tests for security controls, authentication, rate limiting, and secret redaction."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.config import settings
from app.security.rate_limit import RateLimiter
from app.security.secrets import hash_sha256, mask_secret, redact_dict


def test_mask_secret():
    """Verify secrets are masked with start and end characters preserved safely."""
    assert mask_secret("EAAG1234567890abcdef") == "EAA***def"
    assert mask_secret("short") == "***"
    assert mask_secret("") == ""


def test_redact_dict_recursive():
    """Verify sensitive fields are redacted recursively from dictionaries."""
    data = {
        "access_token": "SUPER_SECRET_TOKEN",
        "api_secret": "GA4_SECRET_KEY",
        "event_name": "Lead",
        "nested": {
            "user_email": "jane@example.com",
            "phone_number": "+15551234567",
            "public_metric": 100,
        },
        "list_items": [
            {"secret_code": "SECRET_123", "id": 1},
            {"name": "Item"},
        ],
    }

    redacted = redact_dict(data)

    # Check top-level redactions
    assert "***" in redacted["access_token"]
    assert "***" in redacted["api_secret"]
    assert redacted["event_name"] == "Lead"

    # Check nested dictionary redactions
    assert "***" in redacted["nested"]["user_email"]
    assert "***" in redacted["nested"]["phone_number"]
    assert redacted["nested"]["public_metric"] == 100

    # Check list of dictionaries redactions
    assert "***" in redacted["list_items"][0]["secret_code"]
    assert redacted["list_items"][1]["name"] == "Item"


def test_hash_sha256():
    """Verify standard SHA-256 calculation and idempotency on pre-hashed strings."""
    raw = "test@example.com"
    expected = "973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b"
    result = hash_sha256(raw)
    assert result == expected

    # Calling hash_sha256 again on the 64-char hex digest should not re-hash
    assert hash_sha256(result) == expected


def test_rate_limiter_exceeded():
    """Verify RateLimiter blocks requests after exceeding the limit in a sliding window."""
    limiter = RateLimiter(requests_per_minute=3)
    client_key = "192.168.1.50"

    # First 3 requests should pass
    limiter.check(client_key)
    limiter.check(client_key)
    limiter.check(client_key)

    # 4th request must raise 429
    with pytest.raises(HTTPException) as exc_info:
        limiter.check(client_key)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_api_key_authentication_enforcement(client, sample_lead_payload):
    """Verify 401 Unauthorized when REQUIRE_API_KEY is True and key is missing or invalid."""
    with (
        patch.object(settings, "REQUIRE_API_KEY", True),
        patch.object(settings, "API_KEY", SecretStr("VALID_SUPER_SECRET_KEY")),
    ):
        # 1. Missing key -> 401
        resp_missing = client.post("/api/v1/events/test", json=sample_lead_payload)
        assert resp_missing.status_code == 401

        # 2. Invalid key -> 401
        resp_invalid = client.post(
            "/api/v1/events/test",
            json=sample_lead_payload,
            headers={"X-API-Key": "WRONG_KEY"},
        )
        assert resp_invalid.status_code == 401

        # 3. Valid X-API-Key -> 200
        resp_valid_header = client.post(
            "/api/v1/events/test",
            json=sample_lead_payload,
            headers={"X-API-Key": "VALID_SUPER_SECRET_KEY"},
        )
        assert resp_valid_header.status_code == 200

        # 4. Valid Bearer Token -> 200
        resp_valid_bearer = client.post(
            "/api/v1/events/test",
            json=sample_lead_payload,
            headers={"Authorization": "Bearer VALID_SUPER_SECRET_KEY"},
        )
        assert resp_valid_bearer.status_code == 200
