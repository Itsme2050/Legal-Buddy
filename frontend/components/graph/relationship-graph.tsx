"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type {
  EntityType,
  GraphEdgePayload,
  GraphNodePayload,
  GraphPayload,
  Source,
} from "@/types/research";
import {
  ENTITY_STYLES,
  EntityNode,
  type EntityNodeType,
} from "@/components/graph/entity-node";
import { NodeDetails } from "@/components/graph/node-details";
import { EdgeDetails } from "@/components/graph/edge-details";
import { cn, downloadJson } from "@/lib/utils";
import {
  Download,
  RotateCcw,
  Search,
  Share2,
} from "lucide-react";

const nodeTypes = { entity: EntityNode };

interface Props {
  graph: GraphPayload;
  sources: Source[];
  sessionId?: string;
  focusNodeId?: string | null;
  onFocusNodeChange?: (id: string | null) => void;
}

const ENTITY_TYPES: EntityType[] = [
  "CASE",
  "COURT",
  "LAW",
  "PROVISION",
  "PERSON",
  "PARTY",
  "AUTHORITY",
  "LOCATION",
  "LEGAL_CONCEPT",
  "DATE",
];

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function RelationshipGraph({
  graph,
  sources,
  sessionId,
  focusNodeId,
  onFocusNodeChange,
}: Props) {
  const [selectedNode, setSelectedNode] = useState<GraphNodePayload | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdgePayload | null>(null);
  const [enabledTypes, setEnabledTypes] = useState<Set<EntityType>>(
    () => new Set(ENTITY_TYPES)
  );
  const [search, setSearch] = useState("");
  const [showDisconnected, setShowDisconnected] = useState(false);

  // Reset selection when graph changes
  useEffect(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, [graph]);

  const connectedIds = useMemo(() => {
    const current = focusNodeId ?? selectedNode?.id ?? null;
    if (!current) return null;
    const s = new Set<string>([current]);
    for (const e of graph.edges) {
      if (e.source === current) s.add(e.target);
      if (e.target === current) s.add(e.source);
    }
    return s;
  }, [focusNodeId, selectedNode, graph.edges]);

  const searchMatch = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return null;
    return new Set(
      graph.nodes.filter((n) => n.label.toLowerCase().includes(q)).map((n) => n.id)
    );
  }, [search, graph.nodes]);

  const visible = useCallback(
    (n: GraphNodePayload) => {
      if (!enabledTypes.has(n.entityType)) return false;
      if (searchMatch && !searchMatch.has(n.id)) return false;
      return true;
    },
    [enabledTypes, searchMatch]
  );

  const flowNodes: Node[] = useMemo(() => {
    const cols = Math.max(3, Math.ceil(Math.sqrt(graph.nodes.length)));
    return graph.nodes
      .filter(visible)
      .map((n, i) => {
        const dimmed =
          (connectedIds && showDisconnected && !connectedIds.has(n.id)) ||
          (searchMatch && !searchMatch.has(n.id));
        return {
          id: n.id,
          type: "entity",
          position: {
            x: (i % cols) * 260 + 40,
            y: Math.floor(i / cols) * 130 + 40,
          },
          data: {
            label: n.label,
            entityType: n.entityType,
            description: n.description,
            confidence: n.confidence,
            dimmed,
          },
          selected: selectedNode?.id === n.id || focusNodeId === n.id,
        } satisfies Node;
      });
  }, [graph.nodes, visible, connectedIds, searchMatch, selectedNode, focusNodeId]);

  const flowEdges: Edge[] = useMemo(() => {
    const visibleIds = new Set(flowNodes.map((n) => n.id));
    return graph.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e) => {
        const uncertain = e.confidence_label === "uncertain" || e.confidence < 0.5;
        const direct = e.confidence_label === "direct";
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          animated: uncertain,
          selected: selectedEdge?.id === e.id,
          labelStyle: { fill: "#253a68", fontSize: 10, fontWeight: 600 },
          labelBgStyle: { fill: "#ffffff", fillOpacity: 0.9 },
          style: {
            stroke: direct ? "#0f8884" : uncertain ? "#d97706" : "#5f80bd",
            strokeDasharray: uncertain ? "5 4" : undefined,
            strokeWidth: uncertain ? 1.3 : 1.8,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: direct ? "#0f8884" : uncertain ? "#d97706" : "#5f80bd",
          },
        } satisfies Edge;
      });
  }, [graph.edges, flowNodes, selectedEdge]);

  const onNodeClick = useCallback(
    (_: unknown, node: Node) => {
      const payload = graph.nodes.find((n) => n.id === node.id) ?? null;
      setSelectedNode(payload);
      setSelectedEdge(null);
      onFocusNodeChange?.(node.id);
    },
    [graph.nodes, onFocusNodeChange]
  );

  const onEdgeClick = useCallback(
    (_: unknown, edge: Edge) => {
      const payload = graph.edges.find((e) => e.id === edge.id) ?? null;
      setSelectedEdge(payload);
      setSelectedNode(null);
    },
    [graph.edges]
  );

  const reset = useCallback(() => {
    setEnabledTypes(new Set(ENTITY_TYPES));
    setSearch("");
    setSelectedNode(null);
    setSelectedEdge(null);
    setShowDisconnected(false);
    onFocusNodeChange?.(null);
  }, [onFocusNodeChange]);

  const exportJson = useCallback(() => {
    downloadJson(`legal-buddy-graph-${sessionId ?? "export"}.json`, graph);
  }, [graph, sessionId]);

  const exportImage = useCallback(() => {
    if (!isBrowser()) return;
    const el = document.querySelector(".react-flow__renderer") as
      | HTMLCanvasElement
      | null;
    // React Flow renders to canvas — best-effort export
    const canvas = document.querySelector("canvas") as HTMLCanvasElement | null;
    const target = el ?? canvas;
    if (!target) return;
    try {
      const url = (target as HTMLCanvasElement).toDataURL("image/png");
      const a = document.createElement("a");
      a.href = url;
      a.download = `legal-buddy-graph-${sessionId ?? "export"}.png`;
      a.click();
    } catch {
      alert("Graph image export is not supported in this browser — use JSON export.");
    }
  }, [sessionId]);

  if (!graph.nodes.length) {
    return (
      <div className="flex min-h-[320px] flex-col items-center justify-center rounded-xl border border-dashed border-navy-200 bg-white p-8 text-center">
        <Share2 className="mb-2 h-8 w-8 text-navy-300" aria-hidden />
        <p className="text-sm font-medium text-navy-700">No relationships extracted</p>
        <p className="mt-1 max-w-md text-xs text-navy-500">
          The evidence did not support entity/relationship extraction for this
          session. Review the sources panel instead — empty graphs are honest
          results, not failures.
        </p>
      </div>
    );
  }

  const typeCounts = useMemo(() => {
    const counts: Partial<Record<EntityType, number>> = {};
    for (const n of graph.nodes) counts[n.entityType] = (counts[n.entityType] ?? 0) + 1;
    return counts;
  }, [graph.nodes]);

  return (
    <section className="space-y-3" aria-label="Legal relationship graph">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-navy-100 bg-white p-3 shadow-sm">
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-navy-400"
            aria-hidden
          />
          <input
            aria-label="Search nodes by name"
            placeholder="Search nodes…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-44 rounded-md border border-navy-200 py-1.5 pl-7 pr-2 text-xs focus:border-teal-400 focus:outline-none"
            data-testid="graph-search"
          />
        </div>
        <div className="flex flex-wrap gap-1">
          {ENTITY_TYPES.filter((t) => typeCounts[t]).map((t) => {
            const on = enabledTypes.has(t);
            const st = ENTITY_STYLES[t];
            return (
              <button
                key={t}
                onClick={() =>
                  setEnabledTypes((prev) => {
                    const next = new Set(prev);
                    if (next.has(t)) next.delete(t);
                    else next.add(t);
                    return next;
                  })
                }
                aria-pressed={on}
                data-testid={`filter-${t}`}
                className={cn(
                  "flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] transition-opacity",
                  on ? "border-navy-200 bg-white text-navy-700" : "border-navy-100 bg-navy-50 text-navy-400 opacity-60"
                )}
              >
                <span className={cn("h-1.5 w-1.5 rounded-full", st.dot)} />
                {st.label} ({typeCounts[t]})
              </button>
            );
          })}
        </div>
        <div className="ml-auto flex gap-1.5">
          <button
            onClick={() => setShowDisconnected((v) => !v)}
            className={cn(
              "rounded-md border px-2 py-1.5 text-[11px]",
              showDisconnected
                ? "border-teal-300 bg-teal-50 text-teal-700"
                : "border-navy-200 text-navy-600 hover:bg-navy-50"
            )}
            title="Dim unrelated nodes when a node is selected"
            data-testid="toggle-disconnected"
          >
            {showDisconnected ? "Connected only" : "Show all"}
          </button>
          <button
            onClick={reset}
            className="rounded-md border border-navy-200 px-2 py-1.5 text-[11px] text-navy-600 hover:bg-navy-50"
            title="Reset filters, search and selection"
            data-testid="graph-reset"
          >
            <RotateCcw className="inline h-3 w-3" aria-hidden /> Reset
          </button>
          <button
            onClick={exportJson}
            className="rounded-md border border-navy-200 px-2 py-1.5 text-[11px] text-navy-600 hover:bg-navy-50"
            data-testid="graph-export-json"
          >
            <Download className="inline h-3 w-3" aria-hidden /> JSON
          </button>
          <button
            onClick={exportImage}
            className="rounded-md border border-navy-200 px-2 py-1.5 text-[11px] text-navy-600 hover:bg-navy-50"
            data-testid="graph-export-image"
          >
            PNG
          </button>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[1fr_320px]">
        <div
          className="h-[520px] rounded-xl border border-navy-100 bg-white shadow-sm"
          data-testid="graph-canvas"
        >
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            fitView
            minZoom={0.2}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
            nodesDraggable
            nodesConnectable={false}
            elementsSelectable
          >
            <Background gap={18} color="#d9e2f1" />
            <MiniMap
              pannable
              zoomable
              nodeColor={(n) => {
                const t = (n.data as { entityType?: EntityType })?.entityType;
                return t ? ENTITY_STYLES[t]?.dot.replace("bg-", "#") ?? "#8aa4d2" : "#8aa4d2";
              }}
            />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>

        <aside className="min-h-[240px] space-y-3">
          <NodeDetails node={selectedNode} sources={sources} />
          <EdgeDetails edge={selectedEdge} sources={sources} />
          {!selectedNode && !selectedEdge && (
            <div className="rounded-xl border border-dashed border-navy-200 bg-white p-4 text-xs text-navy-500">
              <p className="font-medium text-navy-700">How to explore</p>
              <ul className="mt-1.5 list-disc space-y-1 pl-4">
                <li>Click a node to see its evidence and supporting sources.</li>
                <li>Click an edge to read the supporting excerpt.</li>
                <li>
                  Solid teal = direct evidence · dashed amber = uncertain
                  relationship.
                </li>
                <li>Use filters/search to focus, Reset to restore everything.</li>
              </ul>
            </div>
          )}
        </aside>
      </div>
      <p className="text-xs text-navy-400">
        Every node and edge traces back to a retrieved source. Uncertain
        relationships are marked and never presented as established law.
      </p>
    </section>
  );
}