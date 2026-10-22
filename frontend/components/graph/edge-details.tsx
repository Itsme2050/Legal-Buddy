"use client";

import { ExternalLink, Quote } from "lucide-react";
import type { GraphEdgePayload, Source } from "@/types/research";
import { cn } from "@/lib/utils";

const labelStyles: Record<GraphEdgePayload["confidence_label"], string> = {
  direct: "border-emerald-200 bg-emerald-50 text-emerald-700",
  supported: "border-sky-200 bg-sky-50 text-sky-700",
  uncertain: "border-amber-200 bg-amber-50 text-amber-700",
};

export function EdgeDetails({
  edge,
  sources,
}: {
  edge: GraphEdgePayload | null;
  sources: Source[];
}) {
  if (!edge) return null;
  const source = sources.find((s) => s.id === edge.source_id);

  return (
    <div
      data-testid="edge-details"
      className="rounded-xl border border-navy-100 bg-white p-4 shadow-sm"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-navy-900">Relationship</h3>
        <span
          className={cn(
            "rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
            labelStyles[edge.confidence_label]
          )}
        >
          {edge.confidence_label} evidence · {Math.round(edge.confidence * 100)}%
        </span>
      </div>
      <p className="text-xs text-navy-500">
        {edge.source} <span className="font-semibold text-teal-700">—{edge.label}→</span>{" "}
        {edge.target}
      </p>

      {edge.evidence_excerpt && (
        <blockquote className="mt-3 flex gap-2 rounded border border-navy-100 bg-navy-50 p-2.5 text-xs text-navy-700">
          <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-600" aria-hidden />
          <span>{edge.evidence_excerpt}</span>
        </blockquote>
      )}

      {edge.explanation && (
        <p className="mt-2 text-xs text-navy-600">{edge.explanation}</p>
      )}

      {source ? (
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-teal-700 underline underline-offset-2"
          data-testid="edge-source-link"
        >
          Source: {source.title}
          <ExternalLink className="h-3 w-3" aria-hidden />
        </a>
      ) : (
        <p className="mt-3 text-xs text-amber-700" data-testid="edge-source-missing">
          Supporting source {edge.source_id} was not retrieved — could not verify.
        </p>
      )}
    </div>
  );
}