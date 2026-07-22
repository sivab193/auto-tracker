"""Document upload (with OCR auto-extraction), listing, versioning, download."""
from __future__ import annotations

import json
import uuid
from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_vehicle, get_current_user, require_vehicle_write
from app.database import get_db
from app.models.document import Document
from app.models.enums import DocumentType
from app.models.user import User
from app.models.vehicle import Vehicle
from app.ocr import classify_document, extract_text, parse_fields
from app.schemas.document import DocumentRead, DocumentUpdate, OCRPreview
from app.services import audit
from app.services.storage import get_storage, guess_extension

router = APIRouter(tags=["documents"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _run_ocr(data: bytes, content_type: str, filename: str, override_type: DocumentType | None):
    result = extract_text(data, content_type=content_type, filename=filename)
    doc_type = override_type or classify_document(result.text, filename)
    fields = parse_fields(result.text, doc_type, filename) if result.text else {}
    return result, doc_type, fields


def _parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@router.post(
    "/vehicles/{vehicle_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: DocumentType | None = Form(default=None),
    title: str | None = Form(default=None),
    auto_ocr: bool = Form(default=True),
    supersede_id: int | None = Form(default=None),
    # Manual overrides (win over OCR).
    expiry_date: str | None = Form(default=None),
    issue_date: str | None = Form(default=None),
    document_number: str | None = Form(default=None),
    issuer: str | None = Form(default=None),
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(require_vehicle_write),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large (max 25MB)")

    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    ocr_text = None
    ocr_conf = None
    fields: dict = {}
    resolved_type = doc_type or DocumentType.other
    if auto_ocr:
        result, resolved_type, fields = _run_ocr(data, content_type, filename, doc_type)
        ocr_text = result.text or None
        ocr_conf = result.confidence

    # Persist bytes to storage.
    ext = guess_extension(filename)
    storage = get_storage()
    object_key = f"{vehicle.id}_{uuid.uuid4().hex}" + (f".{ext}" if ext else "")
    key = storage.save(data, key=object_key, content_type=content_type)

    # Versioning: superseding an existing document.
    version = 1
    superseded: Document | None = None
    if supersede_id is not None:
        superseded = db.get(Document, supersede_id)
        if not superseded or superseded.vehicle_id != vehicle.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid supersede_id")
        superseded.is_current = False
        version = superseded.version + 1
        if doc_type is None:
            resolved_type = superseded.doc_type

    doc = Document(
        vehicle_id=vehicle.id,
        uploaded_by_id=user.id,
        doc_type=resolved_type,
        title=title or (superseded.title if superseded else None),
        storage_key=key,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(data),
        ocr_text=ocr_text,
        ocr_confidence=ocr_conf,
        extracted_fields=json.dumps(fields) if fields else None,
        expiry_date=_parse_iso(expiry_date) or _parse_iso(fields.get("expiry_date")),
        issue_date=_parse_iso(issue_date) or _parse_iso(fields.get("issue_date")),
        document_number=document_number or fields.get("document_number"),
        issuer=issuer or fields.get("issuer"),
        version=version,
        is_current=True,
        supersedes_id=supersede_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    audit.record(
        db, action="document.upload", actor_id=user.id, family_id=vehicle.family_id,
        entity_type="document", entity_id=doc.id,
        detail=f"{resolved_type.value} for {vehicle.registration_number}",
    )
    return DocumentRead.model_validate(doc)


@router.post("/documents/ocr-preview", response_model=OCRPreview)
async def ocr_preview(
    file: UploadFile = File(...),
    doc_type: DocumentType | None = Form(default=None),
    _user: User = Depends(get_current_user),
) -> OCRPreview:
    """Run OCR on an upload without persisting — powers the upload form preview."""
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    result, resolved_type, fields = _run_ocr(
        data, file.content_type or "", file.filename or "", doc_type
    )
    return OCRPreview(
        doc_type=resolved_type,
        ocr_text=(result.text or "")[:4000],
        ocr_confidence=result.confidence,
        fields=fields,
    )


@router.get("/vehicles/{vehicle_id}/documents", response_model=list[DocumentRead])
def list_documents(
    include_history: bool = Query(default=False),
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(get_accessible_vehicle),
) -> list[DocumentRead]:
    stmt = select(Document).where(Document.vehicle_id == vehicle.id)
    if not include_history:
        stmt = stmt.where(Document.is_current.is_(True))
    stmt = stmt.order_by(Document.expiry_date.is_(None), Document.expiry_date)
    docs = db.scalars(stmt).all()
    return [DocumentRead.model_validate(d) for d in docs]


def _load_doc(db: Session, user: User, document_id: int) -> Document:
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    # Reuse vehicle access rules.
    get_accessible_vehicle(doc.vehicle_id, db=db, user=user)
    return doc


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    return DocumentRead.model_validate(_load_doc(db, user, document_id))


@router.get("/documents/{document_id}/versions", response_model=list[DocumentRead])
def document_versions(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    doc = _load_doc(db, user, document_id)
    # Walk the supersedes chain in both directions.
    chain: list[Document] = [doc]
    cur = doc
    while cur.supersedes_id:
        prev = db.get(Document, cur.supersedes_id)
        if not prev:
            break
        chain.append(prev)
        cur = prev
    # Forward links (documents that supersede this one).
    forward = db.scalars(
        select(Document).where(Document.supersedes_id == doc.id)
    ).all()
    chain = list(forward) + chain
    chain.sort(key=lambda d: d.version, reverse=True)
    return [DocumentRead.model_validate(d) for d in chain]


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = _load_doc(db, user, document_id)
    storage = get_storage()
    url = storage.presigned_url(doc.storage_key, expires_seconds=300)
    if url:
        return RedirectResponse(url)
    payload = storage.load(doc.storage_key)
    return StreamingResponse(
        iter([payload]),
        media_type=doc.content_type,
        headers={"Content-Disposition": f'inline; filename="{doc.original_filename}"'},
    )


@router.patch("/documents/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int,
    body: DocumentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    doc = _load_doc(db, user, document_id)
    require_vehicle_write(doc.vehicle_id, db=db, user=user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(doc, k, v)
    db.commit()
    db.refresh(doc)
    return DocumentRead.model_validate(doc)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = _load_doc(db, user, document_id)
    vehicle = require_vehicle_write(doc.vehicle_id, db=db, user=user)
    try:
        get_storage().delete(doc.storage_key)
    except Exception:  # noqa: BLE001
        pass
    audit.record(
        db, action="document.delete", actor_id=user.id, family_id=vehicle.family_id,
        entity_type="document", entity_id=doc.id, commit=False,
    )
    db.delete(doc)
    db.commit()
