import { Check, Info } from "lucide-react";
import { DisclaimerBanner } from "@/components/disclaimer-banner";

const freeFeatures = [
  "Legal research for ordinary citizens",
  "Fair-use research limit (10 searches / 25 fetches per day)",
  "Bounded document analysis (10 MB PDFs)",
  "Interactive relationship graph viewing",
  "Source citations and JSON export",
  "30-day research history",
];

const proFeatures = [
  "Everything in Free, plus:",
  "Higher research limits (100 searches / 500 fetches per day)",
  "More document analyses",
  "Graph exports (JSON + PNG)",
  "Extended research history and case organization",
  "Priority support when it ships",
  "Bulk research tools (on the roadmap)",
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-navy-900">Pricing</h1>
        <p className="mx-auto mt-2 max-w-2xl text-navy-600">
          Transparent freemium pricing. Limits are configurable and reflect actual
          TinyFish and Gemini usage costs — we don&apos;t promise unlimited API
          usage we can&apos;t back up.
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Free */}
        <div className="rounded-2xl border border-navy-100 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-navy-900">Citizen Free</h2>
          <p className="mt-1 text-sm text-navy-500">For individuals exploring their rights</p>
          <p className="mt-4 text-4xl font-bold text-navy-900">
            ₹0
            <span className="text-base font-normal text-navy-400"> / month</span>
          </p>
          <ul className="mt-5 space-y-2.5">
            {freeFeatures.map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm text-navy-700">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" aria-hidden />
                {f}
              </li>
            ))}
          </ul>
          <a
            href="/dashboard"
            className="mt-6 block rounded-lg border border-navy-200 px-4 py-2.5 text-center text-sm font-medium text-navy-800 hover:bg-navy-50"
          >
            Start researching
          </a>
        </div>

        {/* Professional */}
        <div className="relative rounded-2xl border-2 border-teal-400 bg-white p-6 shadow-md">
          <span className="absolute -top-3 left-6 rounded-full bg-teal-600 px-3 py-0.5 text-xs font-semibold text-white">
            Proposed plan
          </span>
          <h2 className="text-lg font-semibold text-navy-900">
            Legal Buddy Professional
          </h2>
          <p className="mt-1 text-sm text-navy-500">
            For small law firms, legal-aid NGOs and researchers
          </p>
          <p className="mt-4 text-4xl font-bold text-navy-900">
            ₹999
            <span className="text-base font-normal text-navy-400"> / month</span>
          </p>
          <ul className="mt-5 space-y-2.5">
            {proFeatures.map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm text-navy-700">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" aria-hidden />
                {f}
              </li>
            ))}
          </ul>
          <button
            disabled
            title="Payments are not implemented in this MVP"
            className="mt-6 w-full cursor-not-allowed rounded-lg bg-navy-100 px-4 py-2.5 text-sm font-medium text-navy-400"
          >
            Coming soon — payments not yet implemented
          </button>
        </div>
      </div>

      {/* Cost assumptions */}
      <div className="mt-8 rounded-xl border border-navy-100 bg-white p-6 shadow-sm">
        <h2 className="flex items-center gap-1.5 text-base font-semibold text-navy-900">
          <Info className="h-4 w-4 text-teal-600" aria-hidden />
          How we think about cost
        </h2>
        <div className="mt-3 grid gap-4 text-sm text-navy-600 md:grid-cols-3">
          <p>
            Every research session makes a TinyFish Search call and up to 5
            Fetch calls, then one Gemini analysis over bounded excerpts. Usage
            counters per session are visible under{" "}
            <code className="rounded bg-navy-50 px-1">/api/usage/summary</code>.
          </p>
          <p>
            The ₹999/month price is <strong>proposed</strong> — its viability
            depends on actual TinyFish pricing, Gemini token costs, average
            sources per session, hosting and storage. We don&apos;t claim
            verified profitability or invent market figures.
          </p>
          <p>
            Free-tier limits are configurable environment variables, not
            hardcoded claims about provider allowances. Excess usage returns a
            clear 429 with the current plan limits.
          </p>
        </div>
      </div>

      <div className="mt-6">
        <DisclaimerBanner />
      </div>
    </div>
  );
}