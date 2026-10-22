"""Session persistence tests through the repository layer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.repositories.database import SessionLocal, init_db
from app.repositories.session_repository import DISCLAIMER, SessionRepository
from app.schemas import (
    AnalysisResult,
    FetchStatus,
    PipelineStage,
    SearchStep,
    SessionStatus,
    Source,
    SourceExcerpt,
    SourceType,
    Summary,
    Takeaway,
    UsageRecord,
)


@pytest.fixture()
def repo():
    init_db()
    db = SessionLocal()
    try:
        yield SessionRepository(db)
    finally:
        db.close()


def _minimal_analysis() -> AnalysisResult:
    return AnalysisResult(
        summary=Summary(
            plain_language="Notice is required before eviction.",
            key_takeaways=[Takeahead := Takeaway(text="Notice required", source_ids=["source_1"])],
        ),
    )


def test_create_and_read_session(repo):
    row = repo.create_session(
        question="What protects tenants from eviction?",
        jurisdiction="India",
        topic="tenancy",
        source_preference="official_first",
    )
    assert row.id
    assert row.status == SessionStatus.PENDING.value
    assert row.disclaimer == DISCLAIMER
    got = repo.get(row.id)
    assert got is not None
    assert got.question.startswith("What protects")


def test_stages_populated_with_all_pipeline_keys(repo):
    row = repo.create_session(
        question="q?" + "x" * 10,
        jurisdiction="India",
        topic="general",
        source_preference="broad",
    )
    stages = [s["key"] for s in row.stages]
    assert stages == [
        "prepare",
        "tinyfish_search",
        "select",
        "tinyfish_fetch",
        "gemini",
        "graph",
        "done",
    ]


def test_sources_roundtrip(repo):
    row = repo.create_session(
        question="q?" + "x" * 10,
        jurisdiction="India",
        topic="general",
        source_preference="broad",
    )
    sources = [
        Source(
            id="source_1",
            title="Supreme Court",
            url="https://sci.gov.in/x",
            source_type=SourceType.COURT,
            fetch_status=FetchStatus.SUCCESS,
            content_markdown="# ruling",
            content_chars=8,
            excerpts=[SourceExcerpt(text="excerpt", url="https://sci.gov.in/x")],
            retrieved_at=datetime.now(timezone.utc),
        ),
        Source(
            id="source_2",
            title="Blocked page",
            url="https://example.test/blocked",
            fetch_status=FetchStatus.FAILED,
            fetch_error="HTTP 403",
        ),
    ]
    repo.replace_sources(row.id, sources)
    loaded = repo.get_sources(row.id)
    assert [s.id for s in loaded] == ["source_1", "source_2"]
    assert loaded[0].source_type == SourceType.COURT
    assert loaded[0].excerpts[0].text == "excerpt"
    assert loaded[0].content_markdown == "# ruling"
    assert loaded[1].fetch_status == FetchStatus.FAILED


def test_update_status_and_analysis(repo):
    row = repo.create_session(
        question="q?" + "x" * 10,
        jurisdiction="India",
        topic="general",
        source_preference="broad",
    )
    analysis = _minimal_analysis()
    search_step = SearchStep(query="q", result_count=3)
    repo.update(
        row.id,
        status=SessionStatus.COMPLETED,
        analysis=analysis,
        search_step=search_step.model_dump(mode="json"),
    )
    result = repo.to_result(repo.get(row.id))
    assert result.status == SessionStatus.COMPLETED
    assert result.analysis is not None
    assert result.analysis.summary.plain_language.startswith("Notice")
    assert result.search_step is not None and result.search_step.result_count == 3


def test_delete_session(repo):
    row = repo.create_session(
        question="q?" + "x" * 10,
        jurisdiction="India",
        topic="general",
        source_preference="broad",
    )
    assert repo.delete_session(row.id) is True
    assert repo.get(row.id) is None
    assert repo.delete_session(row.id) is False


def test_history_listing(repo):
    row = repo.create_session(
        question="history check question",
        jurisdiction="India",
        topic="general",
        source_preference="broad",
    )
    h = repo.history()
    assert h.total >= 1
    item = next(i for i in h.items if i.session_id == row.id)
    assert item.question == "history check question"
    assert item.source_count == 0


def test_usage_record_and_summary(repo):
    row = repo.create_session(
        question="usage check question",
        jurisdiction="India",
        topic="general",
        source_preference="broad",
    )
    usage = UsageRecord(
        session_id=row.id,
        search_requests=1,
        fetch_requests=5,
        fetched_successfully=3,
        analyzed_sources=3,
        estimated_cost_usd=0.0015,
    )
    repo.record_usage(usage)
    summary = repo.usage_summary()
    assert "free" in summary
    assert summary["free"]["search_requests"] >= 1
    daily = repo.daily_usage("free")
    assert daily["search_requests"] >= 1
    assert daily["search_limit"] > 0