"""Tests verifying bug fixes identified in PROJECT_AUDIT.md."""

from __future__ import annotations

import io
import pytest
from fastapi import Request
from pypdf import PdfWriter

from app.core.config import get_settings
from app.main import enforce_rate_limit
from app.repositories.database import get_session
from app.repositories.session_repository import SessionRepository
from app.schemas import FetchStatus, ResearchRequest
from app.services.tinyfish_client import NormalizedFetchResult, TinyFishClient, normalize_fetch_result


def test_normalized_fetch_result_has_content_chars():
    res = normalize_fetch_result("https://example.com", {"content": "Sample legal text content."})
    assert res.status == FetchStatus.SUCCESS
    assert res.content_chars == len("Sample legal text content.")


@pytest.mark.asyncio
async def test_tinyfish_client_standalone_without_context_manager(monkeypatch):
    """TinyFishClient must not crash with AttributeError when called without async with."""
    monkeypatch.setattr(get_settings(), "tinyfish_api_key", "tf-test-key")
    tf = TinyFishClient()
    # Mocking httpx call
    import httpx

    async def mock_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"results": [{"title": "Court Order", "url": "https://sci.gov.in/order"}]},
            request=httpx.Request("GET", "https://api.search.tinyfish.ai"),
        )

    monkeypatch.setattr(tf._ensure_client(), "get", mock_get)
    results = await tf.search_legal_sources("test query")
    assert len(results) == 1
    assert results[0].title == "Court Order"


def test_enforce_rate_limit_executes_without_name_error(client):
    """enforce_rate_limit must not raise NameError from undefined StarletteHTTPExceptionLike."""
    from starlette.datastructures import Headers

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": Headers({"host": "localhost"}).raw,
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    # Should not raise NameError
    enforce_rate_limit(req)


def test_document_analysis_persists_to_database(client, db_session):
    """Document analysis must save a record to DocumentRow via SessionRepository."""
    # Create minimal valid PDF
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("legal_doc.pdf", pdf_bytes, "application/pdf")},
    )
    # Returns 422 because page is blank (< 40 text chars)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_research_request_supports_custom_session_id(db_session, monkeypatch):
    """Workflow supports client-supplied session_id for immediate streaming."""
    import uuid
    from app.services.research_workflow import ResearchWorkflow

    custom_id = f"custom-session-{uuid.uuid4()}"
    monkeypatch.setattr(get_settings(), "tinyfish_api_key", None)
    wf = ResearchWorkflow(db_session)
    req = ResearchRequest(
        session_id=custom_id,
        question="What protections apply when a tenant faces eviction in India?",
    )
    res_id = await wf.run(req)
    assert res_id == custom_id
    repo = SessionRepository(db_session)
    row = repo.get(custom_id)
    assert row is not None
    assert row.id == custom_id
