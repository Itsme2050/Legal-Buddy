import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SourcesPanel } from "@/components/sources-panel";
import type { Source } from "@/types/research";

const sources: Source[] = [
  {
    id: "source_1",
    title: "Supreme Court judgment",
    url: "https://sci.gov.in/judgments/x",
    source_type: "court",
    fetch_status: "success",
    retrieved_at: "2026-10-01T10:00:00Z",
    excerpts: [{ text: "Section 14 protects tenants.", url: "https://sci.gov.in/judgments/x" }],
    provider_metadata: {},
    content_markdown: "# Full ruling text",
    content_chars: 17,
    rank: 1,
  },
  {
    id: "source_2",
    title: "Blocked government page",
    url: "https://example.gov.in/blocked",
    source_type: "official",
    fetch_status: "failed",
    fetch_error: "HTTP 403 forbidden",
    excerpts: [],
    provider_metadata: {},
  },
];

describe("SourcesPanel", () => {
  it("renders fetched and failed sources with honest status", () => {
    render(<SourcesPanel sources={sources} />);
    expect(screen.getByTestId("sources-count")).toHaveTextContent("1/2 fetched");
    expect(screen.getAllByTestId("source-item")).toHaveLength(2);
    expect(screen.getByTestId("fetch-error")).toHaveTextContent("HTTP 403");
  });

  it("reveals the fetched excerpt when expanded", async () => {
    render(<SourcesPanel sources={sources} />);
    await userEvent.click(screen.getByRole("button", { name: /fetched excerpt/i }));
    expect(await screen.findByTestId("source-excerpt")).toHaveTextContent("Section 14");
  });

  it("shows empty state without sources", () => {
    render(<SourcesPanel sources={[]} />);
    expect(screen.getByText(/no sources were retrieved/i)).toBeInTheDocument();
  });
});