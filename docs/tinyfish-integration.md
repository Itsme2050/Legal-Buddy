# TinyFish Integration in Legal Buddy

TinyFish is the **only** live-web retrieval path in Legal Buddy. Nothing is simulated, hardcoded, or silently substituted. When credentials are not provided or a retrieval fails, the application reports the error honestly and never fabricates mock legal authorities.

## 1. Where TinyFish is Used

| Pipeline Step | Code Location | Primary Methods | TinyFish Service |
|---|---|---|---|
| **Live Discovery** | `backend/app/services/tinyfish_client.py` | `TinyFishClient.search_legal_sources()` | TinyFish **Search API** (`GET /`) |
| **Document Retrieval** | `backend/app/services/tinyfish_client.py` | `TinyFishClient.fetch_source()`, `fetch_multiple_sources()` | TinyFish **Fetch API** (`POST /`, fallback `GET /`) |
| **Result Normalization** | `backend/app/services/tinyfish_client.py` | `normalize_search_results()`, `normalize_fetch_result()` | Pure normalization functions |
| **Workflow Orchestration** | `backend/app/services/research_workflow.py` | `ResearchWorkflow.run()`, `_execute()` | End-to-end async pipeline |

---

## 2. Search Request & Response Contract

- **Endpoint Default:** `https://api.search.tinyfish.ai` (configurable via `TINYFISH_SEARCH_ENDPOINT`)
- **Authentication:** `X-API-Key` header with `TINYFISH_API_KEY`
- **HTTP Method:** `GET`
- **Request Parameters:**
  - `query`: Deterministically engineered legal search query (e.g. `tenant eviction notice India (site:gov.in OR site:sci.gov.in)`).
  - `location`: Jurisdiction string (e.g. `India`, `Delhi`, `Maharashtra`).
  - `include_domains`: When `source_preference == "official_first"`, passes authoritative government domains (`gov.in`, `nic.in`, `indiacode.nic.in`, `sci.gov.in`, `ecourts.gov.in`).
  - `after_date` / `before_date`: Optional ISO date filters from user request.
- **Normalization:**
  - Accepts `{ results: [...] }`, `{ data: [...] }`, or raw list payloads.
  - Strips URL schemes, www prefixes, and trailing slashes for canonical deduplication.
  - Assigns `authority_score` (0.0 to 1.0) prioritizing court repositories (`sci.gov.in`, `ecourts.gov.in`, `indiacode.nic.in`, `kanoon.org`).
  - Classifies source types into `COURT`, `LEGISLATION`, `OFFICIAL`, `ACADEMIC`, `NEWS`, or `UNKNOWN`.
  - Preserves provider metadata without data loss.

---

## 3. Fetch Request & Response Contract

- **Endpoint Default:** `https://api.fetch.tinyfish.ai` (configurable via `TINYFISH_FETCH_ENDPOINT`)
- **Authentication:** `X-API-Key` header with `TINYFISH_API_KEY`
- **HTTP Method:** `POST` with JSON body `{"url": "<target_url>"}` (automatically falls back to `GET ?url=` upon HTTP 405 Method Not Allowed).
- **Concurrency & Safety:**
  - Bounded concurrency with `asyncio.Semaphore` (default max 4 concurrent requests).
  - Pre-flight SSRF protection via `validate_public_url` in `app/core/security.py` (rejects private IP ranges, loopback, metadata services).
- **Response Parsing:**
  - Extracts Markdown text from `markdown`, `content_markdown`, `text`, `html_text`, or nested `data` envelopes.
  - Retains original target URL, retrieval timestamp, and provider metadata.
  - Computes `content_chars` and extracts keyword-window evidence passages via `extract_relevant_excerpts()`.

---

## 4. Honest Failure Modes & Fallback

| Failure Condition | Exception Raised | Application & UI Behavior |
|---|---|---|
| Missing `TINYFISH_API_KEY` | `TinyFishConfigError` | Session status set to `failed`; UI displays setup notification with exact `.env` instructions. |
| HTTP 401 / 403 | `TinyFishAuthError` | Identifies invalid or revoked API key; no simulated results substituted. |
| HTTP 429 | `TinyFishRateLimitError` | Informs user of provider rate limits with advice to retry. |
| Timeout | `TinyFishTimeoutError` | Handled cleanly; indicates provider timeout after `TINYFISH_TIMEOUT_SECONDS`. |
| 200 OK but 0 results | `TinyFishEmptyResultError` | Reports zero results found for the specific query; encourages broader search parameters. |
| Per-URL Fetch Failure | Handled per source | Sets source `fetch_status: failed` with provider error; other successful sources proceed to Gemini. |
| All Fetches Failed | `TinyFishError` | Fails session honestly: "All source fetches failed — no evidence available for analysis." |

---

## 5. Evidence Flow into Gemini & React Flow Graph

1. Fetched Markdown is capped per source (`GEMINI_MAX_EXCERPT_CHARS`) and packaged into structured `===== EVIDENCE source_N =====` blocks with explicit provenance metadata.
2. The Gemini system prompt marks retrieved text as **untrusted data** and demands that every takeaway, legal provision, and entity node reference an actual retrieved `source_id`.
3. Pydantic validation rejects fabricated source IDs and automatically downgrades `OVERRULES`/`DISTINGUISHES` relationships unless explicit evidence exists in the text.
4. The React Flow graph maps verified entities and relationships into interactive nodes and edges, allowing users to inspect the exact underlying excerpt for every legal connection.

---

## 6. Live Testing Verification

Live integration tests are located in `backend/tests/test_integration_live.py`:
- `test_live_tinyfish_search`: Executes a live search query against `https://api.search.tinyfish.ai`.
- `test_live_tinyfish_fetch_of_official_source`: Tests retrieval of an official legal portal.
- Run with:
  ```bash
  cd backend && TINYFISH_API_KEY="your-key" GEMINI_API_KEY="your-key" python -m pytest -m integration
  ```
