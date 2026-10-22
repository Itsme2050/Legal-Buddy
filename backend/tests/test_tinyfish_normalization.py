"""Unit tests for TinyFish response normalization (no credentials required)."""

from __future__ import annotations

import pytest

from app.schemas import FetchStatus, SourceType
from app.services.tinyfish_client import (
    classify_source,
    extract_relevant_excerpts,
    normalize_fetch_result,
    normalize_search_results,
    officialness_score,
    rank_for_fetch,
)


SEARCH_PAYLOAD = {
    "query": "tenant eviction protection India",
    "results": [
        {
            "url": "https://www.sci.gov.in/",
            "title": "Supreme Court of India",
            "snippet": "Judgments and orders.",
            "position": 1,
        },
        {
            "url": "https://indiacode.nic.in/",
            "title": "India Code",
            "description": "Acts and rules",
            "position": 2,
        },
        {
            # duplicate of first (www, trailing slash)
            "url": "https://sci.gov.in/",
            "title": "Duplicate entry",
            "position": 3,
        },
        {
            "url": "https://example-blog.test/post",
            "name": "Blog post",
            "summary": "Opinion piece",
            "custom_field": "kept-in-metadata",
            "position": 4,
        },
        {"title": "no url at all"},
        "not-a-dict",
    ],
}


def test_normalize_search_results_shapes_and_dedup():
    results = normalize_search_results(SEARCH_PAYLOAD, query="q")
    assert len(results) == 3  # dup + invalid entries removed
    urls = [r.url for r in results]
    assert "https://www.sci.gov.in/" in urls
    assert "https://sci.gov.in/" not in urls
    assert results[0].rank == 1


def test_normalize_search_results_accepts_bare_list_and_data_key():
    bare = normalize_search_results(SEARCH_PAYLOAD["results"][:1])
    assert len(bare) == 1
    wrapped = normalize_search_results({"data": [{"url": "https://gov.in/x", "title": "X"}]})
    assert len(wrapped) == 1


def test_normalize_search_results_empty_payload():
    assert normalize_search_results(None) == []
    assert normalize_search_results({"results": []}) == []


def test_normalize_search_results_rejects_non_html_urls():
    results = normalize_search_results([{"url": "javascript:alert(1)", "title": "x"}])
    assert results == []


def test_officialness_score_prefers_gov_domains():
    assert officialness_score("https://www.sci.gov.in/x") > officialness_score(
        "https://random-blog.test/x"
    )
    assert officialness_score("https://indiacode.nic.in/act") >= 0.75


def test_classify_source():
    assert classify_source("SC judgment", "https://www.sci.gov.in/") == SourceType.COURT
    assert classify_source("India Code", "https://indiacode.nic.in/") == SourceType.LEGISLATION
    assert classify_source("Dept note", "https://mh.gov.in/x") == SourceType.OFFICIAL
    assert classify_source("Story", "https://timesofindia.indiatimes.com/x") == SourceType.NEWS
    assert classify_source("Random", "https://random-site.example/x") == SourceType.UNKNOWN
    assert classify_source("Blog", "https://legal-blog.test/x") == SourceType.NEWS  # blogs are secondary/news


def test_rank_for_fetch_orders_by_authority():
    results = normalize_search_results(SEARCH_PAYLOAD)
    ranked = rank_for_fetch(results, limit=2, prefer_official=True)
    assert ranked[0].authority_score >= ranked[1].authority_score


def test_normalize_fetch_result_markdown():
    r = normalize_fetch_result(
        "https://x.test/a",
        {"markdown": "# Title\\n\\nBody text", "title": "Title", "status": "ok"},
    )
    assert r.status == FetchStatus.SUCCESS
    assert r.content_markdown.startswith("# Title")
    assert r.title == "Title"


def test_normalize_fetch_result_empty():
    r = normalize_fetch_result("https://x.test/a", {"content": ""})
    assert r.status == FetchStatus.FAILED
    assert r.error


def test_normalize_fetch_result_plain_string():
    r = normalize_fetch_result("https://x.test/a", "just text")
    assert r.status == FetchStatus.SUCCESS
    assert r.content_markdown == "just text"


def test_extract_excerpts_keyword_and_fallback():
    text = "Section 14 protects tenants. " * 20 + " unrelated content"
    excerpts = extract_relevant_excerpts(text, ["tenants", "section 14"])
    assert excerpts
    assert "tenants" in excerpts[0].text.lower()

    fallback = extract_relevant_excerpts("short text with no hits", ["zzzz"])
    assert fallback and fallback[0].note == "opening-passage"


def test_extract_excerpts_empty_text():
    assert extract_relevant_excerpts("", ["x"]) == []