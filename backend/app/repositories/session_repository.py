"""Repository layer for research sessions, sources, usage, documents.

Kept deliberately thin so the ORM can be swapped for PostgreSQL without
touching service logic.
"""

from __future__ import annotations

import uuid
from datetime import timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import DocumentRow, ResearchSessionRow, SourceRow, UsageRow, utcnow
from app.schemas import (
    AnalysisResult,
    FetchStatus,
    HistoryItem,
    HistoryResponse,
    PipelineStage,
    ResearchResult,
    SessionStatus,
    Source,
    UsageRecord,
)

DISCLAIMER = (
    "Legal Buddy provides informational research assistance, not legal advice. "
    "Verify important information against official sources and consult a qualified "
    "lawyer before making consequential legal decisions."
)

STAGE_TEMPLATES: list[dict[str, str]] = [
    {"key": "prepare", "label": "Preparing legal search"},
    {"key": "tinyfish_search", "label": "Searching live sources with TinyFish"},
    {"key": "select", "label": "Selecting relevant documents"},
    {"key": "tinyfish_fetch", "label": "Fetching source content with TinyFish"},
    {"key": "gemini", "label": "Analyzing retrieved evidence with Gemini"},
    {"key": "graph", "label": "Building the legal relationship graph"},
    {"key": "done", "label": "Research complete"},
]


def default_stages() -> list[PipelineStage]:
    return [PipelineStage(**t) for t in STAGE_TEMPLATES]


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    # ----- create / read -------------------------------------------------
    def create_session(
        self,
        question: str,
        jurisdiction: str,
        topic: str,
        source_preference: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> ResearchSessionRow:
        row = ResearchSessionRow(
            id=str(uuid.uuid4()),
            question=question,
            jurisdiction=jurisdiction,
            topic=topic,
            source_preference=source_preference,
            date_from=date_from,
            date_to=date_to,
            status=SessionStatus.PENDING.value,
            stages=[s.model_dump(mode="json") for s in default_stages()],
            disclaimer=DISCLAIMER,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get(self, session_id: str) -> Optional[ResearchSessionRow]:
        return self.db.get(ResearchSessionRow, session_id)

    def update(
        self,
        session_id: str,
        *,
        status: Optional[SessionStatus] = None,
        error: Optional[str] = None,
        stages: Optional[list[PipelineStage]] = None,
        search_step: Optional[dict[str, Any]] = None,
        fetch_step: Optional[dict[str, Any]] = None,
        analysis: Optional[AnalysisResult] = None,
        graph: Optional[dict[str, Any]] = None,
        usage: Optional[UsageRecord] = None,
    ) -> Optional[ResearchSessionRow]:
        row = self.get(session_id)
        if row is None:
            return None
        if status is not None:
            row.status = status.value
        if error is not None:
            row.error = error
        if stages is not None:
            row.stages = [s.model_dump(mode="json") for s in stages]
        if search_step is not None:
            row.search_step = search_step
        if fetch_step is not None:
            row.fetch_step = fetch_step
        if analysis is not None:
            row.analysis = analysis.model_dump(mode="json")
        if graph is not None:
            row.graph = graph
        if usage is not None:
            row.usage = usage.model_dump(mode="json")
        row.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    # ----- sources -------------------------------------------------------
    def replace_sources(self, session_id: str, sources: list[Source]) -> None:
        self.db.execute(delete(SourceRow).where(SourceRow.session_id == session_id))
        for s in sources:
            self.db.add(
                SourceRow(
                    session_id=session_id,
                    source_id=s.id,
                    title=s.title,
                    url=s.url,
                    source_type=s.source_type.value,
                    authority_label=s.authority_label,
                    court_or_authority=s.court_or_authority,
                    decision_date=s.decision_date,
                    snippet=s.snippet,
                    retrieved_at=s.retrieved_at,
                    fetch_status=s.fetch_status.value,
                    fetch_error=s.fetch_error,
                    content_markdown=s.content_markdown,
                    content_chars=s.content_chars,
                    excerpts=[e.model_dump(mode="json") for e in s.excerpts],
                    provider_metadata=s.provider_metadata,
                    rank=s.rank,
                )
            )
        self.db.commit()

    def get_sources(self, session_id: str) -> list[Source]:
        rows = self.db.scalars(
            select(SourceRow)
            .where(SourceRow.session_id == session_id)
            .order_by(SourceRow.rank.is_(None), SourceRow.rank, SourceRow.id)
        ).all()
        return [self._to_source(r) for r in rows]

    @staticmethod
    def _to_source(r: SourceRow) -> Source:
        from app.schemas import SourceExcerpt

        return Source(
            id=r.source_id,
            title=r.title,
            url=r.url,
            source_type=SourceType_from(r.source_type),
            authority_label=r.authority_label,
            court_or_authority=r.court_or_authority,
            decision_date=r.decision_date,
            snippet=r.snippet,
            retrieved_at=r.retrieved_at,
            fetch_status=FetchStatus(r.fetch_status),
            fetch_error=r.fetch_error,
            content_markdown=r.content_markdown,
            content_chars=r.content_chars,
            excerpts=[SourceExcerpt(**e) for e in (r.excerpts or [])],
            provider_metadata=r.provider_metadata or {},
            rank=r.rank,
        )

    # ----- serialization -------------------------------------------------
    def to_result(self, row: ResearchSessionRow) -> ResearchResult:
        analysis = None
        if row.analysis:
            try:
                analysis = AnalysisResult.model_validate(row.analysis)
            except Exception:
                analysis = None
        return ResearchResult(
            session_id=row.id,
            status=SessionStatus(row.status),
            question=row.question,
            jurisdiction=row.jurisdiction,
            topic=row.topic,
            created_at=row.created_at,
            updated_at=row.updated_at,
            stages=[PipelineStage.model_validate(s) for s in (row.stages or [])],
            search_step=row.search_step,
            fetch_step=row.fetch_step,
            sources=self.get_sources(row.id),
            analysis=analysis,
            graph=row.graph,
            usage=UsageRecord.model_validate(row.usage) if row.usage else None,
            error=row.error,
            disclaimer=row.disclaimer or DISCLAIMER,
        )

    # ----- history -------------------------------------------------------
    def history(self, limit: int = 50) -> HistoryResponse:
        rows = self.db.scalars(
            select(ResearchSessionRow)
            .order_by(ResearchSessionRow.created_at.desc())
            .limit(limit)
        ).all()
        items: list[HistoryItem] = []
        for r in rows:
            sources = self.get_sources(r.id)
            summary_preview = None
            if r.analysis:
                try:
                    a = AnalysisResult.model_validate(r.analysis)
                    summary_preview = a.summary.plain_language[:280]
                except Exception:
                    summary_preview = None
            items.append(
                HistoryItem(
                    session_id=r.id,
                    question=r.question,
                    jurisdiction=r.jurisdiction,
                    topic=r.topic,
                    status=SessionStatus(r.status),
                    created_at=r.created_at,
                    source_count=len(sources),
                    fetched_count=sum(
                        1 for s in sources if s.fetch_status == FetchStatus.SUCCESS
                    ),
                    entity_count=len((r.graph or {}).get("nodes", [])),
                    summary_preview=summary_preview,
                )
            )
        return HistoryResponse(items=items, total=len(items))

    def delete_session(self, session_id: str) -> bool:
        row = self.get(session_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def purge_expired(self) -> int:
        settings = get_settings()
        cutoff = utcnow() - timedelta(days=settings.session_retention_days)
        rows = self.db.scalars(
            select(ResearchSessionRow).where(ResearchSessionRow.created_at < cutoff)
        ).all()
        for r in rows:
            self.db.delete(r)
        self.db.commit()
        return len(rows)

    # ----- usage ---------------------------------------------------------
    def record_usage(self, usage: UsageRecord) -> None:
        self.db.add(
            UsageRow(
                session_id=usage.session_id,
                plan=usage.plan,
                search_requests=usage.search_requests,
                fetch_requests=usage.fetch_requests,
                fetched_successfully=usage.fetched_successfully,
                analyzed_sources=usage.analyzed_sources,
                gemini_prompt_tokens=usage.gemini_prompt_tokens,
                gemini_completion_tokens=usage.gemini_completion_tokens,
                estimated_cost_usd=usage.estimated_cost_usd,
            )
        )
        self.db.commit()

    def usage_summary(self) -> dict[str, Any]:
        rows = self.db.scalars(select(UsageRow)).all()
        by_plan: dict[str, dict[str, Any]] = {}
        for r in rows:
            bucket = by_plan.setdefault(
                r.plan,
                {
                    "sessions": 0,
                    "search_requests": 0,
                    "fetch_requests": 0,
                    "fetched_successfully": 0,
                    "analyzed_sources": 0,
                    "gemini_prompt_tokens": 0,
                    "gemini_completion_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
            )
            bucket["sessions"] += 1
            bucket["search_requests"] += r.search_requests
            bucket["fetch_requests"] += r.fetch_requests
            bucket["fetched_successfully"] += r.fetched_successfully
            bucket["analyzed_sources"] += r.analyzed_sources
            bucket["gemini_prompt_tokens"] += r.gemini_prompt_tokens or 0
            bucket["gemini_completion_tokens"] += r.gemini_completion_tokens or 0
            bucket["estimated_cost_usd"] += r.estimated_cost_usd or 0.0
        return by_plan

    def daily_usage(self, plan: str = "free") -> dict[str, int]:
        settings = get_settings()
        day_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        rows = self.db.scalars(
            select(UsageRow).where(
                UsageRow.plan == plan,
                UsageRow.created_at >= day_start,
            )
        ).all()
        search = sum(r.search_requests for r in rows)
        fetch = sum(r.fetch_requests for r in rows)
        return {
            "search_requests": search,
            "fetch_requests": fetch,
            "search_limit": (
                settings.usage_daily_search_limit_free
                if plan == "free"
                else settings.usage_daily_search_limit_pro
            ),
            "fetch_limit": (
                settings.usage_daily_fetch_limit_free
                if plan == "free"
                else settings.usage_daily_fetch_limit_pro
            ),
        }

    # ----- documents -----------------------------------------------------
    def save_document(
        self,
        *,
        document_id: str,
        filename: str,
        size_bytes: int,
        text_chars: int,
        status: FetchStatus,
        preview_markdown: str,
        analysis: Optional[AnalysisResult] = None,
        graph: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> DocumentRow:
        row = DocumentRow(
            id=document_id,
            filename=filename,
            size_bytes=size_bytes,
            text_chars=text_chars,
            status=status.value,
            preview_markdown=preview_markdown,
            analysis=analysis.model_dump(mode="json") if analysis else None,
            graph=graph,
            error=error,
        )
        self.db.merge(row)
        self.db.commit()
        return row

    def get_document(self, document_id: str) -> Optional[DocumentRow]:
        return self.db.get(DocumentRow, document_id)


def SourceType_from(value: str):
    from app.schemas import SourceType

    try:
        return SourceType(value)
    except ValueError:
        return SourceType.UNKNOWN