"""Health check endpoint for ConversionBridge."""

import time

from fastapi import APIRouter

from ..config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service health check")
async def health_check():
    """Return minimal operational health status.

    Does not disclose environment secrets or private credentials.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": int(time.time()),
    }
