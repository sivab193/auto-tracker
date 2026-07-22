"""Document — an uploaded file plus OCR-extracted metadata.

Supports versioning: uploading a fresh copy of the same logical document
(e.g. a renewed insurance policy) creates a new row that points back to the
previous version via ``supersedes_id``. Only the latest is ``is_current``.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import DocumentType
from app.models.mixins import TimestampMixin
from app.models.types import EnumStr


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    doc_type: Mapped[DocumentType] = mapped_column(
        EnumStr(DocumentType), default=DocumentType.other, index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # --- Storage ---
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    # --- Extracted / structured metadata ---
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    issuer: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # Raw OCR text + a JSON blob of extra parsed fields (stored as text).
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Versioning ---
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    vehicle = relationship("Vehicle", back_populates="documents")
    supersedes = relationship("Document", remote_side="Document.id")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document {self.id} {self.doc_type} v{self.version}>"
