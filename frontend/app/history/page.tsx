"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Archive, Clock, Loader2, Trash2 } from "lucide-react";

import { ApiError, deleteSession, getHistory } from "@/lib/api";
import type { HistoryItem } from "@/types/research";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

const statusStyle: Record<string, string> = {
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  partial: "bg-amber-50 text-amber-700 border-amber-200",
  failed: "bg-rose-50 text-rose-700 border-rose-200",
  running: "bg-teal-50 text-teal-700 border-teal-200",
  pending: "bg-navy-50 text-navy-500 border-navy-100",
};

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const h = await getHistory();
      setItems(h.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const onDelete = async (id: string) => {
    if (!confirm("Delete this research session? This cannot be undone.")) return;
    setDeleting(id);
    try {
      await deleteSession(id);
      setItems((prev) => prev.filter((i) => i.session_id !== id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Delete failed.");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-navy-900">
            <Archive className="h-6 w-6 text-teal-600" aria-hidden />
            Research history
          </h1>
          <p className="mt-1 text-sm text-navy-600">
            Sessions expire after the retention window (30 days). Deleting removes
            sources, analysis and graph data permanently.
          </p>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="skeleton h-24 rounded-xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-navy-200 bg-white p-10 text-center">
          <Clock className="mx-auto mb-2 h-8 w-8 text-navy-300" aria-hidden />
          <p className="font-medium text-navy-700">No research sessions yet</p>
          <p className="mt-1 text-sm text-navy-500">
            Completed searches will appear here with their sources and graph.
          </p>
          <Link
            href="/dashboard"
            className="mt-4 inline-block rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
          >
            Start your first research
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li
              key={item.session_id}
              data-testid="history-item"
              className="rounded-xl border border-navy-100 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <Link
                  href={`/results/${item.session_id}`}
                  className="min-w-0 flex-1 group"
                >
                  <p className="break-words text-sm font-medium text-navy-900 group-hover:text-teal-700">
                    {item.question}
                  </p>
                  {item.summary_preview && (
                    <p className="mt-1 line-clamp-2 text-xs text-navy-500">
                      {item.summary_preview}
                    </p>
                  )}
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-navy-400">
                    <span
                      className={cn(
                        "rounded border px-1.5 py-0.5 uppercase",
                        statusStyle[item.status]
                      )}
                    >
                      {item.status}
                    </span>
                    <span>{formatDate(item.created_at)}</span>
                    <span>·</span>
                    <span>{item.jurisdiction}</span>
                    <span>·</span>
                    <span>
                      {item.fetched_count}/{item.source_count} fetched
                    </span>
                    <span>·</span>
                    <span>{item.entity_count} graph nodes</span>
                  </div>
                </Link>
                <button
                  onClick={() => void onDelete(item.session_id)}
                  disabled={deleting === item.session_id}
                  aria-label="Delete session"
                  data-testid="delete-session"
                  className="shrink-0 rounded-md border border-navy-200 p-2 text-navy-400 transition-colors hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-40"
                >
                  {deleting === item.session_id ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  ) : (
                    <Trash2 className="h-4 w-4" aria-hidden />
                  )}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-6 text-xs text-navy-400">
        Demo-mode limitation: there is no user authentication in this MVP, so
        session IDs are not a security boundary. Treat history as demo data.
      </p>
    </div>
  );
}