"""Main application entrypoint for ConversionBridge.

Supports both ASGI local development (Uvicorn) and Firebase Cloud Functions v2.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes.events import router as events_router
from .routes.health import router as health_router
from .routes.status import router as status_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("conversionbridge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info(
        "Starting %s (%s environment, backend=%s)",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
        settings.STORAGE_BACKEND,
    )
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Privacy-First Server-Side Conversion Tracking for Meta Ads & Google Analytics 4. "
        "Collects consent-aware first-party conversion events and forwards them using "
        "server-to-server integrations."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to verified brand domain origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include versioned API routers
app.include_router(health_router)
app.include_router(status_router)
app.include_router(events_router)


# Firebase Cloud Functions v2 entrypoint
try:
    from fastapi.testclient import TestClient
    from firebase_functions import https_fn

    _fb_client = TestClient(app, raise_server_exceptions=False)

    @https_fn.on_request(timeout_sec=30, memory=512)
    def conversionbridge_api(req: https_fn.Request) -> https_fn.Response:
        """Firebase Cloud Functions v2 HTTPS handler bridging to the FastAPI application."""
        headers = dict(req.headers)
        method = req.method
        url = req.full_path if hasattr(req, "full_path") and req.full_path else req.path
        body = req.get_data()

        resp = _fb_client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
        )
        return https_fn.Response(
            response=resp.content,
            status=resp.status_code,
            headers=dict(resp.headers),
        )

except ImportError:
    pass
