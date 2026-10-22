"""SQLAlchemy ORM models for Legal Buddy persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ResearchSessionRow(Base):
    __tablename__ = "research_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(120), default="India")
    topic: Mapped[str] = mapped_column(String(80), default="general")
    source_preference: Mapped[str] = mapped_column(String(32), default="official_first")
    date_from: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    date_to: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    disclaimer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stages: Mapped[list] = mapped_column(JSON, default=list)
    search_step: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    fetch_step: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    graph: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    usage: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    sources: Mapped[list["SourceRow"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(String(32))  # e.g. "source_1"
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(32), default="unknown")
    authority_label: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    court_or_authority: Mapped[Optional[str]] = mapped_column(String(240), nullable=True)
    decision_date: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetch_status: Mapped[str] = mapped_column(String(24), default="pending")
    fetch_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_chars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    excerpts: Mapped[list] = mapped_column(JSON, default=list)
    provider_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    session: Mapped[ResearchSessionRow] = relationship(back_populates="sources")


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    text_chars: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    preview_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    graph: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UsageRow(Base):
    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    plan: Mapped[str] = mapped_column(String(24), default="free")
    search_requests: Mapped[int] = mapped_column(Integer, default=0)
    fetch_requests: Mapped[int] = mapped_column(Integer, default=0)
    fetched_successfully: Mapped[int] = mapped_column(Integer, default=0)
    analyzed_sources: Mapped[int] = mapped_column(Integer, default=0)
    gemini_prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gemini_completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)