"""Pytest fixtures and test environment setup for ConversionBridge."""

import os
import time

import pytest
from fastapi.testclient import TestClient

# Ensure test environment variables are set before app config loads
os.environ["ENVIRONMENT"] = "test"
os.environ["STORAGE_BACKEND"] = "memory"
os.environ["REQUIRE_API_KEY"] = "false"
os.environ["META_ENABLED"] = "true"
os.environ["META_PIXEL_ID"] = "123456789012345"
os.environ["META_ACCESS_TOKEN"] = "EAAG_TEST_ACCESS_TOKEN_ABC123"
os.environ["GA4_ENABLED"] = "true"
os.environ["GA4_MEASUREMENT_ID"] = "G-TEST123456"
os.environ["GA4_API_SECRET"] = "GA4_TEST_API_SECRET_XYZ789"

from app.main import app
from app.security.rate_limit import rate_limiter
from app.storage.memory import MemoryStorage


@pytest.fixture(autouse=True)
def reset_state():
    """Reset rate limiter and storage state between test cases."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def sample_lead_payload():
    """Generate a fresh valid lead conversion event payload."""
    now = int(time.time())
    return {
        "event_name": "Lead",
        "event_id": f"test_lead_{now}_{os.urandom(4).hex()}",
        "event_time": now,
        "event_source_url": "https://example.com/contact",
        "action_source": "website",
        "consent": {
            "analytics": True,
            "advertising": True,
            "granted_at": now,
        },
        "user_data": {
            "email": "test.user@example.com",
            "phone": "+15551234567",
            "first_name": "John",
            "last_name": "Doe",
            "city": "Dallas",
            "state": "tx",
            "zip_code": "75001",
            "country": "us",
            "client_id": "123456789.1729300000",
            "fbp": "fb.1.1729300000.1234567890",
            "fbc": "fb.1.1729300000.IwARtest",
        },
        "custom_data": {
            "value": 150.0,
            "currency": "USD",
            "content_name": "Consultation",
            "content_category": "Lead Gen",
        },
        "destinations": ["meta", "ga4"],
        "test_mode": True,
    }


@pytest.fixture
def memory_storage():
    """Fresh in-memory storage instance."""
    return MemoryStorage()
