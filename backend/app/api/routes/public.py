"""Unauthenticated endpoints guarded by short-lived signed tokens.

Used by the Telegram bot's temporary download links.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse, StreamingResponse

from app.core.security import decode_access_token
from app.database import SessionLocal
from app.models.document import Document
from app.services.storage import get_storage

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/download/{token}")
def download_via_token(token: str):
    payload = decode_access_token(token)
    if not payload or payload.get("scope") != "download":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired link")
    doc_id = payload.get("doc")
    if doc_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Malformed token")

    db = SessionLocal()
    try:
        doc = db.get(Document, int(doc_id))
        if not doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        storage = get_storage()
        url = storage.presigned_url(doc.storage_key, expires_seconds=300)
        if url:
            return RedirectResponse(url)
        data = storage.load(doc.storage_key)
        return StreamingResponse(
            iter([data]),
            media_type=doc.content_type,
            headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
        )
    finally:
        db.close()
