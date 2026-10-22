# TinyFish integration in Legal Buddy

TinyFish is the **only** live-web retrieval path. Nothing is simulated,
hardcoded, or silently substituted.

## Where TinyFish is used

| Step | Code | Method |
|---|---|---|
| Live discovery | `SearchLiveSource` tool (`tools_live_search.py`) | TinyFish **Search API** |
| Content retrieval | `FetchDocumentation` tool (`tools_live_fetch.py`) | TinyFish **Fetch API** |
| Result normalization | `SearchFileContract`, `FetchFileContract` | Pure functions |
| Workflow orchestration | `workflow_live_research.py` | Calls both tools in order |

## Search request shape

Endpoint, key header, query params (`query`, `purpose`, `location`, `language`,
`include_domains`, `exclude_domains`, `recency_minutes`, `after_date`,
`before_date`, `page`) and response parsing (`results[].{url,title,snippet,position}`)
are all configurable in blocks 3 and 6. Endpoint variables exist so the values
can be corrected from the official docs/dashboard without code changes.

## Fetch request shape

Default: `POST {TINYFISH_FETCH_ENDPOINT}` with `{"url": ...}` and `X-API-Key`
header; falls back to `GET ?url=` on 405 (block 7). Handles string bodies,
`{markdown|text|content|html_text}` fields and nested `{data: {...}}` envelopes.
405-fallback and 4xx mapping are in block 8.

## Normalization & ranking (blocks 4–5)

- URL-normalized dedup (www, trailing slash, case)
- `officialness_score()` prefers `*.gov.in`, `*.nic.in`, courts, India Code
- `classify_source()` → `court | legislation | official | academic | news | unknown`
- `rank_for_fetch()` selects top-N by authority before fetching

## Honest failure modes

| Condition | Error / status |
|---|---|
| Missing `TINYFISH_API_KEY` | `TinyFishConfigError` → session `failed`, UI setup message |
| 401/403 | `TinyFishAuthError` |
| 429 | `TinyFishRateLimitError` |
| Timeout | `TinyFishTimeoutError` |
| 200 but zero results | `TinyFishEmptyResultError` |
| Fetch 4xx/5xx/timeout | per-source `fetch_status: failed` + provider message |
| All fetches failed | session fails with concatenated provider errors |

## Evidence flow into Gemini (blocks 17–19)

Fetched markdown is sliced to `GEMINI_MAX_EXCERPT_CHARS` per source and wrapped
in `===== EVIDENCE source_N =====` blocks with URL/type/date headers. The system
instruction (block 19) is separate and tells the model retrieved text is
untrusted. Unknown `source_ids` in the response are stripped; `OVERRULES` and
`DISTINGUISHES` are downgraded unless the excerpt is explicit.

## Configuration troubleshooting

1. `curl`-check `/health` — shows `configured: true/false` per provider.
2. Confirm the key is present in `backend/.env` and the server was restarted.
3. 401 → key invalid/revoked. 429 → back off (rate limits are provider-side).
4. Zero results → simplify the query, or set `source_preference: broad` to drop
   `include_domains` hints.
5. All fetches failed → the sources are likely bot-protected; this is surfaced
   per-source, not hidden. Try a different question with more accessible sources.
6. Never fabricate: if live retrieval fails, the app shows the error — it does
   not generate a canned answer.