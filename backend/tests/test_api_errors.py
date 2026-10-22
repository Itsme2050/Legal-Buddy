"""API error-response tests (TestClient, no live credentials)."""

from __future__ import annotations

import pytest


def test_health_returns_integration_statuses(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "Legal Buddy"
    assert {i["provider"] for i in body["integrations"]} >= {
        "tinyfish_search",
        "tinyfish_fetch",
        "gemini",
    }
    for i in body["integrations"]:
        assert isinstance(i["configured"], bool)
        # never leak secrets
        assert "key" not in str(i).lower() or "apikey" not in str(i).lower()


def test_integrations_status_no_secrets(client):
    resp = client.get("/api/integrations/status")
    assert resp.status_code == 200
    body = resp.text
    assert "GEMINI_API_KEY" not in body.replace("GEMINI_API_KEY missing", "")
    assert "TINYFISH_API_KEY" not in body.replace("TINYFISH_API_KEY missing", "")
    assert '"configured"' in body


def test_research_rejects_short_question(client):
    resp = client.post("/api/research", json={"question": "hi"})
    assert resp.status_code == 422


def test_research_rejects_bad_date_format(client):
    resp = client.post(
        "/api/research",
        json={"question": "What are tenant eviction protections in India?", "date_from": "not-a-date"},
    )
    assert resp.status_code == 422


def test_get_session_404_has_error_schema(client):
    resp = client.get("/api/research/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]


def test_graph_404(client):
    resp = client.get("/api/research/nope/graph")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_delete_history_404(client):
    resp = client.delete("/api/history/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_history_returns_shape(client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and "total" in body


def test_usage_summary_shape(client):
    resp = client.get("/api/usage/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "by_plan" in body and "daily" in body and "assumptions" in body


def test_upload_rejects_non_pdf(client):
    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("notes.txt", b"hello world this is not a pdf", "text/plain")},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_document"


def test_upload_rejects_bad_pdf_magic(client):
    resp = client.post(
        "/api/documents/analyze",
        files={"file": ("x.pdf", b"NOTPDF this is fake content " * 10, "application/pdf")},
    )
    assert resp.status_code == 422


def test_sse_stream_terminal_session_emits_status_and_done(client, monkeypatch):
    """SSE must emit properly-framed events with JSON-serializable stages and
    terminate with a done event for a terminal (failed) session."""
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "tinyfish_api_key", None)
    resp = client.post(
        "/api/research",
        json={"question": "What protections apply when a tenant faces eviction in India?"},
    )
    session_id = resp.json()["session_id"]

    stream = client.get(f"/api/research/{session_id}/stream")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    body = stream.text
    # Real newlines on the wire (not literal \\n text), proper SSE framing
    assert "event: status\ndata: {" in body
    assert "event: done\ndata: {" in body
    assert "\\n" not in body, "SSE frames must use real newlines"
    # Stages payload is JSON (datetimes serialized, not raw objects)
    import json as _json

    status_line = [l for l in body.splitlines() if l.startswith("data: {")][0]
    data = _json.loads(status_line[len("data: "):])
    assert data["status"] == "failed"
    assert isinstance(data["stages"], list) and data["stages"]


def test_research_without_credentials_fails_honestly(client, monkeypatch):
    """With no TINYFISH key, the workflow must fail loudly and store an
    honest failed session — never fabricate sources, analysis or a graph."""
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "tinyfish_api_key", None)

    resp = client.post(
        "/api/research",
        json={
            "question": "What protections apply when a tenant faces eviction in India?",
            "jurisdiction": "India",
            "topic": "tenancy",
        },
    )
    # The session-model contract: a persisted, clearly-failed session whose
    # error names the missing credential and whose evidence set is empty.
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    result = body["result"]
    assert "TINYFISH_API_KEY" in (result["error"] or "")
    # No fabricated evidence whatsoever
    assert result["sources"] == []
    assert result["analysis"] is None
    assert result["graph"] in (None, {"nodes": [], "edges": []})
    # The failing stage is visible, not hidden
    failed_stages = [s for s in result["stages"] if s["status"] == "failed"]
    assert failed_stages, "at least one stage must be marked failed"
    never_complete = [s for s in result["stages"] if s["status"] == "completed"]
    assert all(s["key"] == "prepare" for s in never_complete), (
        "no downstream stage may claim completion after a search failure"
    )