"""Pydantic schemas shared across the Legal Buddy backend."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EntityType(str, Enum):
    CASE = "CASE"
    COURT = "COURT"
    LAW = "LAW"
    PROVISION = "PROVISION"
    PERSON = "PERSON"
    PARTY = "PARTY"
    AUTHORITY = "AUTHORITY"
    LOCATION = "LOCATION"
    LEGAL_CONCEPT = "LEGAL_CONCEPT"
    DATE = "DATE"


class RelationshipType(str, Enum):
    CITES = "CITES"
    INTERPRETS = "INTERPRETS"
    APPLIES = "APPLIES"
    OVERRULES = "OVERRULES"
    DISTINGUISHES = "DISTINGUISHES"
    FILED_BY = "FILED_BY"
    DECIDED_BY = "DECIDED_BY"
    INVOLVES = "INVOLVES"
    ISSUED_BY = "ISSUED_BY"
    GOVERNED_BY = "GOVERNED_BY"
    RELATED_TO = "RELATED_TO"
    GOVERNS = "GOVERNS"


class SourceType(str, Enum):
    OFFICIAL = "official"
    COURT = "court"
    LEGISLATION = "legislation"
    NEWS = "news"
    ACADEMIC = "academic"
    UNKNOWN = "unknown"


class FetchStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Confidence(str, Enum):
    DIRECT = "direct"
    SUPPORTED = "supported"
    UNCERTAIN = "uncertain"


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

class PipelineStage(BaseModel):
    key: str = Field(..., description="machine key, e.g. 'tinyfish_search'")
    label: str = Field(..., description="human label shown to user")
    status: StageStatus = StageStatus.PENDING
    detail: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class SearchStep(BaseModel):
    query: str
    jurisdiction: Optional[str] = None
    result_count: int = 0
    executed_at: Optional[datetime] = None


class FetchStep(BaseModel):
    requested_urls: list[str] = Field(default_factory=list)
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    executed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

class SourceExcerpt(BaseModel):
    text: str
    url: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    note: Optional[str] = None


class Source(BaseModel):
    id: str = Field(..., description="e.g. 'source_1'")
    title: str
    url: str
    source_type: SourceType = SourceType.UNKNOWN
    authority_label: Optional[str] = None
    court_or_authority: Optional[str] = None
    decision_date: Optional[str] = None
    snippet: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    fetch_status: FetchStatus = FetchStatus.PENDING
    fetch_error: Optional[str] = None
    content_markdown: Optional[str] = None
    content_chars: Optional[int] = None
    excerpts: list[SourceExcerpt] = Field(default_factory=list)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    rank: Optional[int] = None


# ---------------------------------------------------------------------------
# Entities & relationships
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    id: str
    name: str
    type: EntityType
    description: Optional[str] = None
    source_ids: list[str] = Field(default_factory=list)


class Relationship(BaseModel):
    id: str
    source_entity_id: str
    target_entity_id: str
    type: RelationshipType
    source_id: str = Field(..., description="supporting source id")
    evidence_excerpt: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    confidence_label: Confidence = Confidence.UNCERTAIN
    explanation: Optional[str] = None

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    @field_validator("source_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_id must be non-empty")
        return v.strip()


# ---------------------------------------------------------------------------
# Analysis result (Gemini output, validated)
# ---------------------------------------------------------------------------

class Takeaway(BaseModel):
    text: str
    source_ids: list[str] = Field(default_factory=list)


class Summary(BaseModel):
    plain_language: str
    key_takeaways: list[Takeaway] = Field(default_factory=list)


class Provision(BaseModel):
    citation: str
    description: Optional[str] = None
    source_ids: list[str] = Field(default_factory=list)


class LimitationItem(BaseModel):
    text: str
    kind: Literal["uncertainty", "missing_evidence", "jurisdiction", "date"] = "uncertainty"


class NextStep(BaseModel):
    text: str
    portal_name: Optional[str] = None
    portal_url: Optional[str] = None
    source_ids: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    summary: Summary
    key_concepts: list[str] = Field(default_factory=list)
    provisions: list[Provision] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    conditions_and_exceptions: list[str] = Field(default_factory=list)
    jurisdiction_and_dates: list[str] = Field(default_factory=list)
    limitations: list[LimitationItem] = Field(default_factory=list)
    next_steps: list[NextStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

class UsageRecord(BaseModel):
    session_id: str
    search_requests: int = 0
    fetch_requests: int = 0
    fetched_successfully: int = 0
    analyzed_sources: int = 0
    gemini_prompt_tokens: Optional[int] = None
    gemini_completion_tokens: Optional[int] = None
    plan: Literal["free", "professional"] = "free"
    estimated_cost_usd: Optional[float] = None


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    question: str = Field(..., min_length=8, max_length=2000)
    jurisdiction: str = Field(default="India", max_length=120)
    topic: str = Field(default="general", max_length=80)
    source_preference: Literal["official_first", "broad"] = "official_first"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    max_search_results: int = Field(default=8, ge=1, le=20)
    max_fetch_sources: int = Field(default=5, ge=1, le=10)
    plan: Literal["free", "professional"] = "free"

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 8:
            raise ValueError("question too short")
        return v

    @field_validator("date_from", "date_to")
    @classmethod
    def _check_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        datetime.strptime(v, "%Y-%m-%d")  # raises ValueError on bad input
        return v


class ResearchResult(BaseModel):
    session_id: str
    status: SessionStatus
    question: str
    jurisdiction: str
    topic: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    stages: list[PipelineStage] = Field(default_factory=list)
    search_step: Optional[SearchStep] = None
    fetch_step: Optional[FetchStep] = None
    sources: list[Source] = Field(default_factory=list)
    analysis: Optional[AnalysisResult] = None
    graph: Optional[dict[str, Any]] = None
    usage: Optional[UsageRecord] = None
    error: Optional[str] = None
    disclaimer: Optional[str] = None


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentAnalyzeResponse(BaseModel):
    document_id: str
    filename: str
    size_bytes: int
    text_chars: int
    status: FetchStatus
    preview_markdown: str
    fetch_status_note: str = "user_uploaded"
    analysis: Optional[AnalysisResult] = None
    graph: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    disclaimer: Optional[str] = None


# ---------------------------------------------------------------------------
# Health / integration status
# ---------------------------------------------------------------------------

class IntegrationStatus(BaseModel):
    provider: str
    configured: bool
    endpoint: Optional[str] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    version: str = "0.1.0"
    environment: str
    integrations: list[IntegrationStatus] = Field(default_factory=list)
    database: str
    server_time: datetime


# ---------------------------------------------------------------------------
# Graph payload (returned per-session)
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    entityType: EntityType
    description: Optional[str] = None
    source_ids: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relationshipType: RelationshipType
    source_id: str
    evidence_excerpt: Optional[str] = None
    explanation: Optional[str] = None
    confidence: float
    confidence_label: Confidence


class GraphPayload(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Session history
# ---------------------------------------------------------------------------

class HistoryItem(BaseModel):
    session_id: str
    question: str
    jurisdiction: str
    topic: str
    status: SessionStatus
    created_at: datetime
    source_count: int = 0
    fetched_count: int = 0
    entity_count: int = 0
    summary_preview: Optional[str] = None


class HistoryResponse(BaseModel):
    items: list[HistoryItem] = Field(default_factory=list)
    total: int = 0