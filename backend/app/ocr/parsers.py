"""Doc-type classification and field extraction from OCR text.

Strategy:
  1. classify_document() scores the text against keyword sets per doc type.
  2. parse_fields() pulls common fields (dates, numbers, issuer) with regex,
     then applies doc-type-specific extractors for things like policy numbers
     or registration numbers.

Everything is best-effort: unknown text yields DocumentType.other and an
empty-ish field dict that the user can correct in the UI.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.models.enums import DocumentType

# --- Classification keywords ------------------------------------------------

_KEYWORDS: dict[DocumentType, list[str]] = {
    DocumentType.insurance: [
        "insurance", "policy", "insured", "premium", "sum insured", "idv",
        "third party", "comprehensive", "cover note",
    ],
    DocumentType.registration: [
        "registration", "certificate of registration", "rc", "registered owner",
        "chassis", "vehicle registration",
    ],
    DocumentType.pollution: [
        "pollution", "puc", "emission", "pucc", "under control", "co2", "smoke",
    ],
    DocumentType.road_tax: ["road tax", "tax token", "motor vehicle tax", "tax receipt"],
    DocumentType.fitness: ["fitness", "certificate of fitness"],
    DocumentType.permit: ["permit", "national permit", "goods carriage"],
    DocumentType.driving_license: [
        "driving licence", "driving license", "dl no", "licence to drive",
    ],
    DocumentType.warranty: ["warranty", "guarantee", "warranty card"],
    DocumentType.invoice: ["invoice", "tax invoice", "bill", "amount payable", "gst"],
}

# --- Date handling ----------------------------------------------------------

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

# 12/03/2025, 12-03-2025, 12.03.2025
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
# 12 Mar 2025 / 12 March, 2025
_TEXT_DATE = re.compile(
    r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{2,4})\b", re.IGNORECASE
)
# 2025-03-12 (ISO)
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")

_EXPIRY_HINTS = re.compile(
    r"(valid\s*(?:up\s*to|till|until|upto)|expiry|expires|valid\s*to|"
    r"date\s*of\s*expiry|good\s*through|renewal\s*date)",
    re.IGNORECASE,
)
_ISSUE_HINTS = re.compile(
    r"(date\s*of\s*issue|issued\s*on|issue\s*date|valid\s*from|w\.?e\.?f)",
    re.IGNORECASE,
)


def _norm_year(y: int) -> int:
    if y < 100:
        return 2000 + y if y < 70 else 1900 + y
    return y


def _try_date(fragment: str) -> date | None:
    m = _ISO_DATE.search(fragment)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _safe_date(y, mo, d)
    m = _TEXT_DATE.search(fragment)
    if m:
        d = int(m.group(1))
        mo = _MONTHS.get(m.group(2)[:3].lower())
        y = _norm_year(int(m.group(3)))
        if mo:
            return _safe_date(y, mo, d)
    m = _NUMERIC_DATE.search(fragment)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), _norm_year(int(m.group(3)))
        # Prefer DD/MM/YYYY; fall back to MM/DD if day > 12.
        if a > 12 and b <= 12:
            return _safe_date(c, b, a)
        if b > 12 and a <= 12:
            return _safe_date(c, a, b)
        return _safe_date(c, b, a)  # default day-first
    return None


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _all_dates(text: str) -> list[date]:
    out: list[date] = []
    for rx in (_ISO_DATE, _TEXT_DATE, _NUMERIC_DATE):
        for m in rx.finditer(text):
            dt = _try_date(m.group(0))
            if dt:
                out.append(dt)
    return out


def _hinted_date(text: str, hint_rx: re.Pattern) -> date | None:
    """Find a date appearing shortly after a hint keyword."""
    for m in hint_rx.finditer(text):
        window = text[m.end(): m.end() + 40]
        dt = _try_date(window)
        if dt:
            return dt
    return None


# --- Doc-specific field regexes ---------------------------------------------

_POLICY_NO = re.compile(
    r"(?:policy\s*(?:no|number|#)|policy\s*no\.?)\s*[:\-]?\s*([A-Z0-9\/\-]{5,25})",
    re.IGNORECASE,
)
_REG_NO = re.compile(r"\b([A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{0,3}[\s\-]?\d{3,4})\b")
_VIN = re.compile(r"\b([A-HJ-NPR-Z0-9]{17})\b")
_CHASSIS = re.compile(r"chassis\s*(?:no|number)?\s*[:\-]?\s*([A-Z0-9]{6,20})", re.IGNORECASE)
_ENGINE = re.compile(r"engine\s*(?:no|number)?\s*[:\-]?\s*([A-Z0-9]{5,20})", re.IGNORECASE)
_INVOICE_NO = re.compile(
    r"(?:invoice\s*(?:no|number|#)|bill\s*no)\s*[:\-]?\s*([A-Z0-9\/\-]{3,25})",
    re.IGNORECASE,
)
_AMOUNT = re.compile(r"(?:total|amount|grand\s*total)\s*[:\-]?\s*[₹$€£]?\s*([\d,]+\.?\d{0,2})",
                     re.IGNORECASE)
_DL_NO = re.compile(r"\b([A-Z]{2}[-\s]?\d{2}\s?\d{11})\b")


def classify_document(text: str, filename: str = "") -> DocumentType:
    haystack = f"{text}\n{filename}".lower()
    if not haystack.strip():
        return DocumentType.other

    best_type = DocumentType.other
    best_score = 0
    for dtype, kws in _KEYWORDS.items():
        score = sum(haystack.count(kw) for kw in kws)
        if score > best_score:
            best_score, best_type = score, dtype
    return best_type if best_score > 0 else DocumentType.other


def parse_fields(text: str, doc_type: DocumentType, filename: str = "") -> dict[str, Any]:
    """Return a dict of extracted fields. Keys used by the API:
    expiry_date, issue_date, document_number, issuer, plus type-specific extras.
    """
    fields: dict[str, Any] = {}
    if not text:
        return fields

    # Dates: prefer hinted, else infer from the set of all dates found.
    expiry = _hinted_date(text, _EXPIRY_HINTS)
    issue = _hinted_date(text, _ISSUE_HINTS)
    dates = sorted(set(_all_dates(text)))
    if expiry is None and dates:
        # Heuristic: the latest future-ish date is most likely the expiry.
        future = [d for d in dates if d >= date.today()]
        expiry = (future[0] if future else dates[-1])
    if issue is None and dates:
        issue = dates[0]

    if expiry:
        fields["expiry_date"] = expiry.isoformat()
    if issue:
        fields["issue_date"] = issue.isoformat()

    def _first(rx: re.Pattern) -> str | None:
        m = rx.search(text)
        return m.group(1).strip() if m else None

    reg = _first(_REG_NO)
    if reg:
        fields["registration_number"] = re.sub(r"\s+", "", reg).upper()
    vin = _first(_VIN)
    if vin:
        fields["vin"] = vin
    chassis = _first(_CHASSIS)
    if chassis:
        fields["chassis_number"] = chassis
    engine = _first(_ENGINE)
    if engine:
        fields["engine_number"] = engine

    if doc_type == DocumentType.insurance:
        pol = _first(_POLICY_NO)
        if pol:
            fields["document_number"] = pol
    elif doc_type == DocumentType.invoice:
        inv = _first(_INVOICE_NO)
        if inv:
            fields["document_number"] = inv
        amt = _first(_AMOUNT)
        if amt:
            fields["amount"] = amt.replace(",", "")
    elif doc_type == DocumentType.driving_license:
        dl = _first(_DL_NO)
        if dl:
            fields["document_number"] = re.sub(r"\s+", "", dl)

    # Issuer: first non-empty line that looks like an org name.
    issuer = _guess_issuer(text)
    if issuer:
        fields["issuer"] = issuer

    return fields


_ISSUER_HINTS = re.compile(
    r"(insurance|assurance|motor|rto|transport|authority|company|ltd|limited|"
    r"general|corporation|govt|government|department)",
    re.IGNORECASE,
)


def _guess_issuer(text: str) -> str | None:
    for raw in text.splitlines():
        line = raw.strip()
        if 4 <= len(line) <= 60 and _ISSUER_HINTS.search(line):
            return line
    return None
