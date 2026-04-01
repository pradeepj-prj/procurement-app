from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.endpoints.health import router as health_router
from app.api.middleware.cors import setup_cors

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise shared resources on startup; clean up on shutdown."""
    from app.db import get_backend

    logger.info("Initialising database backend…")
    app.state.backend = get_backend()
    logger.info("Backend ready: %s", type(app.state.backend).__name__)
    yield


app = FastAPI(
    title="Procurement GenAI Q&A",
    version="2.0.0",
    lifespan=lifespan,
)

setup_cors(app)
app.include_router(health_router, tags=["health"])
