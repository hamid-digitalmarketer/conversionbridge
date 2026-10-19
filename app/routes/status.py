"""Destination status endpoint for ConversionBridge."""

from fastapi import APIRouter, Depends

from ..schemas.events import DestinationStatus
from ..security.authentication import verify_api_key
from ..services.event_processor import EventProcessor

router = APIRouter(prefix="/api/v1", tags=["Destinations"])
_processor = EventProcessor()


@router.get(
    "/destinations/status",
    response_model=list[DestinationStatus],
    summary="Get operational status of configured destinations",
    dependencies=[Depends(verify_api_key)],
)
async def get_destinations_status():
    """Return operational status for Meta Conversions API and GA4 integrations.

    Access tokens and API secrets are never exposed in plaintext.
    """
    statuses = []
    for adapter in _processor.destinations.values():
        statuses.append(adapter.get_status())
    return statuses
