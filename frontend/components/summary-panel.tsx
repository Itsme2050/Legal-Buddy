"use client";

import { AlertTriangle, Lightbulb, Scale } from "lucide-react";
import type { AnalysisResult, ResearchResult } from "@/types/research";
import { formatDate } from "@/lib/utils";
import { DisclaimerBanner } from "@/components/disclaimer-banner";

export function SummaryPanel({
  result,
  analysis,
}: {
  result: ResearchResult;
  analysis?: AnalysisResult | null;
}) {
  if (!analysis) {
    return (
      <section className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
        <h2 className="mb-2 text-base font-semibold text-navy-900">
          No analysis available
        </h2>
        <p className="text-sm text-navy-500">
          The analysis stage did not complete
          {result.error ? ` — ${result.error}` : "."} You can still review the
          retrieved sources below.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
        <div className="mb-2 flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-navy-900">Summary</h2>
          <span className="rounded-full bg-navy-50 px-2 py-0.5 text-xs text-navy-500">
            {result.jurisdiction} · {formatDate(result.created_at)}
          </span>
        </div>
        <p
          className="text-[15px] leading-relaxed text-navy-800"
          data-testid="plain-summary"
        >
          {analysis.summary.plain_language}
        </p>

        {analysis.summary.key_takeaways.length > 0 && (
          <div className="mt-4">
            <h3 className="mb-2 flex items-center gap-1.5 text-sm font-medium text-navy-700">
              <Lightbulb className="h-4 w-4 text-teal-600" aria-hidden />
              Key takeaways
            </h3>
            <ul className="space-y-2">
              {analysis.summary.key_takeaways.map((t, i) => (
                <li key={i} className="flex flex-wrap items-start gap-1.5 text-sm text-navy-700">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
                  <span className="flex-1">{t.text}</span>
                  {t.source_ids.map((sid) => (
                    <span
                      key={sid}
                      className="rounded border border-navy-100 bg-navy-50 px-1.5 py-0.5 font-mono text-[10px] text-navy-500"
                      title="Supporting retrieved source"
                    >
                      {sid}
                    </span>
                  ))}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {analysis.provisions.length > 0 && (
        <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
          <h3 className="mb-3 flex items-center gap-1.5 text-sm font-medium text-navy-700">
            <Scale className="h-4 w-4 text-indigo-600" aria-hidden />
            Provisions & references (from retrieved evidence)
          </h3>
          <ul className="space-y-2.5">
            {analysis.provisions.map((p, i) => (
              <li key={i} className="text-sm">
                <span className="font-semibold text-navy-800">{p.citation}</span>
                {p.description && (
                  <span className="text-navy-600"> — {p.description}</span>
                )}
                <span className="ml-2 inline-flex gap-1">
                  {p.source_ids.map((sid) => (
                    <span
                      key={sid}
                      className="rounded border border-indigo-100 bg-indigo-50 px-1 font-mono text-[10px] text-indigo-500"
                    >
                      {sid}
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(analysis.jurisdiction_and_dates.length > 0 ||
        analysis.conditions_and_exceptions.length > 0) && (
        <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
          <h3 className="mb-2 text-sm font-medium text-navy-700">Context & conditions</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-navy-600">
            {analysis.jurisdiction_and_dates.map((j, i) => (
              <li key={`j-${i}`}>{j}</li>
            ))}
            {analysis.conditions_and_exceptions.map((c, i) => (
              <li key={`c-${i}`}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-5">
        <h3 className="mb-2 flex items-center gap-1.5 text-sm font-medium text-amber-900">
          <AlertTriangle className="h-4 w-4" aria-hidden />
          Limitations & could-not-verify
        </h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">
          {analysis.limitations.length === 0 ? (
            <li>No explicit limitations were returned — still verify independently.</li>
          ) : (
            analysis.limitations.map((l, i) => (
              <li key={i}>
                <span className="rounded bg-amber-100 px-1 text-[10px] uppercase tracking-wide">
                  {l.kind.replace("_", " ")}
                </span>{" "}
                {l.text}
              </li>
            ))
          )}
        </ul>
      </div>

      <DisclaimerBanner />
    </section>
  );
}