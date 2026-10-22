import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// React Flow relies on layout APIs jsdom doesn't provide — mock it but keep
// our toolbar / details panels real so behavior is actually exercised.
vi.mock("@xyflow/react", () => {
  const ReactFlow = ({ nodes, edges }: { nodes: unknown[]; edges: unknown[] }) => (
    <div data-testid="flow-mock">
      nodes:{nodes.length},edges:{edges.length}
    </div>
  );
  return {
    ReactFlow,
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
    Handle: () => null,
    Position: { Top: "top", Bottom: "bottom", Left: "left", Right: "right" },
    MarkerType: { ArrowClosed: "arrowclosed" },
    memo: (c: unknown) => c,
  };
});

import { RelationshipGraph } from "@/components/graph/relationship-graph";
import type { GraphPayload, Source } from "@/types/research";

const graph: GraphPayload = {
  nodes: [
    { id: "entity_1", type: "entity", label: "Rent Control Act", entityType: "LAW", source_ids: ["source_1"], confidence: 0.9 },
    { id: "entity_2", type: "entity", label: "Section 14", entityType: "PROVISION", source_ids: ["source_1"], confidence: 0.8 },
    { id: "entity_3", type: "entity", label: "High Court", entityType: "COURT", source_ids: ["source_2"], confidence: 0.7 },
  ],
  edges: [
    {
      id: "rel_1",
      source: "entity_1",
      target: "entity_2",
      label: "GOVERNS",
      relationshipType: "GOVERNS",
      source_id: "source_1",
      evidence_excerpt: "The Act governs Section 14.",
      confidence: 0.9,
      confidence_label: "direct",
    },
  ],
};

const sources: Source[] = [
  {
    id: "source_1",
    title: "The Rent Control Act",
    url: "https://indiacode.nic.in/act",
    source_type: "legislation",
    fetch_status: "success",
    excerpts: [],
    provider_metadata: {},
  },
  {
    id: "source_2",
    title: "High Court order",
    url: "https://delhihighcourt.gov.in/order",
    source_type: "court",
    fetch_status: "success",
    excerpts: [],
    provider_metadata: {},
  },
];

describe("RelationshipGraph", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nodes and edges", () => {
    render(<RelationshipGraph graph={graph} sources={sources} />);
    expect(screen.getByTestId("flow-mock")).toHaveTextContent("nodes:3,edges:1");
    expect(screen.getAllByTestId("filter-LAW").length).toBe(1);
  });

  it("filters entity types off", async () => {
    render(<RelationshipGraph graph={graph} sources={sources} />);
    await userEvent.click(screen.getByTestId("filter-COURT"));
    expect(screen.getByTestId("filter-COURT")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("flow-mock")).toHaveTextContent("nodes:2");
  });

  it("search narrows visible nodes", async () => {
    render(<RelationshipGraph graph={graph} sources={sources} />);
    await userEvent.type(screen.getByTestId("graph-search"), "Section");
    expect(screen.getByTestId("flow-mock")).toHaveTextContent("nodes:1");
  });

  it("reset restores everything", async () => {
    render(<RelationshipGraph graph={graph} sources={sources} />);
    await userEvent.click(screen.getByTestId("filter-LAW"));
    await userEvent.type(screen.getByTestId("graph-search"), "zzz");
    expect(screen.getByTestId("flow-mock")).toHaveTextContent("nodes:0");
    await userEvent.click(screen.getByTestId("graph-reset"));
    expect(screen.getByTestId("flow-mock")).toHaveTextContent("nodes:3");
  });

  it("shows an honest empty state when there are no nodes", () => {
    render(<RelationshipGraph graph={{ nodes: [], edges: [] }} sources={sources} />);
    expect(screen.getByText(/no relationships extracted/i)).toBeInTheDocument();
  });
});