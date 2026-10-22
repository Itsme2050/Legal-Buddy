"""Schema validation tests for Gemini analysis output (no credentials needed)."""

from __future__ import annotations

import pytest

from app.schemas import (
    AnalysisResult,
    Confidence,
    EntityType,
    FetchStatus,
    RelationshipType,
    Source,
    SourceType,
)
from app.services.gemini_client import (
    GeminiMalformedOutputError,
    _extract_json,
    _validate_and_pure,
)

VALID_JSON = {
    "summary": {
        "plain_language": "Tenants generally cannot be evicted without notice.",
        "key_takeaways": [
            {"text": "Notice is required.", "source_ids": ["source_1"]},
            {"text": "Bogus claim.", "source_ids": ["source_99"]},
        ],
    },
    "key_concepts": ["natural justice"],
    "provisions": [
        {"citation": "Section 14", "description": "Protection", "source_ids": ["source_1"]},
        {"citation": "Ghost section", "source_ids": ["source_99"]},
    ],
    "entities": [
        {"id": "entity_1", "name": "Rent Act", "type": "LAW", "description": "d", "source_ids": ["source_1"]},
    ],
    "relationships": [
        {
            "id": "relationship_1",
            "source_entity_id": "entity_1",
            "target_entity_id": "entity_1",
            "type": "APPLIES",
            "source_id": "source_1",
            "evidence_excerpt": "The Act applies.",
            "confidence": 0.9,
            "confidence_label": "direct",
        },
        {
            "id": "relationship_ghost",
            "source_entity_id": "entity_1",
            "target_entity_id": "entity_1",
            "type": "CITES",
            "source_id": "source_99",
            "evidence_excerpt": "x",
            "confidence": 0.8,
            "confidence_label": "supported",
        },
    ],
    "conditions_and_exceptions": [],
    "jurisdiction_and_dates": ["India"],
    "limitations": [{"text": "could not verify currency", "kind": "date"}],
    "next_steps": [{"text": "Check state amendment", "source_ids": ["source_1"]}],
}


def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    raw = '```json\n{"a": 1}\n```'
    assert _extract_json(raw) == {"a": 1}


def test_extract_json_with_surrounding_prose():
    raw = 'Sure! Here is the JSON:\n{"a": 1}\nHope that helps.'
    assert _extract_json(raw) == {"a": 1}


def test_extract_json_rejects_garbage():
    with pytest.raises(GeminiMalformedOutputError):
        _extract_json("no json here at all")


def test_unknown_source_ids_cleared():
    import copy

    obj = copy.deepcopy(VALID_JSON)
    result = _validate_and_pure(obj, valid_ids={"source_1"})
    assert all(
        all(sid == "source_1" for sid in t.source_ids)
        for t in result.summary.key_takeaways
    )
    assert all(all(sid == "source_1" for sid in p.source_ids) for p in result.provisions)
    ghost = [r for r in result.relationships if r.id == "relationship_ghost"]
    # ghost relationship dropped because its source_id was emptied
    assert ghost == []


def test_invalid_enum_rejected():
    import copy

    obj = copy.deepcopy(VALID_JSON)
    obj["entities"][0]["type"] = "TOTALLY_INVALID"
    with pytest.raises(GeminiMalformedOutputError):
        _validate_and_pure(obj, valid_ids={"source_1"})


def test_overrules_downgraded_without_explicit_evidence():
    import copy

    obj = copy.deepcopy(VALID_JSON)
    obj["relationships"].append(
        {
            "id": "relationship_over",
            "source_entity_id": "entity_1",
            "target_entity_id": "entity_1",
            "type": "OVERRULES",
            "source_id": "source_1",
            "evidence_excerpt": "mentioned in passing",
            "confidence": 0.95,
            "confidence_label": "direct",
        }
    )
    result = _validate_and_pure(obj, valid_ids={"source_1"})
    over = [r for r in result.relationships if r.id == "relationship_over"]
    assert over and over[0].type == RelationshipType.RELATED_TO
    assert over[0].confidence_label == Confidence.UNCERTAIN


def test_overrules_kept_with_explicit_evidence():
    import copy

    obj = copy.deepcopy(VALID_JSON)
    obj["relationships"].append(
        {
            "id": "relationship_over",
            "source_entity_id": "entity_1",
            "target_entity_id": "entity_1",
            "type": "OVERRULES",
            "source_id": "source_1",
            "evidence_excerpt": "This bench overrules the earlier decision.",
            "confidence": 0.95,
            "confidence_label": "direct",
        }
    )
    result = _validate_and_pure(obj, valid_ids={"source_1"})
    over = [r for r in result.relationships if r.id == "relationship_over"]
    assert over and over[0].type == RelationshipType.OVERRULES


def test_direct_analysis_result_roundtrip():
    result = _validate_and_pure(VALID_JSON, valid_ids={"source_1", "source_99"})
    assert isinstance(result, AnalysisResult)
    dumped = result.model_dump(mode="json")
    again = AnalysisResult.model_validate(dumped)
    assert len(again.entities) == 1


def test_source_fetch_status_enum():
    s = Source(id="source_1", title="t", url="https://x.test", fetch_status=FetchStatus.SUCCESS)
    assert s.source_type == SourceType.UNKNOWN  # default
    assert s.fetch_status == FetchStatus.SUCCESS