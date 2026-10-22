"""Deterministic graph construction from an ``AnalysisResult``.

Produces React Flow-shaped ``{nodes, edges}`` with stable ids, entity-type
styling metadata and edge confidence labels. No AI involved — pure function.
"""

from __future__ import annotations

from typing import Any

from app.schemas import AnalysisResult, Entity, GraphEdge, GraphPayload, GraphNode, Relationship


def _entity_confidence(entity: Entity, rel_map: dict[str, list[Relationship]]) -> float:
    rels = rel_map.get(entity.id, [])
    if not rels:
        return 0.4  # entity asserted with excerpt but no relationships
    return max(r.confidence for r in rels)


def build_graph(analysis: AnalysisResult) -> dict[str, Any]:
    rel_map: dict[str, list[Relationship]] = {}
    for r in analysis.relationships:
        rel_map.setdefault(r.source_entity_id, []).append(r)
        rel_map.setdefault(r.target_entity_id, []).append(r)

    nodes: list[GraphNode] = []
    for e in analysis.entities:
        nodes.append(
            GraphNode(
                id=e.id,
                type="entity",
                label=e.name,
                entityType=e.type,
                description=e.description,
                source_ids=e.source_ids,
                confidence=round(_entity_confidence(e, rel_map), 3),
            )
        )

    node_ids = {n.id for n in nodes}
    edges: list[GraphEdge] = []
    for r in analysis.relationships:
        if r.source_entity_id not in node_ids or r.target_entity_id not in node_ids:
            continue
        edges.append(
            GraphEdge(
                id=r.id,
                source=r.source_entity_id,
                target=r.target_entity_id,
                label=r.type.value,
                relationshipType=r.type,
                source_id=r.source_id,
                evidence_excerpt=r.evidence_excerpt,
                explanation=r.explanation,
                confidence=r.confidence,
                confidence_label=r.confidence_label,
            )
        )

    payload = GraphPayload(nodes=nodes, edges=edges)
    return payload.model_dump(mode="json")


def graph_stats(graph: dict[str, Any]) -> dict[str, int]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    by_type: dict[str, int] = {}
    for n in nodes:
        t = n.get("entityType", "UNKNOWN")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "entity_types": len(by_type),  # type: ignore[dict-item]
        **{f"type_{k}": v for k, v in by_type.items()},  # type: ignore[misc]
    }