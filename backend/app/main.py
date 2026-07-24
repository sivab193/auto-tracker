"""AutoTracker API entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import (
    alerts,
    analytics,
    auth,
    documents,
    family,
    fuel,
    public,
    services,
    vehicles,
)
from app.config import settings
from app.database import init_db
from app.services import scheduler, telegram_bot

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("autotracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting %s v%s (env=%s)", settings.app_name, __version__, settings.environment)
    init_db()
    if settings.serverless:
        logger.info("serverless mode: scheduler and telegram polling disabled")
    else:
        scheduler.start()
        telegram_bot.run_in_thread()
    try:
        yield
    finally:
        if not settings.serverless:
            scheduler.shutdown()
        logger.info("shutdown complete")


app = FastAPI(
    title=f"{settings.app_name} API",
    version=__version__,
    description="Automobile document & service management portal.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(vehicles.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(services.router, prefix=API_PREFIX)
app.include_router(fuel.router, prefix=API_PREFIX)
app.include_router(family.router, prefix=API_PREFIX)
app.include_router(alerts.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(public.router, prefix=API_PREFIX)


@app.get("/health", tags=["meta"])
def health() -> dict:
    from app.ocr import ocr_available

    return {
        "status": "ok",
        "version": __version__,
        "single_user": settings.single_user,
        "ocr": ocr_available(),
        "telegram": settings.telegram_enabled,
        "scheduler": settings.scheduler_enabled,
    }


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}
