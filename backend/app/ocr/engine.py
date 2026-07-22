"""Tesseract-backed OCR with graceful degradation.

If pytesseract / the tesseract binary / poppler are not available, functions
return an empty result instead of raising, so document upload still works
(fields can be filled in manually).
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger("autotracker.ocr")


@dataclass
class OCRResult:
    text: str = ""
    confidence: int | None = None
    pages: int = 0
    available: bool = True
    error: str | None = None
    words: list[dict] = field(default_factory=list)


def ocr_available() -> bool:
    if not settings.ocr_enabled:
        return False
    try:
        import pytesseract  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def _configure_tesseract() -> object | None:
    try:
        import pytesseract
    except Exception:  # noqa: BLE001
        return None
    if settings.tesseract_cmd and settings.tesseract_cmd != "tesseract":
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    return pytesseract


def _images_from_pdf(data: bytes) -> list:
    try:
        from pdf2image import convert_from_bytes

        return convert_from_bytes(data, dpi=200)
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdf rasterisation failed: %s", exc)
        return []


def _image_from_bytes(data: bytes):
    try:
        from PIL import Image

        return Image.open(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        logger.warning("image decode failed: %s", exc)
        return None


def extract_text(data: bytes, content_type: str = "", filename: str = "") -> OCRResult:
    """Run OCR over an uploaded file's bytes. Never raises."""
    if not settings.ocr_enabled:
        return OCRResult(available=False, error="ocr disabled")

    pytesseract = _configure_tesseract()
    if pytesseract is None:
        return OCRResult(available=False, error="pytesseract not installed")

    is_pdf = "pdf" in (content_type or "").lower() or filename.lower().endswith(".pdf")
    images = []
    try:
        if is_pdf:
            images = _images_from_pdf(data)
        else:
            img = _image_from_bytes(data)
            if img is not None:
                images = [img]
    except Exception as exc:  # noqa: BLE001
        return OCRResult(available=False, error=str(exc))

    if not images:
        return OCRResult(available=False, error="no rasterisable pages")

    texts: list[str] = []
    confidences: list[int] = []
    lang = settings.ocr_languages or "eng"
    for img in images:
        try:
            texts.append(pytesseract.image_to_string(img, lang=lang))
            data_dict = pytesseract.image_to_data(
                img, lang=lang, output_type=pytesseract.Output.DICT
            )
            page_conf = [int(c) for c in data_dict.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0]
            confidences.extend(page_conf)
        except Exception as exc:  # noqa: BLE001
            logger.warning("tesseract failed on a page: %s", exc)

    text = "\n".join(t for t in texts if t).strip()
    avg_conf = int(sum(confidences) / len(confidences)) if confidences else None
    return OCRResult(text=text, confidence=avg_conf, pages=len(images), available=True)
