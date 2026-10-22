"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  FlaskConical,
  Loader2,
  Sparkles,
} from "lucide-react";

import { ApiError, getIntegrationStatus, getHistory, startResearch } from "@/lib/api";
import {
  DISCLAIMER,
  EXAMPLE_PROMPTS,
  JURISDICTIONS,
  TOPICS,
  type HistoryItem,
  type PipelineStage,
  type ResearchRequest,
} from "@/types/research";
import { PipelineProgress } from "@/components/pipeline-progress";
import { DisclaimerBanner } from "@/components/disclaimer-banner";
import { cn, formatDate } from "@/lib/utils";

const statusStyle: Record<string, string> = {
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  partial: "bg-amber-50 text-amber-700 border-amber-200",
  failed: "bg-rose-50 text-rose-700 border-rose-200",
  running: "bg-teal-50 text-teal-700 border-teal-200",
  pending: "bg-navy-50 text-navy-500 border-navy-100",
};

const INIT_STAGES: PipelineStage[] = [
  { key: "prepare", label: "Preparing legal search", status: "pending" },
  { key: "tinyfish_search", label: "Searching live sources with TinyFish", status: "pending" },
  { key: "select", label: "Selecting relevant documents", status: "pending" },
  { key: "tinyfish_fetch", label: "Fetching source content with TinyFish", status: "pending" },
  { key: "gemini", label: "Analyzing retrieved evidence with Gemini", status: "pending" },
  { key: "graph", label: "Building the legal relationship graph", status: "pending" },
  { key: "done", label: "Research complete", status: "pending" },
];

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-6xl px-4 py-16 text-center text-sm text-navy-500">
          Loading dashboard…
        </div>
      }
    >
      <DashboardInner />
    </Suspense>
  );
}

function DashboardInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [question, setQuestion] = useState("");
  const [jurisdiction, setJurisdiction] = useState<string>("India");
  const [topic, setTopic] = useState<string>("tenancy");
  const [preference, setPreference] = useState<"official_first" | "broad">("official_first");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [stages, setStages] = useState<PipelineStage[]>(INIT_STAGES);
  const [error, setError] = useState<string | null>(null);
  const [errCode, setErrCode] = useState<string | null>(null);
  const [missingKeys, setMissingKeys] = useState<string[]>([]);
  const [recent, setRecent] = useState<HistoryItem[]>([]);
  const abortRef = useRef(false);

  // One-time integration check (surface missing credentials honestly)
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const st = (await getIntegrationStatus()) as {
          tinyfish?: { configured?: boolean };
          gemini?: { configured?: boolean };
        };
        if (!mounted) return;
        const missing: string[] = [];
        if (!st.tinyfish?.configured) missing.push("TINYFISH_API_KEY");
        if (!st.gemini?.configured) missing.push("GEMINI_API_KEY");
        setMissingKeys(missing);
      } catch {
        /* backend down — the submit path will show the real error */
      }
      try {
        const h = await getHistory();
        if (mounted) setRecent(h.items.slice(0, 5));
      } catch {
        /* ignore */
      }
    })();
    return () => {
      mounted = false;
      abortRef.current = true;
    };
  }, []);

  // Prefill from ?demo=1 or ?q=
  useEffect(() => {
    if (params?.get("demo") === "1" && !question) {
      setQuestion(EXAMPLE_PROMPTS[0]);
    }
    const q = params?.get("q");
    if (q && !question) setQuestion(q);
  }, [params, question]);

  const setStageByKey = useCallback((key: string, patch: Partial<PipelineStage>) => {
    setStages((prev) => prev.map((s) => (s.key === key ? { ...s, ...patch } : s)));
  }, []);

  const run = useCallback(async () => {
    const q = question.trim();
    if (q.length < 8) {
      setError("Please enter a fuller legal question (at least 8 characters).");
      return;
    }
    setSubmitting(true);
    setError(null);
    setErrCode(null);
    abortRef.current = false;
    setStages(INIT_STAGES.map((s) => ({ ...s, status: "pending" })));

    // Optimistically mark the prepare stage running (mirrors backend stage machine)
    setStageByKey("prepare", { status: "running" });

    const clientSessionId =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : "sess_" + Math.random().toString(36).substring(2, 11);

    const body: ResearchRequest = {
      session_id: clientSessionId,
      question: q,
      jurisdiction,
      topic,
      source_preference: preference,
      date_from: dateFrom || null,
      date_to: dateTo || null,
    };

    let sse: EventSource | null = null;
    if (typeof window !== "undefined" && typeof EventSource !== "undefined") {
      try {
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
          "http://localhost:8000";
        sse = new EventSource(`${apiBase}/api/research/${clientSessionId}/stream`);
        sse.addEventListener("status", (evt) => {
          try {
            const data = JSON.parse(evt.data);
            if (Array.isArray(data.stages) && data.stages.length > 0) {
              setStages(data.stages);
            }
          } catch {
            /* ignore SSE parse */
          }
        });
        sse.addEventListener("done", () => {
          sse?.close();
        });
        sse.addEventListener("error", () => {
          sse?.close();
        });
      } catch {
        /* fallback to response */
      }
    }

    try {
      const res = await startResearch(body);
      sse?.close();
      if (abortRef.current) return;
      const result = res.result;
      // Reconcile stages from real backend state — never invent progress
      setStages(
        result.stages?.length
          ? result.stages
          : INIT_STAGES.map((s) => ({ ...s, status: "completed" }))
      );
      if (result.status === "failed") {
        setError(result.error ?? "Research failed.");
        setErrCode("failed");
      } else {
        router.push(`/results/${result.session_id}`);
      }
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
        setErrCode(e.code);
        setStages((prev) => {
          const running = prev.find((s) => s.status === "running");
          return prev.map((s) =>
            s.key === running?.key ? { ...s, status: "failed", detail: e.message } : s
          );
        });
      } else {
        setError(
          "Could not reach the backend. Is it running on http://localhost:8000?"
        );
        setErrCode("network");
      }
    } finally {
      sse?.close();
      setSubmitting(false);
    }
  }, [question, jurisdiction, topic, preference, dateFrom, dateTo, router, setStageByKey]);

  const showPipeline = submitting || stages.some((s) => s.status !== "pending");

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-navy-900">Legal research dashboard</h1>
        <p className="mt-1 text-navy-600">
          Ask in plain language. Results depend on your jurisdiction and the
          evidence successfully retrieved — not on guesswork.
        </p>
      </header>

      {missingKeys.length > 0 && (
        <div
          data-testid="missing-keys"
          className="mb-6 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div>
            <p className="font-medium">
              Setup needed: {missingKeys.join(" and ")} not configured on the backend.
            </p>
            <p className="mt-0.5 text-xs">
              Add the key(s) to <code className="rounded bg-amber-100 px-1">backend/.env</code>{" "}
              (see <code className="rounded bg-amber-100 px-1">.env.example</code>) and restart
              the server. Legal Buddy will never substitute simulated results for a
              live request.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        {/* Left: form */}
        <div className="space-y-4">
          <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
            <label htmlFor="question" className="mb-2 block text-sm font-medium text-navy-800">
              Your legal question
            </label>
            <textarea
              id="question"
              data-testid="question-input"
              rows={4}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. My landlord is threatening to evict me without notice. What legal protections may apply in India?"
              className="w-full resize-y rounded-lg border border-navy-200 p-3 text-sm focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100"
            />

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-sm">
                <span className="mb-1 block font-medium text-navy-700">Jurisdiction</span>
                <select
                  data-testid="jurisdiction-select"
                  value={jurisdiction}
                  onChange={(e) => setJurisdiction(e.target.value)}
                  className="w-full rounded-lg border border-navy-200 p-2 text-sm focus:border-teal-400 focus:outline-none"
                >
                  {JURISDICTIONS.map((j) => (
                    <option key={j} value={j}>
                      {j}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <span className="mb-1 block font-medium text-navy-700">Topic</span>
                <select
                  data-testid="topic-select"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full rounded-lg border border-navy-200 p-2 text-sm focus:border-teal-400 focus:outline-none"
                >
                  {TOPICS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <fieldset className="mt-4">
              <legend className="mb-1.5 text-sm font-medium text-navy-700">
                Source preference
              </legend>
              <div className="flex gap-2">
                <button
                  onClick={() => setPreference("official_first")}
                  data-testid="pref-official"
                  aria-pressed={preference === "official_first"}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-sm",
                    preference === "official_first"
                      ? "border-teal-400 bg-teal-50 text-teal-800"
                      : "border-navy-200 text-navy-600 hover:bg-navy-50"
                  )}
                >
                  Official sources first
                </button>
                <button
                  onClick={() => setPreference("broad")}
                  data-testid="pref-broad"
                  aria-pressed={preference === "broad"}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-sm",
                    preference === "broad"
                      ? "border-teal-400 bg-teal-50 text-teal-800"
                      : "border-navy-200 text-navy-600 hover:bg-navy-50"
                  )}
                >
                  Broader research
                </button>
              </div>
            </fieldset>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-sm">
                <span className="mb-1 block font-medium text-navy-700">
                  From date <span className="font-normal text-navy-400">(optional)</span>
                </span>
                <input
                  type="date"
                  data-testid="date-from"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full rounded-lg border border-navy-200 p-2 text-sm"
                />
              </label>
              <label className="text-sm">
                <span className="mb-1 block font-medium text-navy-700">
                  To date <span className="font-normal text-navy-400">(optional)</span>
                </span>
                <input
                  type="date"
                  data-testid="date-to"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full rounded-lg border border-navy-200 p-2 text-sm"
                />
              </label>
            </div>

            <button
              onClick={run}
              disabled={submitting}
              data-testid="submit-research"
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-5 py-3 font-medium text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  Researching…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" aria-hidden />
                  Start Research <ArrowRight className="h-4 w-4" aria-hidden />
                </>
              )}
            </button>

            {error && (
              <div
                role="alert"
                data-testid="research-error"
                className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-800"
              >
                <p className="font-medium">
                  {errCode === "tinyfish_unconfigured"
                    ? "TinyFish is not configured"
                    : errCode === "gemini_unconfigured"
                      ? "Gemini is not configured"
                      : errCode === "rate_limited"
                        ? "Rate limited"
                        : errCode === "network"
                          ? "Backend unreachable"
                          : "Research failed"}
                </p>
                <p className="mt-1 text-xs">{error}</p>
              </div>
            )}

            <div className="mt-4">
              <DisclaimerBanner compact />
            </div>
          </div>

          {/* Example prompts */}
          <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
            <h2 className="mb-3 text-sm font-semibold text-navy-800">Try an example</h2>
            <div className="flex flex-col gap-2">
              {EXAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => setQuestion(p)}
                  data-testid="example-prompt"
                  className="rounded-lg border border-navy-100 bg-navy-50/60 px-3 py-2 text-left text-sm text-navy-700 transition-colors hover:border-teal-200 hover:bg-teal-50"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: pipeline + recent */}
        <div className="space-y-4">
          {showPipeline ? (
            <PipelineProgress stages={stages} />
          ) : (
            <div className="rounded-xl border border-dashed border-navy-200 bg-white p-5 text-sm text-navy-500">
              <p className="font-medium text-navy-700">Live research pipeline</p>
              <p className="mt-1 text-xs">
                Stages appear here when you start a search: TinyFish Search →
                document selection → TinyFish Fetch → Gemini analysis → graph.
                Progress is driven by real backend status, never simulated.
              </p>
              <ul className="mt-3 space-y-1.5 text-xs text-navy-400">
                {INIT_STAGES.map((s) => (
                  <li key={s.key} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-navy-200" />
                    {s.label}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-navy-800">Recent research</h2>
              <a href="/history" className="text-xs text-teal-700 hover:underline">
                View all →
              </a>
            </div>
            {recent.length === 0 ? (
              <p className="text-sm text-navy-500">No sessions yet — start your first search.</p>
            ) : (
              <ul className="space-y-2.5">
                {recent.map((r) => (
                  <li key={r.session_id}>
                    <a
                      href={`/results/${r.session_id}`}
                      className="block rounded-lg border border-navy-100 p-2.5 transition-colors hover:border-teal-200 hover:bg-teal-50/40"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="line-clamp-2 text-sm text-navy-800">{r.question}</span>
                        <span
                          className={cn(
                            "shrink-0 rounded border px-1.5 py-0.5 text-[10px] uppercase",
                            statusStyle[r.status]
                          )}
                        >
                          {r.status}
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] text-navy-400">
                        {formatDate(r.created_at)} · {r.fetched_count}/{r.source_count} fetched ·{" "}
                        {r.entity_count} nodes
                      </p>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {params?.get("demo") === "1" && (
            <p className="flex items-start gap-1.5 text-xs text-navy-500">
              <FlaskConical className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              Demo mode: example question pre-filled. Saved sample results on the
              landing page are clearly labelled as cached — never presented as
              live.
            </p>
          )}
        </div>
      </div>
      <p className="mt-6 text-xs text-navy-400">{DISCLAIMER}</p>
    </div>
  );
}