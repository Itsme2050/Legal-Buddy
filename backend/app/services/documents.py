"""Uploaded-document (PDF) analysis.

Strictly separate from live-web research: uploaded documents are labelled
``user_uploaded`` and are never presented as TinyFish-fetched or verified.
"""

from __future__ import annotations

import io
import logging
import re
import uuid
from typing import Optional

from app.core.config import get_settings
from app.schemas import (
    AnalysisResult,
    DocumentAnalyzeResponse,
    FetchStatus,
    Source,
    SourceType,
)
from app.services.gemini_client import GeminiError, analyze_sources_async
from app.services.graph_builder import build_graph

logger = logging.getLogger("legal_buddy.documents")

_MAX_TEXT_CHARS = 60_000


class DocumentValidationError(ValueError):
    """Upload failed validation (type, size, structure)."""


_PDF_MAGIC = b"%PDF"


def _validate_and_extract(data: bytes, filename: str) -> str:
    settings = get_settings()

    name = (filename or "").strip()
    if not name.lower().endswith(".pdf"):
        raise DocumentValidationError("Only .pdf files are supported.")
    if not data:
        raise DocumentValidationError("Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        max_mb = settings.max_upload_bytes // (1024 * 1024)
        raise DocumentValidationError(f"File exceeds the {max_mb} MB limit.")
    if not data[:1024].lstrip().startswith(_PDF_MAGIC):
        raise DocumentValidationError("File does not look like a valid PDF (missing %PDF header).")

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise DocumentValidationError("pypdf is not installed (pip install -r requirements.txt)") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise DocumentValidationError(f"PDF could not be opened: {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            raise DocumentValidationError("Password-protected PDFs are not supported.")

    pages = len(reader.pages)
    if pages == 0:
        raise DocumentValidationError("PDF contains no pages.")

    texts: list[str] = []
    total = 0
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t:
            texts.append(t)
            total += len(t)
        if total >= _MAX_TEXT_CHARS:
            break

    text = "\n\n".join(texts).strip()
    if len(text) < 40:
        raise DocumentValidationError(
            "Could not extract enough text (the PDF may be scanned images only)."
        )
    return text[:_MAX_TEXT_CHARS]


def _preview_markdown(text: str, limit: int = 1500) -> str:
    t = re.sub(r"[ \t]+", " ", text)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if len(t) > limit:
        return t[:limit] + "\n\n… (preview truncated)"
    return t


async def analyze_uploaded_pdf(data: bytes, filename: str) -> DocumentAnalyzeResponse:
    settings = get_settings()
    document_id = str(uuid.uuid4())
    text = _validate_and_extract(data, filename)  # raises DocumentValidationError

    preview = _preview_markdown(text)

    fake_source = Source(
        id="source_document",
        title=filename,
        url="upload://local",
        source_type=SourceType.UNKNOWN,
        authority_label="user-uploaded (not fetched, not verified by TinyFish)",
        fetch_status=FetchStatus.SUCCESS,
        content_markdown=text[: settings.gemini_max_excerpt_chars],
        retrieved_at=None,
    )

    analysis: Optional[AnalysisResult] = None
    graph = None
    error = None
    status = FetchStatus.SUCCESS

    try:
        analysis = await analyze_sources_async(
            question=f"Summarise and map the legal content of this uploaded document: {filename}",
            jurisdiction="stated in the document",
            sources=[fake_source],
            document_text=text,
        )
        # Force source attribution to the uploaded document only
        for e in analysis.entities:
            e.source_ids = ["source_document"] if "source_document" in e.source_ids or not e.source_ids else ["source_document"]
        graph = build_graph(analysis)
    except GeminiError as exc:
        status = FetchStatus.FAILED
        error = str(exc)
        logger.warning("document analysis failed: %s", exc)

    return DocumentAnalyzeResponse(
        document_id=document_id,
        filename=filename,
        size_bytes=len(data),
        text_chars=len(text),
        status=status,
        preview_markdown=preview,
        fetch_status_note="user_uploaded — not fetched by TinyFish and not independently verified",
        analysis=analysis,
        graph=graph,
        error=error,
        disclaimer=(
            "This analysis covers a document you uploaded. It is informational "
            "research assistance, not legal advice."
        ),
    )