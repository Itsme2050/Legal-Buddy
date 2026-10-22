"""Opt-in live integration tests.

Run with real credentials:

    TINYFISH_API_KEY=... GEMINI_API_KEY=... python -m pytest -m integration

Without credentials the tests skip explicitly (and say so).
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


def _tinyfish_key() -> str | None:
    from app.core.config import get_settings

    return os.environ.get("TINYFISH_API_KEY") or get_settings().tinyfish_api_key


def _gemini_key() -> str | None:
    from app.core.config import get_settings

    return os.environ.get("GEMINI_API_KEY") or get_settings().gemini_api_key


@pytest.mark.asyncio
async def test_live_tinyfish_search():
    key = _tinyfish_key()
    if not key:
        pytest.skip("TINYFISH_API_KEY not set — skipping live Search integration test")
    from app.services.tinyfish_client import TinyFishClient

    async with TinyFishClient() as tf:
        results = await tf.search_legal_sources(
            "tenant eviction protection India", jurisdiction="India"
        )
    assert results, "live search returned no results"
    assert all(r.url.startswith(("http://", "https://")) for r in results)
    assert any(r.title for r in results)


@pytest.mark.asyncio
async def test_live_tinyfish_fetch_of_official_source():
    if not _tinyfish_key():
        pytest.skip("TINYFISH_API_KEY not set — skipping live Fetch integration test")
    from app.schemas import FetchStatus
    from app.services.tinyfish_client import TinyFishClient

    async with TinyFishClient() as tf:
        r = await tf.fetch_source("https://www.sci.gov.in/")
    # Success OR honest failure both acceptable — fabrication is not.
    assert r.status in (FetchStatus.SUCCESS, FetchStatus.FAILED)
    if r.status == FetchStatus.SUCCESS:
        assert r.content_markdown and len(r.content_markdown) > 0
    else:
        assert r.error, "failed fetch must explain why"


def test_live_gemini_analysis():
    if not _gemini_key():
        pytest.skip("GEMINI_API_KEY not set — skipping live Gemini integration test")
    from app.schemas import FetchStatus, Source, SourceType
    from app.services.gemini_client import analyze_sources

    source = Source(
        id="source_1",
        title="Sample tenancy provision",
        url="https://example.test/act",
        source_type=SourceType.LEGISLATION,
        fetch_status=FetchStatus.SUCCESS,
        content_markdown=(
            "Section 14: No landlord shall evict a tenant except in accordance "
            "with the provisions of this Act and subject to notice as prescribed."
        ),
    )
    from app.services.gemini_client import GeminiProviderError
    try:
        result = analyze_sources(
            question="Can a tenant be evicted without notice in India?",
            jurisdiction="India",
            sources=[source],
        )
    except GeminiProviderError as exc:
        if any(w in str(exc) for w in ("503", "UNAVAILABLE", "429", "high demand", "timed out")):
            pytest.skip(f"Gemini API upstream temporarily unavailable: {exc}")
        raise
    assert result.summary.plain_language
    assert result.entities, "analysis produced no entities"
    valid_ids = {"source_1"}
    for ent in result.entities:
        assert set(ent.source_ids) <= valid_ids