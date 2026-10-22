# Legal Buddy — 3-Minute Demo Script

Reproducible judge demo. Prerequisites (run 10 minutes before going on stage):

```bash
# Terminal 1
cd backend && uvicorn app.main:app --port 8000
# Terminal 2
cd frontend && npm run dev
# Verify
curl http://localhost:8000/health   # expect integrations configured: true
```

Open <http://localhost:3000>. Keep <http://localhost:8000/docs> in a second tab
to show the raw API if asked.

**Backup plan:** if live credentials/provider fail mid-demo, say so out loud,
open **History** → show a previously saved session (labelled by its retrieval
timestamp), and walk the Summary → Sources → Graph tabs. Never claim the saved
session is a fresh live search.

---

## 0:00–0:20 — The problem

**Actions:** Land on the landing page. Scroll past the headline.

**Say:** "Try reading a Delhi High Court tenancy order or an Rent Control Act
notification as a normal person — it's nearly impossible. Legal information is
scattered across court websites, government PDFs and portals that weren't built
for citizens. Legal Buddy turns a plain-language question into evidence-backed
research you can audit."

## 0:20–0:45 — Submit a legal question

**Actions:** Click **Start Legal Research**. Click the first example prompt
("What protections may apply when a tenant faces eviction?"). Keep jurisdiction
= India, topic = Tenancy, source preference = Official sources first. Click
**Start Research**.

**Say:** "Real question, real jurisdiction. The dashboard says exactly what
will happen — and it will only claim success for steps that actually succeed."

## 0:45–1:15 — TinyFish Search (live)

**Actions:** As the pipeline runs, narrate the stage list: *Preparing →
Searching live sources with TinyFish → Selecting relevant documents*. When
done, open the session (auto-redirect to results). Point at the "Activity"
card: **query string + result count**.

**Say:** "That was a live TinyFish Search call — not cached, not hardcoded.
Our query adds the jurisdiction and official-domain hints
(gov.in, sci.gov.in, indiacode.nic.in). Here's the exact query we sent and the
number of real results returned."

## 1:15–1:40 — TinyFish Fetch

**Actions:** Go to the **Sources** tab. Point at the source count
("N/M fetched"), badges (Official/Court/Legislation, Fetched/Fetch failed),
the original URLs, retrieval timestamps. Expand one fetched source to show the
excerpt and full retrieved Markdown. Point at one failed source if present.

**Say:** "We selected the highest-authority results and pulled the actual
documents through TinyFish Fetch — court pages and government PDFs come back
as AI-ready Markdown with the original URL and retrieval time preserved. If a
site blocks us, we show 'Fetch failed' with the provider's error. We don't
hide failures and we never fabricate content."

## 1:40–2:05 — Gemini analysis (grounded)

**Actions:** Open the **Summary** tab. Read the two-sentence summary and one
key takeaway with its `source_N` chips. Expand **Provisions** and the
**Limitations / could-not-verify** box.

**Say:** "Gemini only saw the retrieved excerpts. Every takeaway carries the
source IDs it came from, validated against what we actually fetched — if the
model references a source we don't have, we drop the claim. And when evidence
is thin, we say 'could not verify' instead of guessing."

## 2:05–2:35 — Interactive relationship graph

**Actions:** Open the **Relationship graph** tab. Click a LAW node → show the
node panel with supporting source link. Click an edge → show the excerpt panel.
Toggle a filter (e.g. COURT off/on). Search a node. Mention solid-teal vs
dashed-amber edges. Export JSON (optional).

**Say:** "Cases, laws, provisions, courts and authorities — every edge opens
the exact excerpt that supports it, with a link to the fetched source. Solid
teal is direct evidence; dashed amber means uncertain, and we downgraded it
ourselves when the evidence was weak. Search ranking is not legal authority —
the graph is evidence, not vibes."

## 2:35–2:50 — Impact & revenue

**Actions:** Open **Pricing** briefly. Then the **History** tab.

**Say:** "Free tier for citizens with fair-use limits; a proposed ₹999/month
tier for small firms and legal-aid teams — limits are configurable because
they track real TinyFish and Gemini costs, visible per session in the usage
API. Sessions auto-expire and users can delete them. It's a research compass,
explicitly not a lawyer — the disclaimer is everywhere."

## 2:50–3:00 — Close

**Say:** "Legal Buddy: live discovery, real documents, grounded explanations,
and a relationship map where every claim is one click from its evidence.
**Understand the law. Know your rights. Take the next step.**"

---

## Q&A cheat sheet

- **"What if the AI invents a case?"** — Unknown source IDs are stripped;
  OVERRULES/DISTINGUISHES are downgraded without explicit textual evidence;
  unit tests cover all of it (`backend/tests/test_gemini_validation.py`).
- **"Is TinyFish really live?"** — Yes: Search → Fetch → analyze. Kill the
  `TINYFISH_API_KEY` env var and the app refuses to run rather than fake it
  (demonstrable via `/health`).
- **"Security?"** — SSRF-guarded fetch, in-memory PDFs, rate limiting, CORS
  lock, keys backend-only, prompt-injection scanning.
- **"Auth?"** — Honest limitation: demo mode, no auth. Session IDs are not a
  security boundary; documented in the README and the API status endpoint.
