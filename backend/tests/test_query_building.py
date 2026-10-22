"""Unit tests for deterministic search-query construction."""

from __future__ import annotations

from app.services.research_workflow import build_search_query


def test_appends_missing_jurisdiction():
    q = build_search_query("What protects tenants from eviction?", "India", "general", False)
    assert "India" in q
    # trailing question mark is stripped for a cleaner query
    assert q.startswith("What protects tenants from eviction")


def test_does_not_duplicate_jurisdiction_already_in_question():
    q = build_search_query(
        "What protections apply when a tenant faces eviction in India?",
        "India",
        "tenancy",
        False,
    )
    # "India" appears exactly once (from the question itself)
    assert q.count("India") == 1


def test_does_not_duplicate_topic_terms_already_in_question():
    q = build_search_query(
        "Rules about eviction of tenant by landlord",
        "Delhi",
        "tenancy",
        False,
    )
    # topic terms 'eviction'/'tenant'/'landlord' already present -> not re-appended
    assert q.count("eviction") == 1
    assert q.count("tenant") == 1
    assert q.count("landlord") == 1
    assert "Delhi" in q


def test_adds_missing_topic_terms():
    q = build_search_query("What are my rights?", "India", "tenancy", False)
    # tenancy terms absent from the question get appended
    assert "tenant" in q or "landlord" in q


def test_official_preference_adds_domain_hint():
    q = build_search_query("Some question here", "India", "general", True)
    assert "site:gov.in" in q
    q_broad = build_search_query("Some question here", "India", "general", False)
    assert "site:" not in q_broad


def test_global_jurisdiction_not_appended():
    q = build_search_query("Consumer complaint process", "Global", "general", False)
    assert "Global" not in q