"""Abstract destination interface for conversion platforms."""

from abc import ABC, abstractmethod
from typing import Any

from ..schemas.events import DestinationDispatchResult, DestinationStatus, EventRequest


class BaseDestination(ABC):
    """Abstract base class for all conversion tracking destinations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the destination (e.g. 'meta', 'ga4')."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether the necessary API credentials and identifiers are configured."""
        pass

    @abstractmethod
    def get_status(self) -> DestinationStatus:
        """Return the operational and configuration status of this destination."""
        pass

    @abstractmethod
    def transform_payload(self, event: EventRequest) -> dict[str, Any]:
        """Convert an internal EventRequest into the platform's specific wire format."""
        pass

    @abstractmethod
    async def send_event(
        self, event: EventRequest, test_mode: bool = False
    ) -> DestinationDispatchResult:
        """Transmit an event to the destination API (or simulate in test_mode)."""
        pass
