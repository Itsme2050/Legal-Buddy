"use client";

import { ExternalLink } from "lucide-react";
import type { GraphNodePayload, Source } from "@/types/research";
import { ENTITY_STYLES } from "@/components/graph/entity-node";
import { cn } from "@/lib/utils";

export function NodeDetails({
  node,
  sources,
}: {
  node: GraphNodePayload | null;
  sources: Source[];
}) {
  if (!node) return null;
  const style = ENTITY_STYLES[node.entityType] ?? ENTITY_STYLES.LEGAL_CONCEPT;
  const supporting = sources.filter((s) => node.source_ids.includes(s.id));

  return (
    <div
      data-testid="node-details"
      className="rounded-xl border border-navy-100 bg-white p-4 shadow-sm"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className={cn("h-2 w-2 rounded-full", style.dot)} />
          <span className="text-[10px] uppercase tracking-wide text-navy-400">
            {style.label}
          </span>
        </div>
        {typeof node.confidence === "number" && (
          <span className="text-[10px] text-navy-400">
            {Math.round(node.confidence * 100)}% linked evidence
          </span>
        )}
      </div>
      <h3 className="break-words text-sm font-semibold text-navy-900">{node.label}</h3>
      {node.description && (
        <p className="mt-1.5 text-xs leading-relaxed text-navy-600">{node.description}</p>
      )}

      <h4 className="mt-3 text-xs font-medium text-navy-700">
        Supporting source{supporting.length === 1 ? "" : "s"}
      </h4>
      {supporting.length === 0 ? (
        <p className="mt-1 text-xs text-amber-700" data-testid="node-source-missing">
          No retrieved source linked — could not verify.
        </p>
      ) : (
        <ul className="mt-1.5 space-y-1.5">
          {supporting.map((s) => (
            <li key={s.id}>
              <a
                href={s.url}
                target="_blank"
                rel="noreferrer noopener"
                className="flex items-start gap-1 text-xs text-teal-700 underline-offset-2 hover:underline"
                data-testid="node-source-link"
              >
                <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
                <span className="break-words">{s.title}</span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}