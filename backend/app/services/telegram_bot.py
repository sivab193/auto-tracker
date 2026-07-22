"""Telegram bot: fetch vehicle documents, with auto-deletion of sent files
and temporary download links.

Design notes
------------
* Fully optional. If ``TELEGRAM_BOT_TOKEN`` is empty or python-telegram-bot
  isn't installed, ``run_in_thread()`` is a no-op.
* Runs in a dedicated background thread with its own asyncio loop so it can
  live alongside uvicorn (which owns the main thread).
* Sent documents are deleted after ``TELEGRAM_AUTODELETE_SECONDS`` via an
  async task; a signed temporary link (handled by the API) is offered as a
  persistent alternative.

Commands
--------
  /start           – greeting + help
  /link <code>     – bind this chat to an AutoTracker account
  /vehicles        – list your vehicles
  /docs            – list documents (inline buttons to fetch)
"""
from __future__ import annotations

import asyncio
import logging
import threading

from sqlalchemy import select

from app.config import settings
from app.core.security import create_access_token
from app.database import SessionLocal
from app.models.document import Document
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.storage import get_storage

logger = logging.getLogger("autotracker.telegram")

_thread: threading.Thread | None = None
_application = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _user_for_chat(chat_id: str) -> User | None:
    db = SessionLocal()
    try:
        return db.scalar(select(User).where(User.telegram_chat_id == str(chat_id)))
    finally:
        db.close()


def temp_download_link(document_id: int) -> str:
    """Build a short-lived signed link the API can validate at /public/download."""
    token = create_access_token(
        subject=f"doc:{document_id}", extra={"scope": "download", "doc": document_id}
    )
    return f"{settings.public_base_url.rstrip('/')}/api/public/download/{token}"


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #
async def _cmd_start(update, context):  # noqa: ANN001
    await update.message.reply_text(
        "🚗 <b>AutoTracker</b>\n\n"
        "Link this chat to your account, then fetch documents on the go.\n\n"
        "• /link &lt;code&gt; — connect (generate a code in the web app)\n"
        "• /vehicles — list your vehicles\n"
        "• /docs — browse & fetch documents\n\n"
        "Sent files auto-delete after a few minutes for privacy.",
        parse_mode="HTML",
    )


async def _cmd_link(update, context):  # noqa: ANN001
    chat_id = str(update.effective_chat.id)
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /link <code>")
        return
    code = args[0].strip()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.telegram_link_code == code))
        if not user:
            await update.message.reply_text("❌ Invalid or expired code.")
            return
        user.telegram_chat_id = chat_id
        user.telegram_link_code = None
        db.commit()
        await update.message.reply_text(f"✅ Linked to {user.email}. Try /vehicles.")
    finally:
        db.close()


async def _cmd_vehicles(update, context):  # noqa: ANN001
    chat_id = str(update.effective_chat.id)
    user = _user_for_chat(chat_id)
    if not user:
        await update.message.reply_text("This chat isn't linked yet. Use /link <code>.")
        return
    db = SessionLocal()
    try:
        vehicles = db.scalars(select(Vehicle).where(Vehicle.owner_id == user.id)).all()
        if not vehicles:
            await update.message.reply_text("No vehicles yet.")
            return
        lines = ["🚗 <b>Your vehicles</b>"]
        for v in vehicles:
            lines.append(f"• {v.display_name} — {v.registration_number}")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()


async def _cmd_docs(update, context):  # noqa: ANN001
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    chat_id = str(update.effective_chat.id)
    user = _user_for_chat(chat_id)
    if not user:
        await update.message.reply_text("This chat isn't linked yet. Use /link <code>.")
        return
    db = SessionLocal()
    try:
        stmt = (
            select(Document)
            .join(Vehicle, Document.vehicle_id == Vehicle.id)
            .where(Vehicle.owner_id == user.id, Document.is_current.is_(True))
            .order_by(Document.expiry_date.is_(None), Document.expiry_date)
        )
        docs = db.scalars(stmt).all()
        if not docs:
            await update.message.reply_text("No documents yet.")
            return
        buttons = []
        for d in docs[:25]:
            label = d.title or d.doc_type.value.replace("_", " ").title()
            exp = f" (exp {d.expiry_date.isoformat()})" if d.expiry_date else ""
            buttons.append([InlineKeyboardButton(f"{label}{exp}", callback_data=f"doc:{d.id}")])
        await update.message.reply_text(
            "📄 Pick a document to fetch:", reply_markup=InlineKeyboardMarkup(buttons)
        )
    finally:
        db.close()


async def _on_callback(update, context):  # noqa: ANN001
    from telegram import InputFile

    query = update.callback_query
    await query.answer()
    data = query.data or ""
    if not data.startswith("doc:"):
        return
    doc_id = int(data.split(":", 1)[1])
    chat_id = str(query.message.chat_id)
    user = _user_for_chat(chat_id)
    if not user:
        await query.message.reply_text("This chat isn't linked.")
        return

    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if not doc:
            await query.message.reply_text("Document not found.")
            return
        vehicle = db.get(Vehicle, doc.vehicle_id)
        if not vehicle or vehicle.owner_id != user.id:
            await query.message.reply_text("Not authorised for that document.")
            return
        try:
            payload = get_storage().load(doc.storage_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to load doc %s: %s", doc_id, exc)
            await query.message.reply_text("Could not read that file from storage.")
            return

        link = temp_download_link(doc.id)
        caption = (
            f"📄 {doc.title or doc.doc_type.value}\n"
            f"🔗 Temporary link: {link}"
        )
        sent = await context.bot.send_document(
            chat_id=chat_id,
            document=InputFile(payload, filename=doc.original_filename),
            caption=caption,
        )
        # Auto-delete the file message after the configured delay.
        secs = settings.telegram_autodelete_seconds
        if secs and secs > 0:
            asyncio.create_task(_autodelete(context, chat_id, sent.message_id, secs))
    finally:
        db.close()


async def _autodelete(context, chat_id, message_id, delay: int):  # noqa: ANN001
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #
def _build_application():
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
    )

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("help", _cmd_start))
    app.add_handler(CommandHandler("link", _cmd_link))
    app.add_handler(CommandHandler("vehicles", _cmd_vehicles))
    app.add_handler(CommandHandler("docs", _cmd_docs))
    app.add_handler(CallbackQueryHandler(_on_callback))
    return app


def _run_loop() -> None:
    global _application
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        _application = _build_application()
        loop.run_until_complete(_application.initialize())
        loop.run_until_complete(_application.start())
        loop.run_until_complete(_application.updater.start_polling(drop_pending_updates=True))
        logger.info("telegram bot polling started")
        loop.run_forever()
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram bot stopped: %s", exc)


def run_in_thread() -> None:
    """Start the bot in a daemon thread if configured. No-op otherwise."""
    global _thread
    if not settings.telegram_enabled:
        logger.info("telegram bot disabled (no token)")
        return
    try:
        import telegram  # noqa: F401
    except Exception:  # noqa: BLE001
        logger.warning("python-telegram-bot not installed; bot disabled")
        return
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_run_loop, name="telegram-bot", daemon=True)
    _thread.start()
