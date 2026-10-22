"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Download,
  FileDown,
  Loader2,
} from "lucide-react";

import { ApiError, getSession } from "@/lib/api";
import type { GraphPayload, ResearchResult } from "@/types/research";
import { PipelineProgress } from "@/components/pipeline-progress";
import { SummaryPanel } from "@/components/summary-panel";
import { SourcesPanel } from "@/components/sources-panel";
import { NextStepsPanel } from "@/components/next-steps-panel";
import { RelationshipGraph } from "@/components/graph/relationship-graph";
import { cn, downloadJson, formatDate } from "@/lib/utils";

const statusStyle: Record<string, string> = {
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  partial: "bg-amber-50 text-amber-700 border-amber-200",
  failed: "bg-rose-50 text-rose-700 border-rose-200",
  running: "bg-teal-50 text-teal-700 border-teal-200",
  pending: "bg-navy-50 text-navy-500 border-navy-100",
};

type Tab = "summary" | "sources" | "graph" | "next";

export default function ResultsPage({ params }: { params: { sessionId: string } }) {
  const sessionId = params.sessionId;
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("summary");
  const [highlightSource, setHighlightSource] = useState<string | null>(null);
  const [focusNode, setFocusNode] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSession(sessionId);
      setResult(res.result);
      if (res.result.status === "running" || res.result.status === "pending") {
        setTimeout(() => {
          void load();
        }, 2000);
      }
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Could not load this research session."
      );
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  const emptyGraph: GraphPayload = useMemo(() => ({ nodes: [], edges: [] }), []);

  const exportSession = useCallback(() => {
    if (!result) return;
    downloadJson(`legal-buddy-session-${sessionId}.json`, {
      session_id: result.session_id,
      question: result.question,
      jurisdiction: result.jurisdiction,
      status: result.status,
      created_at: result.created_at,
      search_step: result.search_step,
      fetch_step: result.fetch_step,
      sources: result.sources.map((s) => ({
        id: s.id,
        title: s.title,
        url: s.url,
        source_type: s.source_type,
        fetch_status: s.fetch_status,
        retrieved_at: s.retrieved_at,
        excerpts: s.excerpts,
      })),
      analysis: result.analysis,
      graph: result.graph,
      usage: result.usage,
      disclaimer: result.disclaimer,
    });
  }, [result, sessionId]);

  if (loading && !result) {
    return (
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-3 px-4 py-24 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-teal-600" aria-hidden />
        <p className="text-sm text-navy-600">Loading research session…</p>
        <div className="mt-4 w-full max-w-xl space-y-3">
          <div className="skeleton h-8 w-3/4 rounded" />
          <div className="skeleton h-24 rounded-xl" />
          <div className="skeleton h-40 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-rose-500" aria-hidden />
        <h1 className="text-lg font-semibold text-navy-900">Could not load session</h1>
        <p className="mt-2 text-sm text-navy-600">{error}</p>
        <div className="mt-5 flex justify-center gap-3">
          <button
            onClick={() => void load()}
            className="rounded-lg border border-navy-200 px-4 py-2 text-sm hover:bg-navy-50"
          >
            Retry
          </button>
          <Link
            href="/dashboard"
            className="rounded-lg bg-navy-900 px-4 py-2 text-sm text-white hover:bg-navy-800"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!result) return null;

  const analysis = result.analysis;
  const graph: GraphPayload = result.graph ?? emptyGraph;
  const fetched = result.sources.filter((s) => s.fetch_status === "success");

  const tabs: { key: Tab; label: string; badge?: string }[] = [
    {
      key: "summary",
      label: "Summary",
      badge: analysis ? undefined : "unavailable",
    },
    { key: "sources", label: "Sources", badge: `${fetched.length}/${result.sources.length}` },
    { key: "graph", label: "Relationship graph", badge: `${graph.nodes.length} nodes` },
    { key: "next", label: "Next steps" },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Header */}
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link
            href="/dashboard"
            className="mb-2 inline-flex items-center gap-1 text-xs text-navy-500 hover:text-teal-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> New research
          </Link>
          <h1 className="break-words text-xl font-bold text-navy-900">
            {result.question}
          </h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-navy-500">
            <span
              data-testid="session-status"
              className={cn(
                "rounded border px-1.5 py-0.5 uppercase",
                statusStyle[result.status]
              )}
            >
              {result.status}
            </span>
            <span>{result.jurisdiction}</span>
            <span>·</span>
            <span>{formatDate(result.created_at)}</span>
            {result.search_step && (
              <>
                <span>·</span>
                <span data-testid="search-query">
                  query: “{result.search_step.query.slice(0, 80)}”
                </span>
              </>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={exportSession}
            data-testid="export-session"
            className="inline-flex items-center gap-1.5 rounded-lg border border-navy-200 bg-white px-3 py-2 text-xs font-medium text-navy-700 hover:bg-navy-50"
          >
            <FileDown className="h-3.5 w-3.5" aria-hidden /> Export JSON
          </button>
          <button
            onClick={() => {
              if (!graph.nodes.length) return;
              downloadJson(`legal-buddy-graph-${sessionId}.json`, graph);
            }}
            disabled={!graph.nodes.length}
            data-testid="export-graph"
            className="inline-flex items-center gap-1.5 rounded-lg border border-navy-200 bg-white px-3 py-2 text-xs font-medium text-navy-700 hover:bg-navy-50 disabled:opacity-40"
          >
            <Download className="h-3.5 w-3.5" aria-hidden /> Graph JSON
          </button>
        </div>
      </div>

      {result.status !== "completed" && (
        <div
          role="status"
          data-testid="session-warning"
          className={cn(
            "mb-5 rounded-lg border px-4 py-3 text-sm",
            result.status === "failed"
              ? "border-rose-200 bg-rose-50 text-rose-800"
              : result.status === "partial"
                ? "border-amber-200 bg-amber-50 text-amber-900"
                : "border-teal-200 bg-teal-50 text-teal-800"
          )}
        >
          <p className="font-medium">
            {result.status === "failed"
              ? "Research failed"
              : result.status === "partial"
                ? "Partial results — some evidence could not be retrieved or analyzed"
                : "Research in progress…"}
          </p>
          {result.error && <p className="mt-1 text-xs">{result.error}</p>}
          {result.status === "partial" && (
            <p className="mt-1 text-xs">
              Check the Sources tab for per-source fetch failures. Nothing below is
              fabricated to fill the gaps.
            </p>
          )}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        {/* Left: pipeline + usage */}
        <aside className="space-y-4">
          <PipelineProgress stages={result.stages} />
          {result.search_step && (
            <div className="rounded-xl border border-navy-100 bg-white p-4 text-xs shadow-sm">
              <h3 className="mb-1.5 text-sm font-semibold text-navy-800">Activity</h3>
              <dl className="space-y-1 text-navy-600">
                <div className="flex justify-between gap-2">
                  <dt>Search results</dt>
                  <dd className="font-medium">{result.search_step.result_count}</dd>
                </div>
                {result.fetch_step && (
                  <>
                    <div className="flex justify-between gap-2">
                      <dt>Fetched OK</dt>
                      <dd className="font-medium text-emerald-700">
                        {result.fetch_step.succeeded}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt>Fetch failed</dt>
                      <dd className="font-medium text-rose-600">
                        {result.fetch_step.failed}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt>Not selected</dt>
                      <dd>{result.fetch_step.skipped}</dd>
                    </div>
                  </>
                )}
                {result.usage && (
                  <>
                    <div className="flex justify-between gap-2">
                      <dt>Search API calls</dt>
                      <dd>{result.usage.search_requests}</dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt>Fetch API calls</dt>
                      <dd>{result.usage.fetch_requests}</dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt>Est. provider cost</dt>
                      <dd>
                        {result.usage.estimated_cost_usd != null
                          ? `$${result.usage.estimated_cost_usd.toFixed(4)}`
                          : "—"}
                      </dd>
                    </div>
                  </>
                )}
              </dl>
            </div>
          )}
        </aside>

        {/* Right: tabbed workspace */}
        <div>
          <div
            role="tablist"
            aria-label="Research result sections"
            className="mb-4 flex flex-wrap gap-1 border-b border-navy-100"
          >
            {tabs.map((t) => (
              <button
                key={t.key}
                role="tab"
                aria-selected={tab === t.key}
                onClick={() => setTab(t.key)}
                data-testid={`tab-${t.key}`}
                className={cn(
                  "relative -mb-px rounded-t-lg border-b-2 px-3.5 py-2 text-sm",
                  tab === t.key
                    ? "border-teal-500 font-medium text-teal-700"
                    : "border-transparent text-navy-500 hover:text-navy-800"
                )}
              >
                {t.label}
                {t.badge && (
                  <span className="ml-1.5 rounded bg-navy-50 px-1 text-[10px] text-navy-400">
                    {t.badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          {tab === "summary" && (
            <div data-testid="panel-summary" className="animate-fade-in">
              <SummaryPanel result={result} analysis={analysis} />
            </div>
          )}

          {tab === "sources" && (
            <div data-testid="panel-sources" className="animate-fade-in">
              <SourcesPanel
                sources={result.sources}
                highlightId={highlightSource}
              />
            </div>
          )}

          {tab === "graph" && (
            <div data-testid="panel-graph" className="animate-fade-in">
              <RelationshipGraph
                graph={graph}
                sources={result.sources}
                sessionId={sessionId}
                focusNodeId={focusNode}
                onFocusNodeChange={(id) => {
                  setFocusNode(id);
                  // selecting a node also highlights its first source
                  const node = graph.nodes.find((n) => n.id === id);
                  if (node?.source_ids?.[0]) setHighlightSource(node.source_ids[0]);
                }}
              />
            </div>
          )}

          {tab === "next" && (
            <div data-testid="panel-next" className="animate-fade-in">
              <NextStepsPanel analysis={analysis} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}