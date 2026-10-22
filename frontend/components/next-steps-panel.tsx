"use client";

import { ArrowRight, ExternalLink, MessageCircleQuestion } from "lucide-react";
import type { AnalysisResult } from "@/types/research";
import { DisclaimerBanner } from "@/components/disclaimer-banner";

export function NextStepsPanel({ analysis }: { analysis?: AnalysisResult | null }) {
  const steps = analysis?.next_steps ?? [];
  const concepts = analysis?.key_concepts ?? [];

  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-base font-semibold text-navy-900">Suggested next steps</h2>
        {steps.length === 0 ? (
          <p className="text-sm text-navy-500">
            No specific next steps were supported by the retrieved evidence.
          </p>
        ) : (
          <ul className="space-y-3">
            {steps.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-navy-700">
                <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" aria-hidden />
                <div>
                  <span>{s.text}</span>
                  {s.portal_url && (
                    <a
                      href={s.portal_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="ml-2 inline-flex items-center gap-1 text-xs font-medium text-teal-700 underline underline-offset-2"
                    >
                      {s.portal_name || "Open portal"}
                      <ExternalLink className="h-3 w-3" aria-hidden />
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}

        {concepts.length > 0 && (
          <div className="mt-4">
            <h3 className="mb-2 text-sm font-medium text-navy-700">Key concepts</h3>
            <div className="flex flex-wrap gap-1.5">
              {concepts.map((c) => (
                <span
                  key={c}
                  className="rounded-full border border-navy-200 bg-navy-50 px-2.5 py-1 text-xs text-navy-600"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
        <h3 className="mb-2 flex items-center gap-1.5 text-sm font-medium text-navy-700">
          <MessageCircleQuestion className="h-4 w-4 text-teal-600" aria-hidden />
          Questions you may need to clarify
        </h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-navy-600">
          <li>Which state and local body rules apply to your exact situation?</li>
          <li>What are the relevant dates (notice served, agreement signed)?</li>
          <li>Do you have the original documents and communications?</li>
          <li>Has any forum or court already been approached?</li>
        </ul>
      </div>

      <DisclaimerBanner />
    </section>
  );
}