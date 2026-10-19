"""Configuration management for ConversionBridge using Pydantic Settings."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides and safe defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General Service Configuration
    PROJECT_NAME: str = Field(default="ConversionBridge", description="Service name")
    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment: development, test, staging, production",
    )
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    PORT: int = Field(default=8080, description="Server port")

    # API Security & Rate Limiting
    API_KEY: SecretStr | None = Field(
        default=None,
        description="Static API Key required for client requests if REQUIRE_API_KEY is True",
    )
    REQUIRE_API_KEY: bool = Field(
        default=False,
        description="Whether clients must present an X-API-Key or Bearer token header",
    )
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=120,
        description="Sliding window request limit per client IP / key per minute",
    )
    MAX_PAYLOAD_SIZE_BYTES: int = Field(
        default=1024 * 512,  # 512 KB
        description="Maximum allowed request payload size in bytes",
    )

    # Deduplication & Storage
    STORAGE_BACKEND: str = Field(
        default="memory",
        description="Storage backend for event deduplication: 'memory' or 'firestore'",
    )
    FIRESTORE_COLLECTION: str = Field(
        default="conversionbridge_events",
        description="Firestore collection name for event deduplication",
    )
    DEDUPLICATION_WINDOW_HOURS: int = Field(
        default=48,
        description="Time window in hours during which duplicate event_ids are suppressed",
    )

    # Privacy & Consent
    DEFAULT_CONSENT_FAIL_CLOSED: bool = Field(
        default=True,
        description="If true, missing or ambiguous consent blocks outbound event transmission",
    )

    # Meta Conversions API Configuration
    META_ENABLED: bool = Field(
        default=False,
        description="Global switch to enable Meta Conversions API dispatching",
    )
    META_PIXEL_ID: str | None = Field(
        default=None,
        description="Meta Pixel ID or Dataset ID (numeric string)",
    )
    META_ACCESS_TOKEN: SecretStr | None = Field(
        default=None,
        description="System User Access Token for Meta Graph API",
    )
    META_API_VERSION: str = Field(
        default="v20.0",
        description="Meta Graph API version (e.g. v20.0)",
    )
    META_TEST_EVENT_CODE: str | None = Field(
        default=None,
        description="Optional Meta test_event_code for Events Manager testing",
    )
    META_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description="HTTP request timeout for Meta API calls",
    )

    # Google Analytics 4 Measurement Protocol Configuration
    GA4_ENABLED: bool = Field(
        default=False,
        description="Global switch to enable GA4 Measurement Protocol dispatching",
    )
    GA4_MEASUREMENT_ID: str | None = Field(
        default=None,
        description="GA4 Measurement ID (e.g. G-XXXXXXXXXX)",
    )
    GA4_API_SECRET: SecretStr | None = Field(
        default=None,
        description="GA4 Measurement Protocol API Secret created in Admin > Data Streams",
    )
    GA4_DEBUG_MODE: bool = Field(
        default=False,
        description="When true, sends events to GA4 /debug/mp/collect for validation",
    )
    GA4_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description="HTTP request timeout for GA4 API calls",
    )


# Global singleton instance
settings = Settings()
