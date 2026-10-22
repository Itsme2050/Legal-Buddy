// Typed API client for the Legal Buddy backend.

import type {
  HistoryResponse,
  ResearchRequest,
  ResearchResult,
} from "@/types/research";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code: string;
  detail?: unknown;

  constructor(status: number, code: string, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let code = "http_error";
  let message = `Request failed (HTTP ${res.status})`;
  let detail: unknown;
  try {
    const body = await res.json();
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      detail = body.error.detail;
    } else if (body?.detail) {
      message =
        typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      detail = body.detail;
    }
  } catch {
    /* non-JSON body — keep defaults */
  }
  return new ApiError(res.status, code, message, detail);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as T;
}

export function apiBase(): string {
  return BASE;
}

export async function getHealth() {
  return request<{
    status: string;
    app: string;
    integrations: { provider: string; configured: boolean; detail?: string | null }[];
    database: string;
  }>("/health");
}

export async function getIntegrationStatus() {
  return request<Record<string, unknown>>("/api/integrations/status");
}

export interface StartResearchResponse {
  session_id: string;
  status: string;
  result: ResearchResult;
}

export async function startResearch(body: ResearchRequest): Promise<StartResearchResponse> {
  return request<StartResearchResponse>("/api/research", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getSession(sessionId: string): Promise<{ result: ResearchResult }> {
  return request<{ result: ResearchResult }>(
    `/api/research/${encodeURIComponent(sessionId)}`
  );
}

export async function getSessionSources(sessionId: string) {
  return request<{ sources: ResearchResult["sources"] }>(
    `/api/research/${encodeURIComponent(sessionId)}/sources`
  );
}

export async function getSessionGraph(sessionId: string) {
  return request<NonNullable<ResearchResult["graph"]>>(
    `/api/research/${encodeURIComponent(sessionId)}/graph`
  );
}

export async function getHistory(): Promise<HistoryResponse> {
  return request<HistoryResponse>("/api/history");
}

export async function deleteSession(sessionId: string) {
  return request<{ deleted: boolean }>(
    `/api/history/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" }
  );
}

export interface DocumentAnalysisResponse {
  document_id: string;
  filename: string;
  size_bytes: number;
  text_chars: number;
  status: "pending" | "success" | "failed" | "skipped";
  preview_markdown: string;
  fetch_status_note: string;
  analysis?: ResearchResult["analysis"];
  graph?: ResearchResult["graph"];
  error?: string | null;
  disclaimer?: string | null;
}

export async function analyzeDocument(file: File): Promise<DocumentAnalysisResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("plan", "free");
  return request<DocumentAnalysisResponse>("/api/documents/analyze", {
    method: "POST",
    body: form,
  });
}