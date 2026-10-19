"""Pydantic schemas for request and response validation in ConversionBridge."""

from .events import (
    ConsentPayload,
    CustomData,
    DestinationDispatchResult,
    DestinationStatus,
    EventRequest,
    EventResponse,
    UserData,
)

__all__ = [
    "ConsentPayload",
    "CustomData",
    "DestinationDispatchResult",
    "DestinationStatus",
    "EventRequest",
    "EventResponse",
    "UserData",
]
