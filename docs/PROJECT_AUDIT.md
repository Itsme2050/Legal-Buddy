# Legal Buddy — Comprehensive Project Audit

**Date:** 2026-10-22  
**Auditor:** Senior Full-Stack, AI, Security & QA Engineering Evaluation  
**Project:** Legal Buddy (AI-Powered Legal Research Platform)  
**Target Rubric:** Official 100-Point Hackathon Evaluation

---

## 1. Executive Summary & Framework Identification

Legal Buddy was inspected across the entire codebase to evaluate its architectural integrity, security posture, and readiness against the 100-point judging rubric.

- **Frontend Framework:** Next.js 14.2.21 (App Router), React 18.3.1, TypeScript 5.7.2, Tailwind CSS 3.4.17, React Flow (`@xyflow/react` 12.3.6), Lucide Icons, Vitest 2.1.8 with `@testing-library/react`.
- **Backend Framework:** FastAPI 0.115.6, Python 3.11.9, Pydantic v2 (2.10.4), SQLAlchemy 2.0.36 (SQLite dialect with repository isolation pattern), HTTPX 0.28.1, PyPDF 5.1.0, Google GenAI SDK (`google-genai` 0.8.0), Pytest 8.3.4 + pytest-asyncio 0.25.0.
- **AI & Data Discovery:** TinyFish Search API (live web discovery), TinyFish Fetch API (markdown/document retrieval), Google Gemini (`gemini-2.5-flash`).

### Baseline Verification (Before Changes)
- **Git State:** Not initialized initially; initialized and checkpointed on branch `initial-state`. Working branch: `audit-and-fix`.
- **Backend Pytest:** 65 passed, 3 skipped (live integration tests skipped because live API keys are not exported by default).
- **Frontend Typecheck (`tsc --noEmit`):** Passed with 0 errors.
- **Frontend Vitest:** 4 test files, 13 tests passed.
- **Frontend Build (`next build`):** Compiled successfully, all 8 App Router routes prerendered/configured.

---

## 2. Codebase Structure & Inspection Findings

### 2.1 Root Configuration
- `.env.example`: Present and clearly documented. Contains placeholders without leaked secrets.
- `.gitignore`: Ignores `.venv`, `__pycache__`, `.env`, `*.db`, `node_modules`, `.next`, `.coverage`.
- `README.md`: Very thorough documentation of project architecture, TinyFish integration, Gemini workflow, test commands, pricing model, and legal disclaimers.

### 2.2 Backend Inspection
- **`backend/app/core/config.py`**:
  - *Defect (Critical):* Reads environment variables strictly via `os.getenv(...)` without ever calling `load_dotenv()`. If a user or evaluator places `TINYFISH_API_KEY` or `GEMINI_API_KEY` in `backend/.env` or `.env` as documented, the backend completely fails to detect them unless manually exported in shell environment.
  - *Missing Dependency:* `python-dotenv` is installed in the local environment but missing from `backend/requirements.txt`.
- **`backend/app/main.py`**:
  - *Defect (Critical):* Line 95 references `raise StarletteHTTPExceptionLike`, which is an undefined identifier that will crash with `NameError` if `enforce_rate_limit` is called.
  - *Defect (High):* In `research_stream` (SSE endpoint), the polling loop queries `repo.get(session_id)`. Because the SQLAlchemy `Session` retains cached instances in its identity map, it never queries SQLite for updated status/stages committed by concurrent threads unless `db.expire_all()` is called.
  - *Defect (High):* `POST /api/documents/analyze` analyzes the uploaded PDF and builds graph/summary, but fails to call `repo.save_document(...)`. The `DocumentRow` table and persistence logic are never used.
  - *Enhancement (High):* `POST /api/research` blocks until all stages finish. Enabling client-supplied or early-generated `session_id` allows live progress streaming via the SSE `/stream` endpoint.
- **`backend/app/services/tinyfish_client.py`**:
  - *Defect (Medium):* If `TinyFishClient` is invoked outside an `async with` block, `self._client` remains `None` and raises `AttributeError: 'NoneType' object has no attribute 'get'`.
  - *Observation:* Robust normalization and SSRF validation logic (`validate_public_url`), handling URL deduplication and authority scoring.
- **`backend/app/services/gemini_client.py`**:
  - Structured output validated via Pydantic (`AnalysisResult`).
  - Strict evidence-guarding: unknown `source_ids` are pruned, unverified `OVERRULES` and `DISTINGUISHES` relationships are downgraded to `RELATED_TO` with `uncertain` confidence.
- **`backend/app/services/documents.py`**:
  - Strictly enforces PDF magic bytes `%PDF`, maximum upload byte size, and in-memory extraction using `pypdf`. Clearly sets provenance to `user_uploaded` (never spoofing TinyFish retrieval).

### 2.3 Frontend Inspection
- **`frontend/components/graph/relationship-graph.tsx`**:
  - *Defect (High):* The `exportImage` function queries `.react-flow__renderer`, casts it to `HTMLCanvasElement`, and calls `.toDataURL("image/png")`. React Flow renders SVG/HTML elements, not a `<canvas>`, causing a runtime TypeError and alerting an error every time.
- **`frontend/components/site-header.tsx`**:
  - *Polish / Usability (Medium):* Mobile navigation is minimalist and lacks a responsive toggle for mobile devices.
- **`frontend/lib/api.ts` & Dashboard**:
  - Supports strongly-typed API requests and parses structured backend errors.

### 2.4 Documentation Inspection
- **`docs/tinyfish-integration.md`**:
  - *Defect (High):* Documents legacy/hypothetical file names (`tools_live_search.py`, `tools_live_fetch.py`, `SearchFileContract`, `workflow_live_research.py`) that do not exist in the actual repository (`app/services/tinyfish_client.py`, `app/services/research_workflow.py`).

---

## 3. Prioritized Defects & Issue Matrix

| ID | Severity | Category | File | Description & Root Cause | Intended Fix |
|---|---|---|---|---|---|
| **BUG-01** | **Critical** | Backend / Config | `backend/app/core/config.py` & `requirements.txt` | Environment variables in `.env` / `backend/.env` are never loaded because `load_dotenv()` is never called. `python-dotenv` missing from `requirements.txt`. | Add `python-dotenv>=1.0.0` to `requirements.txt`. In `config.py`, invoke `load_dotenv` for root `.env` and `backend/.env`. |
| **BUG-02** | **Critical** | Backend / Syntax | `backend/app/main.py` | `enforce_rate_limit` raises undefined `StarletteHTTPExceptionLike`, causing a crash on execution. | Use `raise HTTPException(status_code=429, detail=...)` or delegate to `rate_limit()`. |
| **BUG-03** | **High** | Backend / Stream | `backend/app/main.py` | `/api/research/{session_id}/stream` SSE loop polls `repo.get(session_id)` on the same SQLAlchemy session without expiring identity map cache, so stage updates are never yielded. | Add `db.expire_all()` in the SSE generation loop prior to reading the row. |
| **BUG-04** | **High** | Frontend / Graph | `frontend/components/graph/relationship-graph.tsx` | PNG export casts a DOM `div` to `HTMLCanvasElement` and calls `toDataURL()`, failing with a TypeError every time. | Implement an SVG/canvas-based image renderer or handle export gracefully. |
| **BUG-05** | **High** | Backend / Docs | `backend/app/main.py` | `/api/documents/analyze` does not save the analyzed document to `SessionRepository`, leaving `DocumentRow` records orphaned. | Call `repo.save_document(...)` on successful extraction and analysis. |
| **BUG-06** | **High** | Documentation | `docs/tinyfish-integration.md` | Inaccurate file and contract references (`tools_live_search.py`, `workflow_live_research.py`). | Update `docs/tinyfish-integration.md` with exact filenames and interfaces. |
| **BUG-07** | **Medium** | Backend / TinyFish | `backend/app/services/tinyfish_client.py` | `TinyFishClient` crashes if called without context manager (`async with`) due to `self._client` being `None`. | Implement lazy `_ensure_client()` initialization in `TinyFishClient`. |
| **BUG-08** | **Medium** | Backend / Model | `backend/app/services/tinyfish_client.py` | Logging accesses `result.content_chars`, but `NormalizedFetchResult` lacks explicit `content_chars` property. | Add `content_chars: int = 0` to `NormalizedFetchResult`. |
| **BUG-09** | **Medium** | Frontend / Mobile | `frontend/components/site-header.tsx` | Mobile header links lack mobile dropdown/toggle, cramming navigation on small screens. | Add mobile menu toggle with responsive layout. |
| **BUG-10** | **Low** | Tests / CI | `backend/pytest.ini` | Deprecation warning regarding `asyncio_default_fixture_loop_scope`. | Set `asyncio_default_fixture_loop_scope = function` in `pytest.ini`. |

---

## 4. Security Audit

1. **API Key Isolation:** API keys (`TINYFISH_API_KEY`, `GEMINI_API_KEY`) are kept exclusively on the backend. The endpoint `/api/integrations/status` reports boolean flags (`configured: true|false`), never leaking keys.
2. **SSRF Guard:** `app/core/security.py` enforces scheme restrictions (`http`, `https`), rejects localhost, `.local`, Google metadata services, and blocks all RFC 1918/RFC 4193/loopback IPv4/IPv6 ranges before any HTTP request is dispatched.
3. **Prompt Injection Mitigation:** Untrusted web text and PDF content are segregated into distinct `===== EVIDENCE =====` blocks. The system instructions explicitly order the model to treat retrieved text as untrusted data and ignore embedded directives.
4. **CORS:** Restricts origins to configured `FRONTEND_ORIGIN` (defaulting to localhost/127.0.0.1:3000 in development).
5. **PDF Upload Sanitization:** File size bounded to `MAX_UPLOAD_BYTES` (10 MB), validates `%PDF` magic byte header, parses in-memory with PyPDF without writing executable files to disk.

---

## 5. Summary of Audit Conclusion

The application has a strong architectural foundation, rigorous schema modeling, and genuine evidence traceability logic. The primary defects preventing it from reaching maximum hackathon judging score are:
1. Environment variable loading failure (`.env` not loaded automatically).
2. Undefined symbol in `main.py`.
3. Identity map caching in SSE streaming.
4. Broken graph PNG export.
5. Inaccurate documentation references in `docs/tinyfish-integration.md`.
6. Missing persistence call in document analysis.

All defects are actionable and fixable within the existing codebase structure.
