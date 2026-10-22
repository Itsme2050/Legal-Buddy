import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  FileSearch,
  GitBranch,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { DisclaimerBanner } from "@/components/disclaimer-banner";

const features = [
  {
    icon: FileSearch,
    title: "Live discovery with TinyFish Search",
    body: "Your question becomes a targeted query against live web sources — prioritising court and government domains without pretending any result is authoritative on its own.",
  },
  {
    icon: BookOpen,
    title: "Real documents via TinyFish Fetch",
    body: "Retrieved pages and supported PDFs are pulled as AI-ready Markdown, with original URLs, retrieval timestamps, and honest per-source fetch status.",
  },
  {
    icon: Sparkles,
    title: "Plain-language Gemini analysis",
    body: "A two-sentence summary, key takeaways and provisions — each linked to retrieved source IDs and validated against the evidence set.",
  },
  {
    icon: GitBranch,
    title: "Interactive relationship graph",
    body: "Cases, laws, provisions, courts and authorities mapped in React Flow. Click any edge to read the excerpt that supports it.",
  },
  {
    icon: ShieldCheck,
    title: "Evidence-guarded outputs",
    body: "Fabricated citations are dropped before you see them, OVERRULES claims are downgraded without explicit support, and failures are shown — not hidden.",
  },
  {
    icon: Scale,
    title: "Built for Indian civic reality",
    body: "Tenancy, consumer, municipal, employment and RTI questions with jurisdiction-aware retrieval for citizens, students and legal-aid teams.",
  },
];

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4">
      {/* Hero */}
      <section className="py-14 text-center">
        <p className="mx-auto mb-4 inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700">
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          TinyFish Search & Fetch · Google Gemini · React Flow
        </p>
        <h1 className="mx-auto max-w-3xl text-4xl font-bold leading-tight tracking-tight text-navy-900 sm:text-5xl">
          The law is complex. Understanding your rights shouldn&apos;t be.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-navy-600">
          Live legal research that discovers official sources, analyzes real
          documents, explains them in plain language, and maps how cases, laws
          and authorities connect.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-6 py-3 font-medium text-white shadow-sm transition-colors hover:bg-teal-700"
          >
            Start Legal Research <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link
            href="/dashboard?demo=1"
            className="inline-flex items-center gap-2 rounded-lg border border-navy-200 bg-white px-6 py-3 font-medium text-navy-800 transition-colors hover:bg-navy-50"
          >
            Explore Demo
          </Link>
        </div>
        <p className="mt-3 text-xs text-navy-400">
          Results depend on your jurisdiction and the evidence successfully
          retrieved. Educational guidance — not personalised legal advice.
        </p>
      </section>

      {/* Features */}
      <section className="border-t border-navy-100 py-12">
        <h2 className="text-center text-2xl font-bold text-navy-900">
          From a question to evidence-backed understanding
        </h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm"
            >
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-navy-50 text-teal-600">
                <f.icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="mt-3 font-semibold text-navy-900">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-navy-600">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Product preview — clearly labelled sample */}
      <section className="border-t border-navy-100 py-12">
        <div className="grid items-center gap-8 lg:grid-cols-2">
          <div>
            <h2 className="text-2xl font-bold text-navy-900">
              A research workspace you can audit
            </h2>
            <p className="mt-3 text-navy-600">
              Every session shows the live pipeline, retrieved sources with fetch
              status, a grounded summary with source chips, and a filterable
              relationship graph — each edge traceable to an excerpt.
            </p>
            <ul className="mt-4 list-disc space-y-1.5 pl-5 text-sm text-navy-700">
              <li>“Could not verify” states when evidence is insufficient</li>
              <li>Original URLs and retrieval timestamps preserved</li>
              <li>Research history you can reopen and export</li>
            </ul>
            <Link
              href="/dashboard"
              className="mt-6 inline-flex items-center gap-2 rounded-lg bg-navy-900 px-5 py-2.5 font-medium text-white hover:bg-navy-800"
            >
              Try it live <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
          <div className="rounded-xl border border-navy-200 bg-white p-5 shadow-sm">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-amber-600">
              Sample result (cached — not a fresh live search)
            </p>
            <p className="text-sm font-semibold text-navy-900">
              Q: Can my landlord evict me without notice in India?
            </p>
            <p className="mt-2 text-sm text-navy-700">
              Most states require written notice and a lawful procedure before
              eviction; summary eviction outside these provisions is generally
              not permitted.{" "}
              <span className="rounded bg-navy-50 px-1 font-mono text-[10px] text-navy-500">
                source_1
              </span>{" "}
              <span className="rounded bg-navy-50 px-1 font-mono text-[10px] text-navy-500">
                source_2
              </span>
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
              <span className="rounded border border-teal-200 bg-teal-50 px-1.5 py-0.5 text-teal-700">
                LAW · Rent Control Act
              </span>
              <span className="rounded border border-navy-200 bg-navy-50 px-1.5 py-0.5 text-navy-600">
                COURT · High Court
              </span>
              <span className="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-amber-700">
                GOVERNED_BY · uncertain
              </span>
            </div>
            <div className="mt-4 h-32 rounded border border-dashed border-navy-200 bg-navy-50/60 p-3 text-[11px] text-navy-400">
              ● LAW ──GOVERNS── ● PROVISION
              <br />
              ● COURT ──DECIDED_BY── dashed → ● CASE (uncertain)
            </div>
          </div>
        </div>
      </section>

      {/* Privacy / responsible AI */}
      <section className="border-t border-navy-100 py-12">
        <div className="rounded-xl border border-navy-100 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-navy-900">
            Privacy & responsible AI
          </h2>
          <div className="mt-3 grid gap-4 text-sm text-navy-600 sm:grid-cols-3">
            <p>
              API keys stay on the backend; retrieved text is treated as
              untrusted data, never as instructions.
            </p>
            <p>
              Uploaded PDFs are processed in memory and never stored — only
              metadata and previews are kept for your session.
            </p>
            <p>
              Sessions auto-expire after the retention window; you can delete
              any session from History at any time.
            </p>
          </div>
          <div className="mt-4">
            <DisclaimerBanner />
          </div>
        </div>
      </section>

      {/* Pricing teaser */}
      <section className="border-t border-navy-100 py-12 text-center">
        <h2 className="text-2xl font-bold text-navy-900">Simple, transparent pricing</h2>
        <p className="mx-auto mt-2 max-w-xl text-navy-600">
          Free for citizens with fair-use limits. A proposed Professional tier at
          ₹999/month for firms and researchers — limits reflect actual API and
          model costs, not unlimited promises.
        </p>
        <Link
          href="/pricing"
          className="mt-5 inline-flex items-center gap-2 rounded-lg border border-navy-200 bg-white px-5 py-2.5 font-medium text-navy-800 hover:bg-navy-50"
        >
          View pricing details <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </section>
    </div>
  );
}