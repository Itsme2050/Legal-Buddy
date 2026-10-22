import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-navy-100 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-navy-600">
        <p className="max-w-3xl text-navy-700">
          <strong>Disclaimer:</strong> Legal Buddy provides informational research
          assistance, not legal advice. Verify important information against
          official sources and consult a qualified lawyer before making
          consequential legal decisions.
        </p>
        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
          <a
            className="hover:text-teal-700 underline decoration-teal-300 underline-offset-4"
            href="https://github.com/"
            target="_blank"
            rel="noreferrer noopener"
          >
            GitHub
          </a>
          <a
            className="hover:text-teal-700 underline decoration-teal-300 underline-offset-4"
            href="https://github.com/#readme"
            target="_blank"
            rel="noreferrer noopener"
          >
            Documentation
          </a>
          <Link className="hover:text-teal-700" href="/pricing">
            Pricing
          </Link>
          <a
            className="hover:text-teal-700"
            href="https://docs.tinyfish.ai/"
            target="_blank"
            rel="noreferrer noopener"
          >
            Powered by TinyFish
          </a>
        </div>
        <p className="mt-4 text-xs text-navy-400">
          © {new Date().getFullYear()} Legal Buddy. Search ranking is not legal
          authority ranking. Source retrieval does not prove authenticity,
          currency, or applicability.
        </p>
      </div>
    </footer>
  );
}