"""Services for consent evaluation, deduplication, validation, and event dispatching."""

from .consent import ConsentEngine
from .deduplication import DeduplicationService
from .event_processor import EventProcessor
from .validation import EventValidator

__all__ = [
    "ConsentEngine",
    "DeduplicationService",
    "EventProcessor",
    "EventValidator",
]
