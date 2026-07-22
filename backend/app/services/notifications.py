"""Delivery of alerts to their channel (currently in-app + Telegram)."""
from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.models.enums import AlertChannel

logger = logging.getLogger("autotracker.notifications")


async def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a plain message via the Telegram Bot API using httpx."""
    if not settings.telegram_enabled:
        return False
    import httpx

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            )
            return resp.status_code == 200
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram send failed: %s", exc)
        return False


def notify(channel: AlertChannel, *, chat_id: str | None, text: str) -> bool:
    """Synchronous entry point used by the scheduler thread."""
    if channel == AlertChannel.telegram and chat_id:
        try:
            return asyncio.run(send_telegram_message(chat_id, text))
        except RuntimeError:
            # Already inside a loop — schedule instead.
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(send_telegram_message(chat_id, text))
            finally:
                loop.close()
    # in_app / email fall through — in-app alerts are just persisted rows.
    return True
