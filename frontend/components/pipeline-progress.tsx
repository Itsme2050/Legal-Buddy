"use client";

import { cn } from "@/lib/utils";
import type { PipelineStage } from "@/types/research";
import {
  CheckCircle2,
  CircleDashed,
  Loader2,
  MinusCircle,
  XCircle,
} from "lucide-react";

const icon: Record<PipelineStage["status"], React.ReactNode> = {
  pending: <CircleDashed className="h-4 w-4 text-navy-300" aria-hidden />,
  running: <Loader2 className="h-4 w-4 animate-spin text-teal-600" aria-hidden />,
  completed: <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden />,
  failed: <XCircle className="h-4 w-4 text-rose-600" aria-hidden />,
  skipped: <MinusCircle className="h-4 w-4 text-navy-400" aria-hidden />,
};

export function PipelineProgress({
  stages,
  title = "Research pipeline",
}: {
  stages: PipelineStage[];
  title?: string;
}) {
  if (!stages?.length) return null;
  const done = stages.filter((s) => s.status === "completed").length;
  const pct = Math.round((done / stages.length) * 100);

  return (
    <section
      aria-label={title}
      className="rounded-xl border border-navy-100 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-navy-900">{title}</h3>
        <span className="text-xs text-navy-500" data-testid="pipeline-count">
          {done}/{stages.length} steps
        </span>
      </div>
      <div
        className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-navy-100"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-teal-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <ol className="space-y-2.5">
        {stages.map((s) => (
          <li key={s.key} className="flex items-start gap-2.5 text-sm">
            <span className="mt-0.5 shrink-0">{icon[s.status]}</span>
            <span className="min-w-0 flex-1">
              <span
                className={cn(
                  "block leading-tight",
                  s.status === "completed"
                    ? "text-navy-800"
                    : s.status === "running"
                      ? "font-medium text-teal-700"
                      : s.status === "failed"
                        ? "text-rose-700"
                        : "text-navy-400"
                )}
              >
                {s.label}
              </span>
              {s.detail && (
                <span className="block break-words text-xs text-navy-400">
                  {s.detail}
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}