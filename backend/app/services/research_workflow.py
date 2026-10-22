"""End-to-end research workflow orchestration.

Stage keys (mirrored exactly by the frontend pipeline UI):

  prepare -> tinyfish_search -> select -> tinyfish_fetch -> gemini -> graph -> done

Failures are surfaced honestly: session becomes ``partial`` or ``failed`` with a
human-readable error — never faked, never fabricated results.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.session_repository import SessionRepository, default_stages
from app.schemas import (
    FetchStatus,
    NextStep,
    PipelineStage,
    ResearchRequest,
    SearchStep,
    FetchStep,
    SessionStatus,
    Source,
    StageStatus,
    UsageRecord,
)
from app.services.gemini_client import (
    GeminiConfigError,
    GeminiError,
    analyze_sources_async,
)
from app.services.graph_builder import build_graph
from app.services.tinyfish_client import (
    NormalizedFetchResult,
    NormalizedSearchResult,
    TinyFishClient,
    TinyFishConfigError,
    TinyFishEmptyResultError,
    TinyFishError,
    extract_relevant_excerpts,
    rank_for_fetch,
)

logger = logging.getLogger("legal_buddy.workflow")

_TOPIC_TERMS: dict[str, list[str]] = {
    "tenancy": ["tenant", "landlord", "eviction", "rent", "lease", "tenancy"],
    "consumer_rights": ["consumer", "complaint", "deficiency", "refund", "forum"],
    "municipal": ["municipal", "corporation", "encroachment", "property tax", "wards"],
    "employment": ["employer", "employee", "termination", "wages", "industrial"],
    "education": ["school", "admission", "exam", "university", "education"],
    "public_services": ["rti", "public information", "government service", "grievance"],
    "general": [],
}


def build_search_query(question: str, jurisdiction: str, topic: str, prefer_official: bool) -> str:
    """Deterministic query construction (no model involved unless it adds value).

    Adds jurisdiction/topic terms only when they are not already present, so
    the query stays focused instead of echoing the question back.
    """
    q = re.sub(r"\s+", " ", question).strip().rstrip("?")
    ql = q.lower()
    terms = _TOPIC_TERMS.get(topic, [])
    extras = [t for t in terms if t not in ql][:3]
    domain_hint = ""
    if prefer_official:
        domain_hint = ' (site:gov.in OR site:nic.in OR site:indiacode.nic.in OR site:sci.gov.in OR site:ecourts.gov.in)'
    jurisdiction_part = ""
    if jurisdiction and jurisdiction.lower() != "global" and jurisdiction.lower() not in ql:
        jurisdiction_part = f" {jurisdiction}"
    topic_part = " ".join(extras)
    return f"{q}{jurisdiction_part} {topic_part}{domain_hint}".strip()


class ResearchWorkflow:
    """Async orchestrator persisted through the repository layer."""

    def __init__(self, db: Session):
        self.repo = SessionRepository(db)
        self.settings = get_settings()

    # ----- stage helpers -------------------------------------------------
    def _stages(self, repo: SessionRepository, session_id: str) -> list[PipelineStage]:
        row = repo.get(session_id)
        return [PipelineStage.model_validate(s) for s in (row.stages or [])] if row else default_stages()

    def _mark(
        self,
        session_id: str,
        key: str,
        status: StageStatus,
        detail: Optional[str] = None,
    ) -> None:
        stages = self._stages(self.repo, session_id)
        now = datetime.now(timezone.utc)
        for st in stages:
            if st.key == key:
                st.status = status
                if detail:
                    st.detail = detail
                if status == StageStatus.RUNNING and st.started_at is None:
                    st.started_at = now
                if status in (StageStatus.COMPLETED, StageStatus.FAILED, StageStatus.SKIPPED):
                    st.finished_at = now
                break
        self.repo.update(session_id, stages=stages)

    # ----- main entry ----------------------------------------------------
    async def run(self, request: ResearchRequest) -> str:
        row = self.repo.create_session(
            question=request.question,
            jurisdiction=request.jurisdiction,
            topic=request.topic,
            source_preference=request.source_preference,
            date_from=request.date_from,
            date_to=request.date_to,
            session_id=request.session_id,
        )
        session_id = row.id
        self.repo.update(session_id, status=SessionStatus.RUNNING)

        usage = UsageRecord(session_id=session_id, plan=request.plan)
        stages = self._stages(self.repo, session_id)

        try:
            await self._execute(request, session_id, usage, stages)
        except TinyFishConfigError as exc:
            await self._fail(session_id, usage, str(exc), kind="tinyfish_unconfigured")
        except GeminiConfigError as exc:
            await self._fail(session_id, usage, str(exc), kind="gemini_unconfigured")
        except TinyFishError as exc:
            await self._fail(session_id, usage, str(exc), kind="tinyfish_error")
        except GeminiError as exc:
            await self._fail(session_id, usage, str(exc), kind="gemini_error")
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("research workflow failed")
            await self._fail(session_id, usage, f"Unexpected error: {exc}", kind="internal_error")

        return session_id

    async def _execute(
        self,
        request: ResearchRequest,
        session_id: str,
        usage: UsageRecord,
        stages: list[PipelineStage],
    ) -> None:
        settings = self.settings

        # --- stage: prepare ---------------------------------------------
        self._mark(session_id, "prepare", StageStatus.RUNNING)
        query = build_search_query(
            request.question,
            request.jurisdiction,
            request.topic,
            request.source_preference == "official_first",
        )
        self._mark(session_id, "prepare", StageStatus.COMPLETED, detail=f'query: "{query[:120]}"')

        # --- stage: tinyfish_search -------------------------------------
        self._mark(session_id, "tinyfish_search", StageStatus.RUNNING)
        async with TinyFishClient() as tf:
            if not tf.configured:
                raise TinyFishConfigError(
                    "TINYFISH_API_KEY is not configured — live search cannot run. "
                    "Add the key to backend/.env (see .env.example). This app never "
                    "substitutes simulated results."
                )

            filters: dict[str, object] = {}
            if request.date_from:
                filters["after_date"] = request.date_from
            if request.date_to:
                filters["before_date"] = request.date_to
            if request.source_preference == "official_first":
                filters["include_domains"] = ",".join(
                    [
                        "gov.in",
                        "nic.in",
                        "indiacode.nic.in",
                        "legislative.gov.in",
                        "sci.gov.in",
                        "ecourts.gov.in",
                    ]
                )

            results: list[NormalizedSearchResult] = await tf.search_legal_sources(
                query=query,
                jurisdiction=request.jurisdiction,
                filters=filters or None,
            )
            usage.search_requests = 1

            search_step = SearchStep(
                query=query,
                jurisdiction=request.jurisdiction,
                result_count=len(results),
                executed_at=datetime.now(timezone.utc),
            )
            self.repo.update(
                session_id,
                stages=self._stages(self.repo, session_id),
                search_step=search_step.model_dump(mode="json"),
                usage=usage,
            )
            self._mark(
                session_id, "tinyfish_search", StageStatus.COMPLETED,
                detail=f"{len(results)} live results",
            )

            # --- stage: select -----------------------------------------
            self._mark(session_id, "select", StageStatus.RUNNING)
            ranked = rank_for_fetch(
                results, request.max_fetch_sources,
                prefer_official=request.source_preference == "official_first",
            )
            self._mark(
                session_id, "select", StageStatus.COMPLETED,
                detail=f"selected {len(ranked)} of {len(results)}",
            )

            # Build Source objects for every search hit (fetched or not)
            sources: list[Source] = []
            for i, r in enumerate(results, start=1):
                sources.append(
                    Source(
                        id=f"source_{i}",
                        title=r.title,
                        url=r.url,
                        source_type=r.source_type,
                        authority_label=(
                            "official/authoritative domain"
                            if r.authority_score >= 0.7 else
                            ("secondary" if r.authority_score >= 0.3 else "unclassified")
                        ),
                        snippet=r.snippet,
                        provider_metadata=r.provider_metadata,
                        rank=r.rank,
                        fetch_status=FetchStatus.PENDING,
                    )
                )
            url_to_id = {s.url: s.id for s in sources}
            selected_ids = [url_to_id[r.url] for r in ranked if r.url in url_to_id]

            # --- stage: tinyfish_fetch ---------------------------------
            self._mark(session_id, "tinyfish_fetch", StageStatus.RUNNING, detail=f"fetching {len(ranked)} sources")
            fetch_results: list[NormalizedFetchResult] = await tf.fetch_multiple_sources(
                [r.url for r in ranked]
            )
            usage.fetch_requests = len(fetch_results)

            ok = 0
            failed = 0
            skipped = 0
            fetched_at = datetime.now(timezone.utc)
            by_url = {fr.url: fr for fr in fetch_results}
            keywords = _TOPIC_TERMS.get(request.topic, []) + [
                w for w in re.findall(r"[A-Za-z]{5,}", request.question.lower())
            ][:6]

            for s in sources:
                fr = by_url.get(s.url)
                if fr is None:
                    s.fetch_status = FetchStatus.SKIPPED if s.id not in selected_ids else FetchStatus.PENDING
                    if s.fetch_status == FetchStatus.SKIPPED:
                        skipped += 1
                    continue
                s.fetch_status = fr.status
                s.fetch_error = fr.error
                if fr.status == FetchStatus.SUCCESS:
                    ok += 1
                    s.content_markdown = fr.content_markdown
                    s.content_chars = len(fr.content_markdown or "")
                    s.retrieved_at = fr.fetched_at or fetched_at
                    s.excerpts = extract_relevant_excerpts(
                        s.content_markdown or "", keywords
                    )
                    for ex in s.excerpts:
                        ex.url = s.url
                    # Preserve provider title if we had only the URL
                    if fr.title and (not s.title or s.title == s.url):
                        s.title = fr.title
                    if fr.provider_metadata:
                        s.provider_metadata = {**s.provider_metadata, **fr.provider_metadata}
                else:
                    failed += 1

            usage.fetched_successfully = ok
            fetch_step = FetchStep(
                requested_urls=[r.url for r in ranked],
                succeeded=ok,
                failed=failed,
                skipped=skipped,
                executed_at=fetched_at,
            )
            self.repo.update(
                session_id,
                fetch_step=fetch_step.model_dump(mode="json"),
                usage=usage,
            )
            self.repo.replace_sources(session_id, sources)

            fetched_count = sum(1 for s in sources if s.fetch_status == FetchStatus.SUCCESS)
            self._mark(
                session_id, "tinyfish_fetch",
                StageStatus.COMPLETED if fetched_count else StageStatus.FAILED,
                detail=f"{fetched_count} fetched, {failed} failed, {skipped} not selected",
            )
            if fetched_count == 0:
                raise TinyFishError(
                    "All source fetches failed — no evidence available for analysis. "
                    f"Providers reported: " + "; ".join(
                        filter(None, [s.fetch_error for s in sources if s.fetch_error])
                    )[:400]
                )

        # --- stage: gemini -----------------------------------------------
        self._mark(session_id, "gemini", StageStatus.RUNNING)
        analysis = await analyze_sources_async(
            request.question, request.jurisdiction, sources
        )
        usage.analyzed_sources = sum(
            1 for s in sources if s.id in _all_source_ids(analysis)
        )
        # Rough cost estimate (transparent, documented assumptions)
        usage.estimated_cost_usd = round(0.0002 * (usage.analyzed_sources or 1) + 0.001, 5)
        self.repo.update(session_id, analysis=analysis, usage=usage)
        self._mark(
            session_id, "gemini", StageStatus.COMPLETED,
            detail=f"analyzed {usage.analyzed_sources} sources",
        )

        # --- stage: graph ------------------------------------------------
        self._mark(session_id, "graph", StageStatus.RUNNING)
        graph = build_graph(analysis)
        self.repo.update(session_id, graph=graph, usage=usage)
        self._mark(
            session_id, "graph", StageStatus.COMPLETED,
            detail=f"{len(graph.get('nodes', []))} nodes / {len(graph.get('edges', []))} edges",
        )

        status = SessionStatus.COMPLETED if fetched_count >= 1 else SessionStatus.PARTIAL
        if failed:
            status = SessionStatus.PARTIAL
        self._mark(session_id, "done", StageStatus.COMPLETED, detail="research complete")
        self.repo.update(session_id, status=status, usage=usage)
        self.repo.record_usage(usage)

    async def _fail(
        self, session_id: str, usage: UsageRecord, message: str, kind: str
    ) -> None:
        """Mark the current running stage failed and session status honestly."""
        stages = self._stages(self.repo, session_id)
        for st in stages:
            if st.status == StageStatus.RUNNING:
                st.status = StageStatus.FAILED
                st.detail = message[:300]
                st.finished_at = datetime.now(timezone.utc)
        # Any not-yet-started stage after a failure stays pending (never claimed complete)
        status = SessionStatus.FAILED
        # If we got sources but analysis failed, mark partial
        try:
            row = self.repo.get(session_id)
            if row is not None:
                sources = self.repo.get_sources(session_id)
                has_fetch = any(s.fetch_status == FetchStatus.SUCCESS for s in sources)
                if has_fetch and kind in ("gemini_error", "gemini_unconfigured"):
                    status = SessionStatus.PARTIAL
        except Exception:
            pass
        self.repo.update(
            session_id, status=status, error=f"{kind}: {message}", stages=stages, usage=usage
        )
        try:
            self.repo.record_usage(usage)
        except Exception:
            logger.exception("failed to record usage for %s", session_id)


def _all_source_ids(analysis) -> set[str]:
    ids: set[str] = set()
    for e in analysis.entities:
        ids.update(e.source_ids)
    for t in analysis.summary.key_takeaways:
        ids.update(t.source_ids)
    for p in analysis.provisions:
        ids.update(p.source_ids)
    for r in analysis.relationships:
        if r.source_id:
            ids.add(r.source_id)
    for n in analysis.next_steps:
        ids.update(n.source_ids)
    return ids