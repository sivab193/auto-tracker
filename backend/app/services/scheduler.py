"""Background scheduler that runs the daily expiry sweep.

Uses APScheduler's BackgroundScheduler. If APScheduler isn't installed or the
scheduler is disabled, start()/shutdown() become no-ops.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.database import SessionLocal
from app.services.alerts import run_sweep

logger = logging.getLogger("autotracker.scheduler")

_scheduler = None


def _sweep_job() -> None:
    db = SessionLocal()
    try:
        run_sweep(db)
    except Exception as exc:  # noqa: BLE001
        logger.exception("expiry sweep failed: %s", exc)
    finally:
        db.close()


def start() -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("scheduler disabled")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except Exception as exc:  # noqa: BLE001
        logger.warning("APScheduler unavailable (%s); scheduler not started", exc)
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _sweep_job,
        CronTrigger(hour=settings.alert_sweep_hour, minute=0),
        id="daily_expiry_sweep",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("scheduler started (daily sweep at %02d:00)", settings.alert_sweep_hour)
    # Kick off one sweep at boot so alerts exist immediately.
    _sweep_job()


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:  # noqa: BLE001
            pass
        _scheduler = None
