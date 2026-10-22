"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink, FileText } from "lucide-react";
import type { Source } from "@/types/research";
import { SourceBadges } from "@/components/source-badge";
import { cn, formatDate, truncate } from "@/lib/utils";

export function SourcesPanel({
  sources,
  highlightId,
}: {
  sources: Source[];
  highlightId?: string | null;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  if (!sources.length) {
    return (
      <section className="rounded-xl border border-navy-100 bg-white p-5 text-sm text-navy-500 shadow-sm">
        No sources were retrieved for this session.
      </section>
    );
  }

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const fetched = sources.filter((s) => s.fetch_status === "success").length;

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-navy-900">Sources</h2>
        <span className="text-xs text-navy-500" data-testid="sources-count">
          {fetched}/{sources.length} fetched
        </span>
      </div>
      <ul className="space-y-3">
        {sources.map((s) => {
          const isOpen = expanded.has(s.id);
          const active = highlightId === s.id;
          const firstExcerpt = s.excerpts[0];
          return (
            <li
              key={s.id}
              data-testid="source-item"
              className={cn(
                "rounded-xl border bg-white p-4 shadow-sm transition-shadow",
                active ? "border-teal-300 ring-2 ring-teal-100" : "border-navy-100"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-navy-400">{s.id}</span>
                    {s.rank != null && (
                      <span className="text-[10px] text-navy-300">#{s.rank}</span>
                    )}
                  </div>
                  <h3 className="mt-0.5 break-words text-sm font-semibold text-navy-900">
                    {s.title}
                  </h3>
                  <div className="mt-1.5">
                    <SourceBadges source={s} />
                  </div>
                </div>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="flex shrink-0 items-center gap-1 rounded-md border border-navy-200 px-2 py-1 text-xs text-navy-600 hover:bg-navy-50"
                  title="Open original source"
                >
                  Open <ExternalLink className="h-3 w-3" aria-hidden />
                </a>
              </div>

              {s.court_or_authority && (
                <p className="mt-2 text-xs text-navy-500">
                  Authority: {s.court_or_authority}
                  {s.decision_date ? ` · ${s.decision_date}` : ""}
                </p>
              )}
              {s.snippet && (
                <p className="mt-2 text-sm text-navy-600">{truncate(s.snippet, 260)}</p>
              )}

              {s.fetch_status === "failed" && s.fetch_error && (
                <p
                  data-testid="fetch-error"
                  className="mt-2 rounded border border-rose-200 bg-rose-50 px-2 py-1.5 text-xs text-rose-700"
                >
                  Could not fetch: {s.fetch_error}
                </p>
              )}

              {s.fetch_status === "success" && firstExcerpt && (
                <div className="mt-3">
                  <button
                    onClick={() => toggle(s.id)}
                    className="flex items-center gap-1 text-xs font-medium text-teal-700 hover:text-teal-800"
                    aria-expanded={isOpen}
                  >
                    <FileText className="h-3.5 w-3.5" aria-hidden />
                    {isOpen ? "Hide fetched content" : "View fetched excerpt + content"}
                    {isOpen ? (
                      <ChevronUp className="h-3 w-3" aria-hidden />
                    ) : (
                      <ChevronDown className="h-3 w-3" aria-hidden />
                    )}
                  </button>
                  {isOpen && (
                    <div className="mt-2 space-y-2">
                      <blockquote
                        data-testid="source-excerpt"
                        className="border-l-2 border-teal-400 bg-teal-50/50 px-3 py-2 text-sm text-navy-700"
                      >
                        {firstExcerpt.text}
                      </blockquote>
                      {s.provider_metadata?.fetched_via != null && (
                        <p className="text-[11px] text-navy-400">
                          provider: {String(s.provider_metadata.fetched_via)}
                        </p>
                      )}
                      {s.content_markdown && (
                        <details className="rounded border border-navy-100 bg-navy-50/50 p-2">
                          <summary className="cursor-pointer text-xs font-medium text-navy-600">
                            Full retrieved markdown ({s.content_chars ?? 0} chars)
                          </summary>
                          <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-navy-700">
                            {s.content_markdown.slice(0, 8000)}
                            {(s.content_chars ?? 0) > 8000 ? "\n… (truncated for display)" : ""}
                          </pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              )}

              <p className="mt-2 text-[11px] text-navy-400">
                Retrieved {formatDate(s.retrieved_at)} · original URL preserved
              </p>
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-navy-400">
        Search ranking is guidance for retrieval — it is not a ranking of legal
        authority. Always open the original source before relying on it.
      </p>
    </section>
  );
}