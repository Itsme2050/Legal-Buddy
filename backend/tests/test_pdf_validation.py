"""PDF upload validation tests."""

from __future__ import annotations

import io

import pytest

from app.services.documents import DocumentValidationError, _preview_markdown, _validate_and_extract


def _make_pdf(text: str) -> bytes:
    """Build a minimal single-page PDF with embedded text (no external tools)."""
    # Use pypdf's writer for a real, parseable PDF.
    from pypdf import PdfWriter
    from pypdf.generic import (
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
    )

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # simplest reliable path: use reportlab if available else fallback content stream
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1", "replace")
    stream = DecodedStreamObject()
    stream.set_data(content)
    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    page[NameObject("/Contents")] = stream
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_rejects_non_pdf_extension():
    with pytest.raises(DocumentValidationError, match="\\.pdf"):
        _validate_and_extract(b"%PDF-1.4 whatever", "notes.txt")


def test_rejects_empty_file():
    with pytest.raises(DocumentValidationError, match="empty"):
        _validate_and_extract(b"", "x.pdf")


def test_rejects_wrong_magic_bytes():
    with pytest.raises(DocumentValidationError, match="%PDF"):
        _validate_and_extract(b"NOT_A_PDF " + b"x" * 200, "fake.pdf")


def test_rejects_oversized_file(monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_bytes", 1024)
    with pytest.raises(DocumentValidationError, match="limit"):
        _validate_and_extract(b"%PDF-1.4" + b"x" * 5000, "big.pdf")


def test_accepts_valid_pdf_with_text():
    data = _make_pdf(
        "Section 14 of the Rent Control Act protects tenants from eviction without notice."
    )
    text = _validate_and_extract(data, "notice.pdf")
    assert "Section 14" in text or "eviction" in text.lower()


def test_preview_markdown_truncates():
    long_text = "word " * 2000
    preview = _preview_markdown(long_text, limit=200)
    assert len(preview) < 300
    assert "preview truncated" in preview


def test_preview_markdown_collapses_whitespace():
    preview = _preview_markdown("a   b\n\n\n\nc")
    assert "  " not in preview