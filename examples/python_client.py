"""Example Python client submitting conversion events to ConversionBridge."""

import os
import time

import requests

# Set endpoint URL (local development or deployed Firebase Function URL)
CONVERSIONBRIDGE_URL = os.getenv("CONVERSIONBRIDGE_URL", "http://localhost:8080/api/v1/events")
API_KEY = os.getenv("CONVERSIONBRIDGE_API_KEY", "")


def send_lead_event():
    """Send a consent-aware Lead conversion event from a website backend."""
    headers = {
        "Content-Type": "application/json",
    }
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    payload = {
        "event_name": "Lead",
        "event_id": f"lead_{int(time.time())}_9482",
        "event_time": int(time.time()),
        "event_source_url": "https://example.com/consultation",
        "action_source": "website",
        "consent": {
            "analytics": True,
            "advertising": True,
            "granted_at": int(time.time()),
        },
        "user_data": {
            "email": "customer@example.com",
            "phone": "+15551234567",
            "first_name": "Jane",
            "last_name": "Doe",
            "country": "us",
            "client_id": "1948201948.1729304859",
            "fbp": "fb.1.1729304859.1029384756",
        },
        "custom_data": {
            "value": 250.00,
            "currency": "USD",
            "content_name": "Executive Marketing Audit",
            "content_category": "B2B Consultation",
            "status": "qualified",
        },
        "destinations": ["meta", "ga4"],
        "test_mode": False,
    }

    print(f"Sending Lead event to {CONVERSIONBRIDGE_URL}...")
    response = requests.post(CONVERSIONBRIDGE_URL, json=payload, headers=headers, timeout=10)
    print(f"Response HTTP {response.status_code}:")
    print(response.json())


def send_purchase_event():
    """Send an E-Commerce Purchase conversion event from an order-confirmation service."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    order_id = f"ORD-{int(time.time())}"
    payload = {
        "event_name": "Purchase",
        "event_id": f"purchase_{order_id}",
        "event_time": int(time.time()),
        "event_source_url": "https://example.com/checkout/success",
        "action_source": "website",
        "consent": {
            "analytics": True,
            "advertising": True,
        },
        "user_data": {
            "email": "buyer@example.com",
            "phone": "+15559876543",
            "first_name": "Alex",
            "last_name": "Smith",
            "city": "Austin",
            "state": "tx",
            "zip_code": "78701",
            "country": "us",
            "client_id": "8472910384.1729304859",
            "fbp": "fb.1.1729304859.9876543210",
        },
        "custom_data": {
            "value": 489.95,
            "currency": "USD",
            "order_id": order_id,
            "num_items": 2,
            "content_ids": ["SKU-1001", "SKU-2045"],
            "contents": [
                {
                    "id": "SKU-1001",
                    "name": "Technical SEO Suite",
                    "quantity": 1,
                    "item_price": 299.95,
                },
                {
                    "id": "SKU-2045",
                    "name": "Analytics Dashboard",
                    "quantity": 1,
                    "item_price": 190.00,
                },
            ],
        },
        "destinations": ["meta", "ga4"],
        "test_mode": False,
    }

    print(f"\nSending Purchase event to {CONVERSIONBRIDGE_URL}...")
    response = requests.post(CONVERSIONBRIDGE_URL, json=payload, headers=headers, timeout=10)
    print(f"Response HTTP {response.status_code}:")
    print(response.json())


if __name__ == "__main__":
    send_lead_event()
    send_purchase_event()
