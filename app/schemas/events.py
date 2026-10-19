"""Event schemas and data transfer objects for ConversionBridge."""

import time
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConsentPayload(BaseModel):
    """Consent signals for analytics and advertising processing."""

    analytics: bool = Field(
        default=False,
        description="Whether user consented to analytics tracking (required for GA4)",
    )
    advertising: bool = Field(
        default=False,
        description="Whether user consented to advertising tracking & targeting (required for Meta CAPI)",
    )
    functional: bool | None = Field(
        default=None,
        description="Optional consent signal for functional website cookies/data",
    )
    consent_string: str | None = Field(
        default=None,
        description="Optional IAB TCF v2 consent string or CMP identifier",
    )
    granted_at: int | None = Field(
        default=None,
        description="Unix epoch timestamp when user granted consent",
    )


class UserData(BaseModel):
    """Customer information and browser context for event matching.

    Sensitive fields (email, phone, names) will be hashed with SHA-256 by destination
    adapters according to platform specifications.
    """

    email: str | None = Field(
        default=None,
        description="Customer email (plain text or pre-hashed SHA-256)",
    )
    phone: str | None = Field(
        default=None,
        description="Customer phone number in E.164 format or pre-hashed",
    )
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    gender: str | None = Field(default=None, description="'m' or 'f'")
    date_of_birth: str | None = Field(default=None, description="YYYYMMDD format")
    city: str | None = Field(default=None, description="City name")
    state: str | None = Field(default=None, description="State or province code")
    zip_code: str | None = Field(default=None, description="Postal / ZIP code")
    country: str | None = Field(
        default=None, description="2-letter ISO country code (e.g. 'us', 'pk')"
    )
    external_id: str | None = Field(
        default=None, description="Unique first-party customer ID / CRM ID"
    )
    client_ip_address: str | None = Field(
        default=None, description="Client IPv4 or IPv6 address (passed raw to Meta)"
    )
    client_user_agent: str | None = Field(
        default=None, description="Browser User-Agent header (passed raw to Meta)"
    )
    fbp: str | None = Field(default=None, description="Meta browser cookie _fbp value")
    fbc: str | None = Field(
        default=None, description="Meta click ID _fbc value (fb.1.timestamp.click_id)"
    )
    client_id: str | None = Field(
        default=None,
        description="Google Analytics 4 client_id (e.g. 123456789.1234567890)",
    )
    user_id: str | None = Field(default=None, description="Google Analytics 4 User-ID")


class CustomData(BaseModel):
    """Event-specific parameters, such as purchase revenue or lead values."""

    value: float | None = Field(default=None, description="Monetary value")
    currency: str | None = Field(
        default=None, description="3-letter ISO 4217 currency code (e.g. USD, EUR)"
    )
    content_name: str | None = Field(
        default=None, description="Product, service, or lead form name"
    )
    content_category: str | None = Field(
        default=None, description="Category of the product or action"
    )
    content_ids: list[str] | None = Field(
        default=None, description="List of product SKUs or content IDs"
    )
    contents: list[dict[str, Any]] | None = Field(
        default=None, description="Itemized contents list for e-commerce purchases"
    )
    num_items: int | None = Field(default=None, description="Number of items in cart or order")
    order_id: str | None = Field(default=None, description="Unique transaction/order ID")
    status: str | None = Field(default=None, description="Status of lead, application, or order")
    custom_properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary custom dimensions or first-party attributes",
    )


class EventRequest(BaseModel):
    """Inbound conversion event payload for ConversionBridge."""

    event_name: str = Field(
        ...,
        description="Standard or custom event name (e.g. 'Lead', 'Purchase', 'Contact')",
        min_length=1,
        max_length=64,
    )
    event_id: str = Field(
        ...,
        description="Unique event identifier used for cross-channel deduplication",
        min_length=1,
        max_length=128,
    )
    event_time: int = Field(
        default_factory=lambda: int(time.time()),
        description="Unix epoch timestamp in seconds",
    )
    event_source_url: str | None = Field(
        default=None,
        description="URL of the webpage where the conversion occurred",
        max_length=1024,
    )
    action_source: str = Field(
        default="website",
        description="Source of event: 'website', 'app', 'system_generated', 'email', 'other'",
    )
    consent: ConsentPayload = Field(
        default_factory=ConsentPayload,
        description="User consent state for analytics and advertising",
    )
    user_data: UserData = Field(
        default_factory=UserData,
        description="User identifiers and browser context for matching",
    )
    custom_data: CustomData = Field(
        default_factory=CustomData,
        description="Event properties, monetary values, and catalog metadata",
    )
    destinations: list[str] = Field(
        default_factory=lambda: ["meta", "ga4"],
        description="Target destinations for this event ('meta', 'ga4')",
    )
    test_mode: bool = Field(
        default=False,
        description="If True, validates and simulates delivery without outbound network calls",
    )

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("event_name cannot be empty or whitespace only")
        # Ensure name doesn't contain HTML tags or control characters
        if any(c in clean for c in "<>;&\n\r\t"):
            raise ValueError("event_name contains forbidden characters")
        return clean

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("event_id cannot be empty or whitespace only")
        if any(c in clean for c in "<>;&\n\r\t"):
            raise ValueError("event_id contains forbidden characters")
        return clean

    @field_validator("event_time")
    @classmethod
    def validate_event_time(cls, v: int) -> int:
        now = int(time.time())
        # Not more than 7 days old (Meta limit is 7 days)
        if v < (now - 7 * 86400):
            raise ValueError("event_time cannot be older than 7 days")
        # Not more than 24 hours in future (clock skew tolerance)
        if v > (now + 86400):
            raise ValueError("event_time cannot be in the future beyond 24 hours")
        return v

    @field_validator("action_source")
    @classmethod
    def validate_action_source(cls, v: str) -> str:
        allowed = {"website", "app", "system_generated", "email", "chat", "physical_store", "other"}
        clean = v.strip().lower()
        if clean not in allowed:
            raise ValueError(f"action_source must be one of {allowed}")
        return clean

    @field_validator("destinations")
    @classmethod
    def validate_destinations(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("destinations list must contain at least one destination")
        allowed = {"meta", "ga4"}
        cleaned = []
        for d in v:
            c = d.strip().lower()
            if c not in allowed:
                raise ValueError(f"Unsupported destination: '{d}'. Must be one of {allowed}")
            if c not in cleaned:
                cleaned.append(c)
        return cleaned


class DestinationDispatchResult(BaseModel):
    """Individual dispatch outcome for a single destination."""

    destination: str = Field(..., description="Target destination ('meta' or 'ga4')")
    status: str = Field(
        ...,
        description="Outcome: 'sent', 'skipped_consent', 'skipped_duplicate', 'skipped_disabled', 'failed', 'test_validated'",
    )
    status_code: int | None = Field(
        default=None, description="HTTP status code from destination API"
    )
    message: str | None = Field(
        default=None, description="Human-readable status summary or error description"
    )
    event_id: str | None = Field(default=None, description="Event ID associated with the dispatch")
    payload_preview: dict[str, Any] | None = Field(
        default=None, description="Safe redacted payload preview (in test mode)"
    )


class EventResponse(BaseModel):
    """Overall response returned by ConversionBridge for an event ingestion request."""

    success: bool = Field(
        ..., description="True if request was validated and processed without fatal errors"
    )
    event_id: str = Field(..., description="The unique event identifier")
    event_name: str = Field(..., description="The processed event name")
    results: list[DestinationDispatchResult] = Field(
        default_factory=list, description="Destination-by-destination dispatch outcomes"
    )
    timestamp: int = Field(
        default_factory=lambda: int(time.time()),
        description="Timestamp of response creation",
    )


class DestinationStatus(BaseModel):
    """Operational status of a configured advertising/analytics destination."""

    destination: str
    enabled: bool
    configured: bool
    details: dict[str, Any] = Field(default_factory=dict)
