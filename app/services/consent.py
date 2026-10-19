"""Consent evaluation engine enforcing privacy-first destination routing."""

from ..schemas.events import ConsentPayload


class ConsentEngine:
    """Enforces consent policies across advertising and analytics destinations.

    Fails closed: without explicit consent for a given destination category,
    outbound event dispatching is strictly blocked.
    """

    def __init__(self, fail_closed: bool = True):
        self.fail_closed = fail_closed

    def evaluate(self, consent: ConsentPayload, destination: str) -> tuple[bool, str]:
        """Determine whether the event is permitted to be transmitted to the destination.

        Returns (is_permitted, explanation).
        """
        dest = destination.lower().strip()

        if dest == "meta":
            if consent.advertising is True:
                return True, "User granted advertising consent"
            return (
                False,
                "Advertising consent is False or not granted (required for Meta CAPI)",
            )

        if dest == "ga4":
            if consent.analytics is True:
                return True, "User granted analytics consent"
            return (
                False,
                "Analytics consent is False or not granted (required for GA4 Measurement Protocol)",
            )

        if self.fail_closed:
            return False, f"Unknown destination '{destination}' blocked under fail-closed policy"

        return False, f"Unsupported destination: '{destination}'"
