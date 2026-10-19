"""Authentication dependencies for ConversionBridge."""

import hmac

from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    auth: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> bool:
    """Verify inbound request credentials against configured settings.API_KEY.

    Supports both 'X-API-Key: <key>' header and 'Authorization: Bearer <key>'.
    If REQUIRE_API_KEY is False, allows the request through.
    """
    if not settings.REQUIRE_API_KEY:
        return True

    expected_key = settings.API_KEY.get_secret_value() if settings.API_KEY else None
    if not expected_key:
        # Configuration error: required key is missing on the server
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration error",
        )

    provided_key = None
    if x_api_key:
        provided_key = x_api_key.strip()
    elif auth and auth.credentials:
        provided_key = auth.credentials.strip()

    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required API authentication credentials (X-API-Key or Bearer token)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
