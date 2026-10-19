"""Event validation service for business rules and destination requirements."""

import re

from ..schemas.events import EventRequest

_URL_PATTERN = re.compile(
    r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
)


class EventValidator:
    """Performs deep validation of conversion event requests before processing."""

    @staticmethod
    def validate_request(req: EventRequest) -> tuple[bool, list[str]]:
        """Validate an EventRequest against business logic and integrity rules.

        Returns (is_valid, list_of_warning_or_error_messages).
        """
        errors: list[str] = []

        # Validate event_source_url if provided
        if req.event_source_url:
            clean_url = req.event_source_url.strip()
            if not _URL_PATTERN.match(clean_url):
                errors.append(f"event_source_url '{clean_url}' is not a valid HTTP/HTTPS URL")

        # Destination-specific prerequisites
        if "ga4" in req.destinations:
            # GA4 Measurement Protocol requires either client_id or user_id
            if not req.user_data.client_id and not req.user_data.user_id:
                errors.append(
                    "GA4 requires either user_data.client_id (e.g. '123456789.1234567890') "
                    "or user_data.user_id to attribute events"
                )

        if "meta" in req.destinations:
            # Meta CAPI requires at least one user identifier for customer matching
            ud = req.user_data
            has_matching_signal = any(
                [
                    ud.email,
                    ud.phone,
                    ud.fbp,
                    ud.fbc,
                    ud.external_id,
                    ud.client_ip_address and ud.client_user_agent,
                ]
            )
            if not has_matching_signal:
                # Warning rather than fatal error (Meta will reject with low match score or 400)
                errors.append(
                    "Meta CAPI requires at least one matching parameter (email, phone, fbp, fbc, external_id, or IP + User-Agent)"
                )

        return (len(errors) == 0, errors)
