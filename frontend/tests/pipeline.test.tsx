import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PipelineProgress } from "@/components/pipeline-progress";
import type { PipelineStage } from "@/types/research";

const stages: PipelineStage[] = [
  { key: "prepare", label: "Preparing legal search", status: "completed" },
  { key: "tinyfish_search", label: "Searching live sources with TinyFish", status: "running" },
  { key: "gemini", label: "Analyzing retrieved evidence with Gemini", status: "pending" },
  { key: "graph", label: "Building the legal relationship graph", status: "pending" },
];

describe("PipelineProgress", () => {
  it("renders every stage label", () => {
    render(<PipelineProgress stages={stages} />);
    for (const s of stages) {
      expect(screen.getByText(s.label)).toBeInTheDocument();
    }
  });

  it("shows real completion counts", () => {
    render(<PipelineProgress stages={stages} />);
    expect(screen.getByTestId("pipeline-count")).toHaveTextContent("1/4 steps");
  });

  it("returns null with no stages (no fabricated progress)", () => {
    const { container } = render(<PipelineProgress stages={[]} />);
    expect(container.firstChild).toBeNull();
  });
});