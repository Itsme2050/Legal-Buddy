# Legal Buddy — Implementation & Optimization Plan

**Target:** Complete bug fixing, verification, and hackathon optimization across all 100 rubric points.  
**Branch:** `audit-and-fix`  

---

## 1. Objectives & Milestones

The goal is to eliminate all identified defects, ensure 100% test reliability, verify TinyFish and Gemini integration pathways, and prepare the project for judge demonstration.

---

## 2. Phase-by-Phase Execution Plan

### Step 1: Backend Core & Configuration Fixes (BUG-01, BUG-02, BUG-10)
1. **Fix `backend/requirements.txt`**:
   - Add `python-dotenv>=1.0.0`.
2. **Fix `backend/app/core/config.py`**:
   - Import `load_dotenv` from `dotenv`.
   - Call `load_dotenv()` looking at `backend/.env` and `.env` in root.
3. **Fix `backend/app/main.py`**:
   - Remove `StarletteHTTPExceptionLike` and replace with valid `HTTPException(status_code=429, detail=...)`.
4. **Fix `backend/pytest.ini`**:
   - Add `asyncio_default_fixture_loop_scope = function` to eliminate deprecation warnings.

### Step 2: Database Persistence & SSE Stream Fixes (BUG-03, BUG-05)
1. **Fix SSE Identity Caching in `backend/app/main.py`**:
   - In `research_stream()`, add `db.expire_all()` inside the polling loop before `repo.get(session_id)`.
2. **Fix Document Analysis Persistence**:
   - In `backend/app/main.py` -> `analyze_document`, persist the analyzed document using `repo.save_document(...)` so `DocumentRow` records are saved and retrievable.

### Step 3: TinyFish Integration & Client Resilience (BUG-07, BUG-08)
1. **Fix `backend/app/services/tinyfish_client.py`**:
   - Add `_ensure_client()` to safely initialize `self._client` if called outside an `async with` block.
   - Add `content_chars: int = 0` to `NormalizedFetchResult` to ensure consistent attribute access.
   - Support optional `session_id` in `ResearchRequest` to enable seamless SSE stream synchronization from frontend.

### Step 4: Frontend Fixes & Usability Optimization (BUG-04, BUG-09)
1. **Fix Graph Image Export in `frontend/components/graph/relationship-graph.tsx`**:
   - Replace the broken `.toDataURL()` on DOM div with a reliable SVG-to-canvas rendering function or clean image export handler.
2. **Fix Mobile Navigation in `frontend/components/site-header.tsx`**:
   - Add responsive mobile menu toggle and mobile links sheet for smooth tablet/mobile usage.
3. **Enhance Real-Time Stage Rendering in `frontend/app/dashboard/page.tsx`**:
   - Connect live SSE stream or dynamic progress updates while research is underway.

### Step 5: Documentation & Rubric Alignment (BUG-06)
1. **Fix `docs/tinyfish-integration.md`**:
   - Replace outdated file references (`tools_live_search.py`, `workflow_live_research.py`) with actual service modules (`app/services/tinyfish_client.py`, `app/services/research_workflow.py`).
2. **Verify & Update `README.md`**:
   - Confirm all endpoint examples, test commands, pricing breakdown, and architecture diagrams match actual implementations.
3. **Prepare Launch Post (Rubric C)**:
   - Provide the complete social media launch copy.
4. **Prepare Demo Presentation Guide (Phase 11)**:
   - Verify `docs/demo-script.md` for a 3-minute stage demo.

### Step 6: Full Verification & Automated Testing
1. Execute backend tests (`pytest`).
2. Execute frontend tests (`vitest`).
3. Run TypeScript typecheck (`tsc --noEmit`).
4. Run Next.js production build (`next build`).
5. Run linting (`npm run lint`).
6. Run live provider test script / verification check.
