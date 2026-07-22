from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DocumentType


class DocumentUpdate(BaseModel):
    doc_type: DocumentType | None = None
    title: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    document_number: str | None = None
    issuer: str | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    doc_type: DocumentType
    title: str | None
    original_filename: str
    content_type: str
    size_bytes: int
    issue_date: date | None
    expiry_date: date | None
    document_number: str | None
    issuer: str | None
    ocr_confidence: int | None
    version: int
    is_current: bool
    supersedes_id: int | None
    extracted_fields: dict[str, Any] | None = None

    @field_validator("extracted_fields", mode="before")
    @classmethod
    def _parse_json(cls, v: Any) -> Any:
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


class OCRPreview(BaseModel):
    """Result of running OCR without persisting — used for the upload preview."""
    doc_type: DocumentType
    ocr_text: str = ""
    ocr_confidence: int | None = None
    fields: dict[str, Any] = Field(default_factory=dict)
