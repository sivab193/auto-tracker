from datetime import date

from app.models.enums import DocumentType
from app.ocr.parsers import classify_document, parse_fields


def test_classify_insurance():
    text = "MOTOR INSURANCE POLICY\nPolicy No: ABC/123/456\nSum Insured 500000"
    assert classify_document(text) == DocumentType.insurance


def test_classify_pollution():
    text = "Pollution Under Control Certificate\nCO2 within limits"
    assert classify_document(text) == DocumentType.pollution


def test_parse_insurance_fields():
    text = (
        "TATA AIG General Insurance Company Limited\n"
        "Policy No: MH12/2026/998877\n"
        "Date of Issue: 15/01/2026\n"
        "Valid up to: 14/01/2027\n"
        "Registration No: MH12AB1234\n"
    )
    fields = parse_fields(text, DocumentType.insurance)
    assert fields["document_number"] == "MH12/2026/998877"
    assert fields["expiry_date"] == date(2027, 1, 14).isoformat()
    assert fields["issue_date"] == date(2026, 1, 15).isoformat()
    assert fields["registration_number"] == "MH12AB1234"
    assert "Insurance" in fields.get("issuer", "")


def test_parse_iso_and_text_dates():
    text = "Valid From 2025-03-01 Expires 2026-03-01"
    fields = parse_fields(text, DocumentType.other)
    assert fields["issue_date"] == "2025-03-01"
    assert fields["expiry_date"] == "2026-03-01"


def test_empty_text_returns_other():
    assert classify_document("") == DocumentType.other
    assert parse_fields("", DocumentType.other) == {}
