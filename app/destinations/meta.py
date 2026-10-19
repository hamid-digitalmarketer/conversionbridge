"""Meta Conversions API (CAPI) destination adapter."""

import logging
import re
from typing import Any

import httpx

from ..config import settings
from ..schemas.events import DestinationDispatchResult, DestinationStatus, EventRequest
from ..security.secrets import hash_sha256, mask_secret, redact_dict
from .base import BaseDestination

logger = logging.getLogger(__name__)
_NON_DIGITS = re.compile(r"\D")


class MetaDestination(BaseDestination):
    """Adapter for Meta Conversions API (Graph API server-to-server)."""

    def __init__(self):
        self._name = "meta"

    @property
    def name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        """Check if Pixel ID and Access Token are configured."""
        token = (
            settings.META_ACCESS_TOKEN.get_secret_value() if settings.META_ACCESS_TOKEN else None
        )
        return bool(settings.META_PIXEL_ID and token)

    def get_status(self) -> DestinationStatus:
        token = (
            settings.META_ACCESS_TOKEN.get_secret_value() if settings.META_ACCESS_TOKEN else None
        )
        return DestinationStatus(
            destination=self.name,
            enabled=settings.META_ENABLED,
            configured=self.is_configured(),
            details={
                "pixel_id": settings.META_PIXEL_ID or "[NOT_CONFIGURED]",
                "api_version": settings.META_API_VERSION,
                "has_access_token": bool(token),
                "token_preview": mask_secret(token) if token else None,
                "test_event_code": settings.META_TEST_EVENT_CODE or None,
            },
        )

    def _normalize_phone(self, phone: str) -> str:
        """Strip non-digits for Meta phone number normalization."""
        clean = _NON_DIGITS.sub("", phone)
        return hash_sha256(clean)

    def _build_user_data(self, ud) -> dict[str, Any]:
        """Normalize and hash user data per Meta specifications."""
        user_data: dict[str, Any] = {}

        if ud.email:
            user_data["em"] = [hash_sha256(ud.email)]
        if ud.phone:
            user_data["ph"] = [self._normalize_phone(ud.phone)]
        if ud.first_name:
            user_data["fn"] = [hash_sha256(ud.first_name)]
        if ud.last_name:
            user_data["ln"] = [hash_sha256(ud.last_name)]
        if ud.gender:
            user_data["ge"] = [hash_sha256(ud.gender)]
        if ud.date_of_birth:
            user_data["db"] = [hash_sha256(ud.date_of_birth)]
        if ud.city:
            user_data["ct"] = [hash_sha256(ud.city)]
        if ud.state:
            user_data["st"] = [hash_sha256(ud.state)]
        if ud.zip_code:
            user_data["zp"] = [hash_sha256(ud.zip_code)]
        if ud.country:
            user_data["country"] = [hash_sha256(ud.country)]
        if ud.external_id:
            user_data["external_id"] = [hash_sha256(ud.external_id)]

        # Meta requires unhashed client context
        if ud.client_ip_address:
            user_data["client_ip_address"] = ud.client_ip_address.strip()
        if ud.client_user_agent:
            user_data["client_user_agent"] = ud.client_user_agent.strip()
        if ud.fbp:
            user_data["fbp"] = ud.fbp.strip()
        if ud.fbc:
            user_data["fbc"] = ud.fbc.strip()

        return user_data

    def _build_custom_data(self, cd) -> dict[str, Any]:
        """Extract monetary, catalog, and custom properties."""
        custom_data: dict[str, Any] = {}
        if cd.value is not None:
            custom_data["value"] = cd.value
        if cd.currency:
            custom_data["currency"] = cd.currency.strip().upper()
        if cd.content_name:
            custom_data["content_name"] = cd.content_name.strip()
        if cd.content_category:
            custom_data["content_category"] = cd.content_category.strip()
        if cd.content_ids:
            custom_data["content_ids"] = cd.content_ids
        if cd.contents:
            custom_data["contents"] = cd.contents
        if cd.num_items is not None:
            custom_data["num_items"] = cd.num_items
        if cd.order_id:
            custom_data["order_id"] = cd.order_id.strip()
        if cd.status:
            custom_data["status"] = cd.status.strip()

        # Merge custom properties
        if cd.custom_properties:
            custom_data.update(cd.custom_properties)

        return custom_data

    def transform_payload(self, event: EventRequest) -> dict[str, Any]:
        """Transform EventRequest into Meta Graph API wire payload."""
        event_dict: dict[str, Any] = {
            "event_name": event.event_name,
            "event_time": event.event_time,
            "event_id": event.event_id,
            "action_source": event.action_source,
            "user_data": self._build_user_data(event.user_data),
        }

        if event.event_source_url:
            event_dict["event_source_url"] = event.event_source_url

        custom_data = self._build_custom_data(event.custom_data)
        if custom_data:
            event_dict["custom_data"] = custom_data

        payload: dict[str, Any] = {
            "data": [event_dict],
        }

        if settings.META_TEST_EVENT_CODE:
            payload["test_event_code"] = settings.META_TEST_EVENT_CODE

        return payload

    async def send_event(
        self, event: EventRequest, test_mode: bool = False
    ) -> DestinationDispatchResult:
        if not settings.META_ENABLED:
            return DestinationDispatchResult(
                destination=self.name,
                status="skipped_disabled",
                message="Meta Conversions API integration is disabled in configuration",
                event_id=event.event_id,
            )

        if not self.is_configured():
            return DestinationDispatchResult(
                destination=self.name,
                status="failed",
                message="Meta Pixel ID or Access Token is missing from configuration",
                event_id=event.event_id,
            )

        payload = self.transform_payload(event)

        if test_mode or event.test_mode:
            logger.info("Meta CAPI test mode: validated payload for event '%s'", event.event_id)
            return DestinationDispatchResult(
                destination=self.name,
                status="test_validated",
                status_code=200,
                message="Payload validated successfully in test mode (no live HTTP call sent)",
                event_id=event.event_id,
                payload_preview=redact_dict(payload),
            )

        token = settings.META_ACCESS_TOKEN.get_secret_value() if settings.META_ACCESS_TOKEN else ""
        url = (
            f"https://graph.facebook.com/{settings.META_API_VERSION}/"
            f"{settings.META_PIXEL_ID}/events"
        )
        params = {"access_token": token}

        try:
            async with httpx.AsyncClient(timeout=settings.META_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, params=params)

            if response.is_success:
                resp_json = response.json()
                events_received = resp_json.get("events_received", 1)
                fbtrace_id = resp_json.get("fbtrace_id", "")
                logger.info(
                    "Meta CAPI accepted event '%s' (events_received=%s, fbtrace_id=%s)",
                    event.event_id,
                    events_received,
                    fbtrace_id,
                )
                return DestinationDispatchResult(
                    destination=self.name,
                    status="sent",
                    status_code=response.status_code,
                    message=f"Meta accepted event successfully (events_received: {events_received})",
                    event_id=event.event_id,
                )
            else:
                resp_data = (
                    response.json()
                    if "application/json" in response.headers.get("content-type", "")
                    else {}
                )
                err_msg = resp_data.get("error", {}).get("message", response.text)
                logger.warning(
                    "Meta CAPI rejected event '%s' with HTTP %d: %s",
                    event.event_id,
                    response.status_code,
                    err_msg,
                )
                return DestinationDispatchResult(
                    destination=self.name,
                    status="failed",
                    status_code=response.status_code,
                    message=f"Meta API error ({response.status_code}): {err_msg}",
                    event_id=event.event_id,
                )
        except httpx.TimeoutException:
            logger.error(
                "Meta CAPI timeout after %s seconds for event '%s'",
                settings.META_TIMEOUT_SECONDS,
                event.event_id,
            )
            return DestinationDispatchResult(
                destination=self.name,
                status="failed",
                message=f"Request to Meta Graph API timed out after {settings.META_TIMEOUT_SECONDS}s",
                event_id=event.event_id,
            )
        except Exception as e:
            logger.error(
                "Meta CAPI unexpected dispatch error for event '%s': %s", event.event_id, e
            )
            return DestinationDispatchResult(
                destination=self.name,
                status="failed",
                message=f"Outbound dispatch exception: {type(e).__name__}",
                event_id=event.event_id,
            )
