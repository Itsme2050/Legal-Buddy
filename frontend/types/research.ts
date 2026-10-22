// Shared frontend types mirroring backend/app/schemas.

export type EntityType =
  | "CASE"
  | "COURT"
  | "LAW"
  | "PROVISION"
  | "PERSON"
  | "PARTY"
  | "AUTHORITY"
  | "LOCATION"
  | "LEGAL_CONCEPT"
  | "DATE";

export type RelationshipType =
  | "CITES"
  | "INTERPRETS"
  | "APPLIES"
  | "OVERRULES"
  | "DISTINGUISHES"
  | "FILED_BY"
  | "DECIDED_BY"
  | "INVOLVES"
  | "ISSUED_BY"
  | "GOVERNED_BY"
  | "GOVERNS"
  | "RELATED_TO";

export type SourceType = "official" | "court" | "legislation" | "news" | "academic" | "unknown";
export type FetchStatus = "pending" | "success" | "failed" | "skipped";
export type SessionStatus = "pending" | "running" | "completed" | "failed" | "partial";
export type StageStatus = "pending" | "running" | "completed" | "failed" | "skipped";
export type ConfidenceLabel = "direct" | "supported" | "uncertain";

export interface SourceExcerpt {
  text: string;
  url: string;
  char_start?: number | null;
  char_end?: number | null;
  note?: string | null;
}

export interface Source {
  id: string;
  title: string;
  url: string;
  source_type: SourceType;
  authority_label?: string | null;
  court_or_authority?: string | null;
  decision_date?: string | null;
  snippet?: string | null;
  retrieved_at?: string | null;
  fetch_status: FetchStatus;
  fetch_error?: string | null;
  content_markdown?: string | null;
  content_chars?: number | null;
  excerpts: SourceExcerpt[];
  provider_metadata: Record<string, unknown>;
  rank?: number | null;
}

export interface PipelineStage {
  key: string;
  label: string;
  status: StageStatus;
  detail?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface SearchStep {
  query: string;
  jurisdiction?: string | null;
  result_count: number;
  executed_at?: string | null;
}

export interface FetchStep {
  requested_urls: string[];
  succeeded: number;
  failed: number;
  skipped: number;
  executed_at?: string | null;
}

export interface Takeaway {
  text: string;
  source_ids: string[];
}

export interface Summary {
  plain_language: string;
  key_takeaways: Takeaway[];
}

export interface Provision {
  citation: string;
  description?: string | null;
  source_ids: string[];
}

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  description?: string | null;
  source_ids: string[];
}

export interface Relationship {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  type: RelationshipType;
  source_id: string;
  evidence_excerpt?: string | null;
  confidence: number;
  confidence_label: ConfidenceLabel;
  explanation?: string | null;
}

export interface LimitationItem {
  text: string;
  kind: "uncertainty" | "missing_evidence" | "jurisdiction" | "date";
}

export interface NextStep {
  text: string;
  portal_name?: string | null;
  portal_url?: string | null;
  source_ids: string[];
}

export interface AnalysisResult {
  summary: Summary;
  key_concepts: string[];
  provisions: Provision[];
  entities: Entity[];
  relationships: Relationship[];
  conditions_and_exceptions: string[];
  jurisdiction_and_dates: string[];
  limitations: LimitationItem[];
  next_steps: NextStep[];
}

export interface UsageRecord {
  session_id: string;
  search_requests: number;
  fetch_requests: number;
  fetched_successfully: number;
  analyzed_sources: number;
  gemini_prompt_tokens?: number | null;
  gemini_completion_tokens?: number | null;
  plan: "free" | "professional";
  estimated_cost_usd?: number | null;
}

export interface GraphNodePayload {
  id: string;
  type: string;
  label: string;
  entityType: EntityType;
  description?: string | null;
  source_ids: string[];
  confidence?: number | null;
}

export interface GraphEdgePayload {
  id: string;
  source: string;
  target: string;
  label: string;
  relationshipType: RelationshipType;
  source_id: string;
  evidence_excerpt?: string | null;
  explanation?: string | null;
  confidence: number;
  confidence_label: ConfidenceLabel;
}

export interface GraphPayload {
  nodes: GraphNodePayload[];
  edges: GraphEdgePayload[];
}

export interface ResearchResult {
  session_id: string;
  status: SessionStatus;
  question: string;
  jurisdiction: string;
  topic: string;
  created_at: string;
  updated_at?: string | null;
  stages: PipelineStage[];
  search_step?: SearchStep | null;
  fetch_step?: FetchStep | null;
  sources: Source[];
  analysis?: AnalysisResult | null;
  graph?: GraphPayload | null;
  usage?: UsageRecord | null;
  error?: string | null;
  disclaimer?: string | null;
}

export interface ResearchRequest {
  session_id?: string | null;
  question: string;
  jurisdiction: string;
  topic: string;
  source_preference: "official_first" | "broad";
  date_from?: string | null;
  date_to?: string | null;
  max_search_results?: number;
  max_fetch_sources?: number;
  plan?: "free" | "professional";
}

export interface HistoryItem {
  session_id: string;
  question: string;
  jurisdiction: string;
  topic: string;
  status: SessionStatus;
  created_at: string;
  source_count: number;
  fetched_count: number;
  entity_count: number;
  summary_preview?: string | null;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
}

export interface IntegrationStatusItem {
  provider: string;
  configured: boolean;
  endpoint?: string | null;
  detail?: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  app: string;
  version: string;
  environment: string;
  integrations: IntegrationStatusItem[];
  database: string;
  server_time: string;
}

export const DISCLAIMER =
  "Legal Buddy provides informational research assistance, not legal advice. Verify important information against official sources and consult a qualified lawyer before making consequential legal decisions.";

export const JURISDICTIONS = [
  "India",
  "Delhi",
  "Maharashtra",
  "Karnataka",
  "Tamil Nadu",
  "Uttar Pradesh",
  "West Bengal",
  "Gujarat",
  "Rajasthan",
  "Telangana",
  "Kerala",
  "Bihar",
  "Punjab",
  "Haryana",
] as const;

export const TOPICS = [
  { value: "tenancy", label: "Tenancy & eviction" },
  { value: "consumer_rights", label: "Consumer rights" },
  { value: "municipal", label: "Municipal / civic issues" },
  { value: "employment", label: "Employment & workplace" },
  { value: "education", label: "Education" },
  { value: "public_services", label: "Public services & RTI" },
  { value: "general", label: "General legal research" },
] as const;

export const EXAMPLE_PROMPTS = [
  "What protections may apply when a tenant faces eviction?",
  "Which official rules govern construction restrictions in a particular area?",
  "What remedies may be available for an unresolved consumer complaint?",
  "Which legal provisions are relevant to a workplace dispute?",
] as const;