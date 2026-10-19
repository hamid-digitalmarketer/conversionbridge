"""Google Analytics 4 (GA4) Measurement Protocol destination adapter."""

import logging
import re
from typing import Any

import httpx

from ..config import settings
from ..schemas.events import DestinationDispatchResult, DestinationStatus, EventRequest
from ..security.secrets import mask_secret, redact_dict
from .base import BaseDestination

logger = logging.getLogger(__name__)

# Standard GA4 name mapping for common performance marketing events
_NAME_MAP = {
    "lead": "generate_lead",
    "purchase": "purchase",
    "contact": "contact",
    "viewcontent": "view_item",
    "view_content": "view_item",
    "addtocart": "add_to_cart",
    "add_to_cart": "add_to_cart",
    "initiatecheckout": "begin_checkout",
    "initiate_checkout": "begin_checkout",
    "completeregistration": "sign_up",
    "complete_registration": "sign_up",
}

_SAFE_PARAM_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,39}$")


class GA4Destination(BaseDestination):
    """Adapter for Google Analytics 4 Measurement Protocol."""

    def __init__(self):
        self._name = "ga4"

    @property
    def name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        """Check if Measurement ID and API Secret are configured."""
        secret = settings.GA4_API_SECRET.get_secret_value() if settings.GA4_API_SECRET else None
        return bool(settings.GA4_MEASUREMENT_ID and secret)

    def get_status(self) -> DestinationStatus:
        secret = settings.GA4_API_SECRET.get_secret_value() if settings.GA4_API_SECRET else None
        return DestinationStatus(
            destination=self.name,
            enabled=settings.GA4_ENABLED,
            configured=self.is_configured(),
            details={
                "measurement_id": settings.GA4_MEASUREMENT_ID or "[NOT_CONFIGURED]",
                "has_api_secret": bool(secret),
                "api_secret_preview": mask_secret(secret) if secret else None,
                "debug_mode": settings.GA4_DEBUG_MODE,
            },
        )

    def _normalize_event_name(self, name: str) -> str:
        """Normalize event name to GA4 standards (max 40 chars, alphanumeric + underscores)."""
        lower = name.strip().lower()
        if lower in _NAME_MAP:
            return _NAME_MAP[lower]

        # Replace non-alphanumeric with underscores
        clean = re.sub(r"[^a-zA-Z0-9_]", "_", lower).strip("_")
        if not clean or not clean[0].isalpha():
            clean = "evt_" + clean
        return clean[:40]

    def _build_event_params(self, event: EventRequest) -> dict[str, Any]:
        """Map custom data and event identifiers into GA4 event parameters."""
        params: dict[str, Any] = {
            "event_id": event.event_id,
        }

        cd = event.custom_data
        if cd.value is not None:
            params["value"] = cd.value
        if cd.currency:
            params["currency"] = cd.currency.strip().upper()
        if cd.content_name:
            params["item_name"] = cd.content_name.strip()
        if cd.content_category:
            params["item_category"] = cd.content_category.strip()
        if cd.order_id:
            params["transaction_id"] = cd.order_id.strip()

        if event.event_source_url:
            params["page_location"] = event.event_source_url

        # Merge custom properties (up to 25 parameters per GA4 event limit)
        if cd.custom_properties:
            for k, v in cd.custom_properties.items():
                if len(params) >= 25:
                    break
                clean_k = re.sub(r"[^a-zA-Z0-9_]", "_", k.strip().lower())[:40]
                if clean_k and clean_k[0].isalpha():
                    params[clean_k] = v

        return params

    def transform_payload(self, event: EventRequest) -> dict[str, Any]:
        """Transform EventRequest into GA4 Measurement Protocol wire payload."""
        # Client ID is required by GA4 Measurement Protocol
        client_id = event.user_data.client_id
        if not client_id:
            # Fall back to external_id or hash of IP/User-Agent if unavailable
            client_id = event.user_data.external_id or f"anon.{event.event_id}"

        ga4_event = {
            "name": self._normalize_event_name(event.event_name),
            "params": self._build_event_params(event),
        }

        payload: dict[str, Any] = {
            "client_id": client_id,
            "timestamp_micros": int(event.event_time * 1_000_000),
            "non_personalized_ads": not event.consent.advertising,
            "events": [ga4_event],
        }

        if event.user_data.user_id:
            payload["user_id"] = event.user_data.user_id.strip()

        return payload

    async def send_event(
        self, event: EventRequest, test_mode: bool = False
    ) -> DestinationDispatchResult:
        if not settings.GA4_ENABLED:
            return DestinationDispatchResult(
                destination=self.name,
                status="skipped_disabled",
                message="Google Analytics 4 integration is disabled in configuration",
                event_id=event.event_id,
            )

        if not self.is_configured():
            return DestinationDispatchResult(
                destination=self.name,
                status="failed",
                message="GA4 Measurement ID or API Secret is missing from configuration",
                event_id=event.event_id,
            )

        payload = self.transform_payload(event)

        if test_mode or event.test_mode:
            logger.info("GA4 test mode: validated payload for event '%s'", event.event_id)
            return DestinationDispatchResult(
                destination=self.name,
                status="test_validated",
                status_code=200,
                message="Payload validated successfully in test mode (no live HTTP call sent)",
                event_id=event.event_id,
                payload_preview=redact_dict(payload),
            )

        secret = settings.GA4_API_SECRET.get_secret_value() if settings.GA4_API_SECRET else ""
        endpoint_path = "/debug/mp/collect" if settings.GA4_DEBUG_MODE else "/mp/collect"
        url = f"https://www.google-analytics.com{endpoint_path}"
        params = {
            "measurement_id": settings.GA4_MEASUREMENT_ID,
            "api_secret": secret,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.GA4_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, params=params)

            # In production, GA4 returns 204 No Content on receipt
            # In debug mode, GA4 returns 200 OK with validationMessages JSON
            if response.status_code in (200, 204):
                if settings.GA4_DEBUG_MODE:
                    try:
                        resp_data = response.json()
                        messages = resp_data.get("validationMessages", [])
                        if messages:
                            logger.warning(
                                "GA4 debug validation warnings for event '%s': %s",
                                event.event_id,
                                messages,
                            )
                            return DestinationDispatchResult(
                                destination=self.name,
                                status="sent",
                                status_code=response.status_code,
                                message=f"Accepted by GA4 DebugView with {len(messages)} validation hint(s)",
                                event_id=event.event_id,
                            )
                    except Exception:
                        pass

                logger.info("GA4 Measurement Protocol accepted event '%s'", event.event_id)
                return DestinationDispatchResult(
                    destination=self.name,
                    status="sent",
                    status_code=response.status_code,
                    message="GA4 accepted event via Measurement Protocol (HTTP 204/200)",
                    event_id=event.event_id,
                )
            else:
                logger.warning(
                    "GA4 rejected event '%s' with HTTP %d", event.event_id, response.status_code
                )
                return DestinationDispatchResult(
                    destination=self.name,
                    status="failed",
                    status_code=response.status_code,
                    message=f"GA4 returned HTTP error {response.status_code}: {response.text}",
                    event_id=event.event_id,
                )
        except httpx.TimeoutException:
            logger.error(
                "GA4 timeout after %s seconds for event '%s'",
                settings.GA4_TIMEOUT_SECONDS,
                event.event_id,
            )
            return DestinationDispatchResult(
                destination=self.name,
                status="failed",
                message=f"Request to GA4 Measurement Protocol timed out after {settings.GA4_TIMEOUT_SECONDS}s",
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error("GA4 unexpected dispatch error for event '%s': %s", event.event_id, e)
            return DestinationDispatchResult(
                destination=self.name,
                status="failed",
                message=f"Outbound dispatch exception: {type(e).__name__}",
                event_id=event.event_id,
            )
