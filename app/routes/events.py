"""Conversion event ingestion routes for ConversionBridge."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from ..config import settings
from ..schemas.events import EventRequest, EventResponse
from ..security.authentication import verify_api_key
from ..security.rate_limit import check_rate_limit
from ..services.event_processor import EventProcessor

router = APIRouter(prefix="/api/v1", tags=["Events"])
_processor = EventProcessor()


async def check_payload_size(content_length: int = Header(None)) -> None:
    """Enforce request body size limits to prevent Denial of Service."""
    if content_length and content_length > settings.MAX_PAYLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Payload exceeds maximum allowed size of {settings.MAX_PAYLOAD_SIZE_BYTES} bytes",
        )


@router.post(
    "/events",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest and forward conversion event to authorized destinations",
    dependencies=[
        Depends(verify_api_key),
        Depends(check_rate_limit),
        Depends(check_payload_size),
    ],
)
async def ingest_event(event: EventRequest, request: Request) -> EventResponse:
    """Ingest a first-party conversion event.

    - Validates event parameters and formats
    - Enforces privacy-first consent requirements
    - Suppresses duplicate event submissions
    - Normalizes and dispatches to Meta Conversions API and GA4
    """
    # Augment client IP and user agent if not already provided in payload
    if not event.user_data.client_ip_address and request.client:
        # Check X-Forwarded-For if behind a proxy
        forwarded = request.headers.get("x-forwarded-for")
        event.user_data.client_ip_address = (
            forwarded.split(",")[0].strip() if forwarded else request.client.host
        )

    if not event.user_data.client_user_agent:
        event.user_data.client_user_agent = request.headers.get("user-agent")

    response = await _processor.process_event(event, test_mode=False)
    return response


@router.post(
    "/events/test",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate event processing and payload transformation without outbound network calls",
    dependencies=[
        Depends(verify_api_key),
        Depends(check_rate_limit),
        Depends(check_payload_size),
    ],
)
async def test_event(event: EventRequest, request: Request) -> EventResponse:
    """Dry-run test mode for validating integration schemas and transformations.

    Validates payload structure, tests consent rules, and generates destination
    wire-format previews without sending real events to Meta or Google.
    """
    if not event.user_data.client_ip_address and request.client:
        forwarded = request.headers.get("x-forwarded-for")
        event.user_data.client_ip_address = (
            forwarded.split(",")[0].strip() if forwarded else request.client.host
        )

    if not event.user_data.client_user_agent:
        event.user_data.client_user_agent = request.headers.get("user-agent")

    response = await _processor.process_event(event, test_mode=True)
    return response
