import { Info } from "lucide-react";

export function DisclaimerBanner({ compact = false }: { compact?: boolean }) {
  return (
    <div
      role="note"
      className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
    >
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>
        {compact
          ? "Informational research, not legal advice. Verify against official sources."
          : "Legal Buddy provides informational research assistance, not legal advice. Verify important information against official sources and consult a qualified lawyer before making consequential legal decisions."}
      </span>
    </div>
  );
}