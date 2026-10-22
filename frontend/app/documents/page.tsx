"use client";

import { useCallback, useRef, useState } from "react";
import { AlertTriangle, FileUp, Loader2, UploadCloud } from "lucide-react";

import { ApiError, analyzeDocument } from "@/lib/api";
import type { DocumentAnalysisResponse } from "@/lib/api";
import { SummaryPanel } from "@/components/summary-panel";
import { RelationshipGraph } from "@/components/graph/relationship-graph";
import { DISCLAIMER, type ResearchResult } from "@/types/research";
import { cn } from "@/lib/utils";

const MAX_BYTES = 10 * 1024 * 1024;

export default function DocumentsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<DocumentAnalysisResponse | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const pick = useCallback((f: File | null | undefined) => {
    setLocalError(null);
    setResp(null);
    setServerError(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setLocalError("Only PDF files are supported.");
      return;
    }
    if (f.size > MAX_BYTES) {
      setLocalError("File is larger than the 10 MB limit.");
      return;
    }
    if (f.type && f.type !== "application/pdf") {
      setLocalError("File must be a PDF.");
      return;
    }
    setFile(f);
  }, []);

  const upload = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setServerError(null);
    setResp(null);
    try {
      const r = await analyzeDocument(file);
      setResp(r);
      if (r.error) setServerError(r.error);
    } catch (e) {
      setServerError(
        e instanceof ApiError ? e.message : "Upload failed — is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  }, [file]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-navy-900">
          <FileUp className="h-6 w-6 text-teal-600" aria-hidden />
          Document analysis
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-navy-600">
          Upload a PDF (max 10 MB) for a grounded summary, entity extraction and a
          relationship graph. Uploaded documents are processed in memory and
          clearly separated from live-web research.
        </p>
      </header>

      <div className="mb-4 rounded-lg border border-sky-200 bg-sky-50 px-4 py-2.5 text-xs text-sky-900">
        <strong>Note:</strong> uploaded content is labelled{" "}
        <code className="rounded bg-sky-100 px-1">user_uploaded</code> — it is
        never presented as fetched or verified by TinyFish.
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          pick(e.dataTransfer.files?.[0]);
        }}
        className={cn(
          "rounded-xl border-2 border-dashed bg-white p-8 text-center transition-colors",
          dragOver ? "border-teal-400 bg-teal-50/50" : "border-navy-200"
        )}
        data-testid="drop-zone"
      >
        <UploadCloud className="mx-auto mb-3 h-10 w-10 text-navy-300" aria-hidden />
        <p className="text-sm font-medium text-navy-800">
          Drag & drop a PDF here, or
        </p>
        <div className="mt-3">
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            data-testid="file-input"
            onChange={(e) => pick(e.target.files?.[0])}
          />
          <button
            onClick={() => inputRef.current?.click()}
            className="rounded-lg border border-navy-200 px-4 py-2 text-sm font-medium text-navy-700 hover:bg-navy-50"
          >
            Choose file
          </button>
          {file && (
            <span className="ml-3 text-sm text-navy-600">
              {file.name}{" "}
              <span className="text-navy-400">
                ({(file.size / 1024).toFixed(0)} KB)
              </span>
            </span>
          )}
        </div>
        <button
          onClick={() => void upload()}
          disabled={!file || loading}
          data-testid="analyze-upload"
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Extracting & analyzing…
            </>
          ) : (
            "Analyze document"
          )}
        </button>
      </div>

      {localError && (
        <div
          role="alert"
          data-testid="upload-error"
          className="mt-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          {localError}
        </div>
      )}
      {serverError && (
        <div
          role="alert"
          className="mt-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div>
            <p className="font-medium">Analysis issue</p>
            <p className="mt-1 text-xs">{serverError}</p>
          </div>
        </div>
      )}

      {resp && (
        <div className="mt-8 space-y-6 animate-fade-in">
          {/* Metadata */}
          <div className="rounded-xl border border-navy-100 bg-white p-4 text-sm shadow-sm">
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-navy-600">
              <span>
                <span className="text-navy-400">File:</span> {resp.filename}
              </span>
              <span>
                <span className="text-navy-400">Size:</span>{" "}
                {(resp.size_bytes / 1024).toFixed(0)} KB
              </span>
              <span>
                <span className="text-navy-400">Text extracted:</span>{" "}
                {resp.text_chars.toLocaleString()} chars
              </span>
              <span>
                <span className="text-navy-400">Provenance:</span>{" "}
                <span className="rounded bg-navy-50 px-1.5 py-0.5 text-xs text-navy-600">
                  {resp.fetch_status_note}
                </span>
              </span>
            </div>
          </div>

          {/* Preview */}
          <div className="rounded-xl border border-navy-100 bg-white p-5 shadow-sm">
            <h2 className="mb-2 text-sm font-semibold text-navy-800">
              Extracted text preview
            </h2>
            <details open>
              <summary className="cursor-pointer text-xs text-teal-700">
                Show preview
              </summary>
              <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded bg-navy-50 p-3 text-xs leading-relaxed text-navy-700">
                {resp.preview_markdown}
              </pre>
            </details>
          </div>

          {/* Summary */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div>
              <h2 className="mb-3 text-base font-semibold text-navy-900">
                Document summary
              </h2>
              <SummaryPanel
                result={
                  {
                    session_id: resp.document_id,
                    question: `Analysis of ${resp.filename}`,
                    jurisdiction: "as stated in document",
                    topic: "general",
                    created_at: new Date().toISOString(),
                    sources: [],
                    stages: [],
                    status: resp.status === "success" ? "completed" : "failed",
                  } satisfies ResearchResult
                }
                analysis={resp.analysis ?? null}
              />
            </div>
            <div>
              <h2 className="mb-3 text-base font-semibold text-navy-900">
                Entity & relationship graph
              </h2>
              <RelationshipGraph
                graph={resp.graph ?? { nodes: [], edges: [] }}
                sources={[]}
                sessionId={resp.document_id}
              />
            </div>
          </div>

          <p className="text-xs text-navy-400">{resp.disclaimer ?? DISCLAIMER}</p>
        </div>
      )}
    </div>
  );
}