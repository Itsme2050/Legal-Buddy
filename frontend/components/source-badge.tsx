import type { Source, SourceType } from "@/types/research";
import { cn, safeHost } from "@/lib/utils";

const styleMap: Record<SourceType, { label: string; cls: string }> = {
  official: { label: "Official gov source", cls: "bg-teal-50 text-teal-700 border-teal-200" },
  court: { label: "Court / tribunal", cls: "bg-navy-50 text-navy-700 border-navy-200" },
  legislation: { label: "Legislation", cls: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  news: { label: "News / secondary", cls: "bg-amber-50 text-amber-700 border-amber-200" },
  academic: { label: "Academic", cls: "bg-sky-50 text-sky-700 border-sky-200" },
  unknown: { label: "Unclassified", cls: "bg-slate-100 text-slate-600 border-slate-200" },
};

const fetchStyle: Record<Source["fetch_status"], { label: string; cls: string }> = {
  success: { label: "Fetched", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  failed: { label: "Fetch failed", cls: "bg-rose-50 text-rose-700 border-rose-200" },
  pending: { label: "Not fetched", cls: "bg-slate-50 text-slate-500 border-slate-200" },
  skipped: { label: "Not selected", cls: "bg-slate-50 text-slate-500 border-slate-200" },
};

export function SourceBadges({ source }: { source: Source }) {
  const t = styleMap[source.source_type] ?? styleMap.unknown;
  const f = fetchStyle[source.fetch_status] ?? fetchStyle.pending;
  return (
    <div className="flex flex-wrap gap-1.5">
      <span
        data-testid="source-type-badge"
        className={cn(
          "rounded border px-1.5 py-0.5 text-[11px] font-medium",
          t.cls
        )}
      >
        {t.label}
      </span>
      <span
        data-testid="source-fetch-badge"
        className={cn(
          "rounded border px-1.5 py-0.5 text-[11px] font-medium",
          f.cls
        )}
      >
        {f.label}
      </span>
      {source.rank != null && (
        <span className="rounded border border-navy-100 bg-navy-50 px-1.5 py-0.5 text-[11px] text-navy-500">
          rank {source.rank}
        </span>
      )}
      <span className="rounded border border-navy-100 bg-white px-1.5 py-0.5 font-mono text-[11px] text-navy-400">
        {safeHost(source.url)}
      </span>
    </div>
  );
}