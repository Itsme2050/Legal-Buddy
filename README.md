# ⚖️ Legal Buddy

**Understand the law. Know your rights. Take the next step.**

AI-powered legal research and civic law navigator: discover live legal sources
with **TinyFish Search**, retrieve real documents with **TinyFish Fetch**,
explain them in plain language with **Google Gemini**, and visualize how cases,
laws, provisions, courts and authorities connect in an interactive **React Flow**
relationship graph.

> **Disclaimer:** Legal Buddy provides informational research assistance, **not
> legal advice**. Verify important information against official sources and
> consult a qualified lawyer before making consequential legal decisions.

---

## 1. Project overview

Everyday citizens, students, legal-aid teams and small law firms struggle with
lengthy court judgments, statutes and government PDFs scattered across
inaccessible portals. Legal Buddy turns a natural-language question into an
**evidence-backed research result**: retrieved sources with original URLs and
fetch timestamps, a grounded plain-language summary, structured entity and
relationship data, and a filterable graph where every edge links back to the
excerpt that supports it.

## 2. Problem & target users

| Who | Pain today |
|---|---|
| Citizens (tenancy, consumer, civic issues) | Legal text is dense, scattered and unsearchable |
| Law students & researchers | Manual citation-hunting across portals |
| Legal-aid organizations | Too many people, too little triage time |
| Small law firms | Fast first-pass research without a research clerk |

Initial target market: **India** (jurisdiction-aware retrieval, official-domain
prioritisation), extensible to other jurisdictions.

## 3. Main features

- 🔍 **Live discovery** — TinyFish Search over official/judicial domains
- 📄 **Real retrieval** — TinyFish Fetch of pages and supported PDFs as AI-ready
  Markdown, with per-source `success | failed | skipped | pending` status
- ✍️ **Grounded analysis** — 2-sentence summary, takeaways, provisions,
  limitations and next steps, each carrying validated `source_ids`
- 🗺️ **Relationship graph** — React Flow nodes for CASE / COURT / LAW /
  PROVISION / PERSON / PARTY / AUTHORITY / LOCATION / LEGAL_CONCEPT / DATE with
  labelled directional edges, confidence labels, filters, search, JSON/PNG export
- 🧾 **Document analysis** — PDF upload (validated, in-memory) with clear
  `user_uploaded` provenance, never claimed as TinyFish-fetched
- 📚 **Research history** — reopen sessions, delete sessions, 30-day retention
- 📈 **Usage & cost visibility** — per-session search/fetch counters at
  `/api/usage/summary`

## 4. Architecture

```mermaid
flowchart TD
    A[User question] --> B[FastAPI backend]
    B --> C[TinyFish Search API]
    C --> D[Official & relevant legal sources]
    D --> E[TinyFish Fetch API]
    E --> F[Retrieved Markdown & document content]
    F --> G[Gemini analysis]
    G --> H[Validated summary + entities + relationships]
    H --> I[React Flow graph]
    I --> J[Evidence-backed research workspace]

    B --> S[(SQLite / repository layer)]
    B -. honest errors .-> K[/api/research/{id}/stream SSE status/]
```

Repo layout:

```text
legal-buddy/
  frontend/         Next.js App Router app, components, lib, types, tests
  backend/          FastAPI app (api, core, models, schemas, services, repositories) + tests
  docs/             architecture.md, tinyfish-integration.md, demo-script.md
  .env.example      all environment variables, documented
```

## 5. Technology stack

- **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS,
  lucide-react icons, React Flow (@xyflow/react), Recharts available, Vitest +
  Testing Library.
- **Backend:** Python 3.11, FastAPI, Pydantic v2, httpx, SQLAlchemy 2 (SQLite →
  PostgreSQL-ready), pypdf, google-genai SDK, pytest + pytest-asyncio.
- **AI:** Google Gemini (`GEMINI_MODEL`, default `gemini-2.5-flash`).
- **Live web:** TinyFish Search + Fetch.

## 6. Exact role of TinyFish Search

`backend/app/services/tinyfish_client.py → TinyFishClient.search_legal_sources()`

Builds a focused query from the question + jurisdiction + topic, calls the live
Search API with the configured endpoint and `X-API-Key`, then normalizes,
deduplicates (URL-normalized) and authority-scores results. Official-domain
preferences (`gov.in`, `nic.in`, `indiacode.nic.in`, `legislative.gov.in`,
`sci.gov.in`, `ecourts.gov.in`, High Courts) are **search guidance only** —
never presented as a legal-authority ranking. The executed query, result count
and timestamp are persisted on the session (`search_step`).

## 7. Exact role of TinyFish Fetch

`TinyFishClient.fetch_source / fetch_multiple_sources`

Selects the top-N (configurable, max 10 per request) results by authority score
and retrieves their real content through the Fetch API (POST `{"url":...}` with
GET `?url=` 405-fallback). Each source keeps: original URL, retrieval timestamp,
provider metadata, normalized Markdown, keyword-window excerpts, and an honest
fetch status/error. SSRF guard (`validate_public_url`) runs before any request —
localhost, private ranges and metadata endpoints are blocked without touching
the network. Failed/blocked sources are shown as failed, never hidden.

## 8. Flow: retrieved content → Gemini

Fetched Markdown is sliced to `GEMINI_MAX_EXCERPT_CHARS` per source and wrapped
in `===== EVIDENCE source_N =====` blocks with title/URL/type/date headers. A
separate system instruction declares retrieved text **untrusted data** (ignore
embedded instructions) and demands strict JSON schema compliance. The response
is validated with Pydantic; `source_ids`/`source_id` references that don't match
actually-fetched sources are **dropped**; `OVERRULES`/`DISTINGUISHES` without
explicit evidence are **downgraded** to `RELATED_TO`/`uncertain`.

## 9. Entities & relationships → React Flow graph

`build_graph(analysis)` is a pure function: entities → nodes (type, description,
`source_ids`, linked-evidence confidence), relationships → directed edges with
label, excerpt, confidence and `confidence_label`. The frontend
`RelationshipGraph` component maps these to React Flow nodes/edges, provides
type filters, search, connected-only focus, node/edge detail panels (excerpt +
source link), and JSON/PNG export. Clicking an edge always shows its supporting
excerpt and fetched source link, or an explicit "could not verify" when the
source is missing.

## 10. Environment setup

```bash
git clone <your-repo-url> legal-buddy && cd legal-buddy

# Backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend (new terminal)
cd frontend
npm install
```

Copy `.env.example` → `backend/.env` and fill in credentials (section 11–12).
Frontend: `frontend/.env.local` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

## 11. TinyFish API configuration

1. Create an API key in your TinyFish dashboard (agent.tinyfish.ai → API keys).
2. Set in `backend/.env`:
   ```dotenv
   TINYFISH_API_KEY=...
   TINYFISH_SEARCH_ENDPOINT=https://api.search.tinyfish.ai
   TINYFISH_FETCH_ENDPOINT=https://api.fetch.tinyfish.ai
   ```
3. Endpoint variables exist so you can correct them from the official
   docs/dashboard without code changes — verify exact hosts/payloads against
   the provider's official documentation before deploying. Detailed
   request/response handling and troubleshooting: [`docs/tinyfish-integration.md`](docs/tinyfish-integration.md).
4. Verify: `curl http://localhost:8000/health` → `tinyfish_search.configured: true`.

## 12. Gemini API configuration

```dotenv
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_EXCERPT_CHARS=9000
```

Keys stay **backend-only** — never in frontend env vars, JS bundles, Git or
API responses.

## 13. Local development

```bash
# Terminal 1 — backend (http://localhost:8000)
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:3000)
cd frontend && npm run dev
```

Open <http://localhost:3000>, go to **Research**, ask a question. The pipeline
shows live stages: preparing → TinyFish Search → selection → TinyFish Fetch →
Gemini → graph → complete. Interactive API docs at <http://localhost:8000/docs>.

## 14. Test commands

```bash
# Backend — mocked unit/API tests (no credentials needed)
cd backend && python -m pytest -m "not integration"

# Backend — live integration tests (opt-in, needs real keys)
cd backend && TINYFISH_API_KEY=... GEMINI_API_KEY=... python -m pytest -m integration

# Frontend — tests, typecheck, lint
cd frontend && npm test
cd frontend && npm run typecheck
cd frontend && npm run lint

# Production build
cd frontend && npm run build
```

Coverage includes: TinyFish search/fetch normalization, missing credentials,
timeouts, rate limits, empty results, fetch failures, Gemini malformed JSON,
unknown source IDs, overrule-gating, graph generation, PDF validation, session
persistence, API error schemas, plus frontend submit/results/source/graph
interaction tests.

## 15. Deployment

**Frontend → Vercel**

- Root directory: `frontend`, build `npm run build`, Node 18+.
- Env: `NEXT_PUBLIC_API_BASE_URL=https://<your-backend>`.

**Backend → Render / Railway**

- Root: `backend`. Build: `pip install -r requirements.txt`.
  Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Env: `TINYFISH_API_KEY`, `GEMINI_API_KEY`, `FRONTEND_ORIGIN=https://<your-frontend>`,
  plus optional `DATABASE_URL` (add `psycopg[binary]` for Postgres).
- Health check path: `/health`.

No secrets are committed; `.env` is git-ignored. SQLite works for demos — use a
managed Postgres for durable data (repository layer already isolates this).

## 16. Responsible AI & legal disclaimers

- Never fabricates laws, citations, quotations or outcomes; unknown evidence →
  "could not verify" states.
- Retrieved documents are untrusted: prompt-injection scanning + strict
  system/source separation; no code execution by the model.
- Search ranking ≠ legal authority; currency of provisions is never asserted
  without supporting evidence.
- Binding vs persuasive authority labels only appear when supported.
- Uploads: type/size/magic-byte validation, in-memory processing, no retention.
- Rate limited, SSRF-guarded outbound fetch, CORS locked to `FRONTEND_ORIGIN`.
- Persistent disclaimer on every page and in every session payload.

## 17. Known limitations

- **Demo mode — no authentication.** Session IDs are not authorization; history
  is effectively public to anyone with the backend URL. Documented honestly in
  `/api/integrations/status` and the UI.
- TinyFish request/response schemas are configurable and normalization is
  deliberately tolerant, but **must be verified against the official docs** for
  the exact account/plan before a live demo; configured via endpoint env vars.
- Anti-bot-protected sites and scanned (image-only) PDFs fail honestly.
- SQLite is single-file; production should move to Postgres (env change only).
- Gemini usage/token counts aren't surfaced unless the SDK reports them; cost
  figures are configurable estimates, not invoices.
- Payments are not implemented — ₹999/month is labelled a **proposed** plan.
- Frontend graph PNG export depends on canvas availability (JSON export always works).

## 18. Proposed revenue model & cost assumptions

| | Citizen Free | Professional (proposed ₹999/mo) |
|---|---|---|
| Searches / day | 10 (env-configurable) | 100 |
| Fetches / day | 25 | 500 |
| Graph exports | JSON | JSON + PNG |
| History | 30 days | Extended + case organization (roadmap) |

Each session ≈ 1 Search call + ≤5 Fetch calls + 1 Gemini call over bounded
excerpts. Track real numbers at `/api/usage/summary` (searches, fetches,
analyzed sources, estimated USD). **Viability depends on actual TinyFish
pricing, Gemini token costs, average source counts, hosting and storage** — we
make no claim of verified profitability and publish no invented market stats.
Willingness-to-pay validation approach: 10–15 paid pilots with small Delhi/Mumbai
firms and legal-aid NGOs at ₹999, measuring sessions/month usage from the same
usage endpoint before firming up pricing.

## 19. Demo video instructions

Follow [`docs/demo-script.md`](docs/demo-script.md) — a reproducible 3-minute
script with exact clicks, timestamps, narration and a fallback plan for
credential/provider outages (labelled cached samples, never passed off as live).

## 20. Screenshots

<!-- Add GIFs/screenshots once the app is running with credentials:
     1) landing page, 2) dashboard + live pipeline, 3) results summary with
     source chips, 4) graph with edge excerpt panel, 5) history. -->

```text
docs/screenshots/landing.png
docs/screenshots/dashboard-pipeline.png
docs/screenshots/results-summary.png
docs/screenshots/graph-edge-evidence.png
```

---

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — services, stage machine, data model, security
- [`docs/tinyfish-integration.md`](docs/tinyfish-integration.md) — exact TinyFish usage & troubleshooting
- [`docs/demo-script.md`](docs/demo-script.md) — 3-minute hackathon demo

## Launch post (draft — GitHub/demo URLs on merge)

> 1 in 3 civic questions dies in a PDF nobody can parse. **Legal Buddy** turns
> "can my landlord evict me without notice?" into evidence-backed research:
> 📍TinyFish Search discovers live sources on real government/judicial domains →
> 📄TinyFish Fetch pulls the actual court orders & acts as AI-ready Markdown →
> ✨Gemini explains them in plain language with citations validated against the
> retrieved evidence (fabricated claims are dropped) → 🗺️React Flow maps how
> laws, provisions & courts connect — click any edge to read the excerpt behind
> it. Free for citizens, ₹999/mo proposed for firms. Not legal advice — a
> research compass. Repo: [TBD] · Demo: [TBD]

## License

Add your chosen license before publishing (MIT recommended).