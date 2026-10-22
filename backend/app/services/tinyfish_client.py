"""TinyFish Search + Fetch integration.

Request formats are configurable via environment variables. The defaults below
mirror TinyFish's documented conventions, but endpoint variables exist precisely
so the values can be corrected from the provider's official dashboard/docs
without code changes. Never invent undocumented fields: unknown response fields
are preserved in ``provider_metadata`` and surfaced as-is.

Search (default): GET {TINYFISH_SEARCH_ENDPOINT}?query=...&...  header X-API-Key
Fetch  (default): POST {TINYFISH_FETCH_ENDPOINT} {"url": ...}   header X-API-Key
                   or GET {TINYFISH_FETCH_ENDPOINT}?url=...     (fall back on 405)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.security import UnsafeURLException, validate_public_url
from app.schemas import FetchStatus, Source, SourceExcerpt, SourceType

logger = logging.getLogger("legal_buddy.tinyfish")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class TinyFishError(Exception):
    """Base class for TinyFish provider failures."""


class TinyFishConfigError(TinyFishError):
    """Missing credentials / endpoint — distinct so the UI can show setup help."""


class TinyFishAuthError(TinyFishError):
    """401/403 — invalid or revoked API key."""


class TinyFishRateLimitError(TinyFishError):
    """429 — provider rate limit."""


class TinyFishTimeoutError(TinyFishError):
    """Request exceeded configured timeout."""


class TinyFishProviderError(TinyFishError):
    """Other 4xx/5xx or malformed provider payload."""


class TinyFishEmptyResultError(TinyFishError):
    """Provider answered but returned zero results."""


# ---------------------------------------------------------------------------
# Normalized containers
# ---------------------------------------------------------------------------

@dataclass
class NormalizedSearchResult:
    title: str
    url: str
    snippet: Optional[str] = None
    rank: Optional[int] = None
    authority_score: float = 0.0
    source_type: SourceType = SourceType.UNKNOWN
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedFetchResult:
    url: str
    status: FetchStatus
    content_markdown: Optional[str] = None
    content_chars: int = 0
    title: Optional[str] = None
    fetched_at: Optional[datetime] = None
    error: Optional[str] = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pure normalization helpers (unit-testable, no I/O)
# ---------------------------------------------------------------------------

_OFFICIAL_HINTS = (
    "sci.gov.in",
    "ecourts.gov.in",
    "indiacode.nic.in",
    "legislative.gov.in",
    "gov.in",
    "nic.in",
    "nclt.gov.in",
    "highcourt",
    "judiciary",
    "kanoon.org",
)

_COURT_HINTS = ("court", "tribunal", "sci.gov.in", "highcourt", "nclt", "kanoon")
_LEGIS_HINTS = ("act", "bill", "code", "rule", "regulation", "notification", "section", "statute")
_NEWS_HINTS = (
    "timesofindia",
    "hindustantimes",
    "ndtv",
    "news",
    "express",
    "journal",
    "blog",
)


def classify_source(title: str, url: str) -> SourceType:
    blob = f"{title} {url}".lower()
    host = (urlparse(url).hostname or "").lower()
    if any(h in host for h in ("sci.gov.in", "highcourt", "ecourts", "nclt", "kanoon.org")):
        return SourceType.COURT
    if any(h in host for h in ("indiacode.nic.in", "legislative.gov.in")):
        return SourceType.LEGISLATION
    if host.endswith(".gov.in") or host.endswith(".nic.in") or host.endswith("gov.uk"):
        return SourceType.OFFICIAL
    if any(n in host for n in _NEWS_HINTS):
        return SourceType.NEWS
    if any(k in host for k in (".edu", ".ac.in")):
        return SourceType.ACADEMIC
    return SourceType.UNKNOWN


def officialness_score(url: str, official_domains: Iterable[str] | None = None) -> float:
    """0..1 heuristic. Search ranking ≠ legal authority — this only orders fetches."""
    host = (urlparse(url).hostname or "").lower()
    domains = tuple(official_domains or get_settings().official_domains)
    if not host:
        return 0.0
    score = 0.0
    for d in domains:
        d = d.lower()
        if host == d or host.endswith("." + d):
            score = max(score, 0.5 + min(0.5, len(d) / 40))
    if host.endswith(".gov.in") or host.endswith(".nic.in"):
        score = max(score, 0.95)
    if "kanoon.org" in host:
        score = max(score, 0.75)
    if "pdf" in url.lower():
        score = min(1.0, score + 0.03)
    return round(score, 3)


def normalize_search_results(payload: Any, query: str = "") -> list[NormalizedSearchResult]:
    """Normalize a TinyFish Search response into a common structure.

    Tolerant of shape variance: accepts ``{results: [...]}``, ``{data: [...]}```
    or a bare list. Duplicates (same normalized URL) are removed; ranking order
    from the provider is preserved as ``rank``.
    """
    if payload is None:
        return []
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = (
            payload.get("results")
            or payload.get("data")
            or payload.get("items")
            or payload.get("sources")
            or []
        )
    else:
        raise TinyFishProviderError(f"Unexpected search payload type: {type(payload).__name__}")

    out: list[NormalizedSearchResult] = []
    seen: set[str] = set()
    settings = get_settings()

    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        url = (
            item.get("url")
            or item.get("link")
            or item.get("href")
            or item.get("source_url")
            or ""
        ).strip()
        if not url or not url.startswith(("http://", "https://")):
            continue
        norm = _normalize_url_for_dedup(url)
        if norm in seen:
            continue
        seen.add(norm)
        title = (
            item.get("title")
            or item.get("name")
            or item.get("headline")
            or url
        ).strip()
        snippet = (
            item.get("snippet")
            or item.get("description")
            or item.get("summary")
            or item.get("content")
            or None
        )
        reserved = {
            "url", "link", "href", "source_url", "title", "name", "headline",
            "snippet", "description", "summary", "content",
        }
        meta = {k: v for k, v in item.items() if k not in reserved}
        out.append(
            NormalizedSearchResult(
                title=title,
                url=url,
                snippet=str(snippet) if snippet else None,
                rank=item.get("position") or item.get("rank") or (idx + 1),
                authority_score=officialness_score(url, settings.official_domains),
                source_type=classify_source(title, url),
                provider_metadata=meta,
            )
        )
    return out


def _normalize_url_for_dedup(url: str) -> str:
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/")
    return f"{host}{path}".lower()


def normalize_fetch_result(url: str, payload: Any) -> NormalizedFetchResult:
    """Normalize a TinyFish Fetch response."""
    now = datetime.now(timezone.utc)
    if payload is None:
        return NormalizedFetchResult(url=url, status=FetchStatus.FAILED, error="Empty provider response", fetched_at=now)
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return NormalizedFetchResult(url=url, status=FetchStatus.FAILED, error="Fetch returned empty content", fetched_at=now)
        return NormalizedFetchResult(
            url=url,
            status=FetchStatus.SUCCESS,
            content_markdown=text,
            content_chars=len(text),
            fetched_at=now,
            provider_metadata={"shape": "plain_text"},
        )
    if not isinstance(payload, dict):
        return NormalizedFetchResult(url=url, status=FetchStatus.FAILED, error="Unexpected fetch payload shape", fetched_at=now)

    # Nested envelopes or batch responses from TinyFish
    if isinstance(payload.get("results"), list) and payload["results"]:
        match = next(
            (item for item in payload["results"] if isinstance(item, dict) and (item.get("url") == url or item.get("final_url") == url)),
            payload["results"][0],
        )
        body = match if isinstance(match, dict) else payload
    elif isinstance(payload.get("errors"), list) and payload["errors"]:
        err_match = next(
            (item for item in payload["errors"] if isinstance(item, dict) and item.get("url") == url),
            payload["errors"][0] if isinstance(payload["errors"][0], dict) else None,
        )
        if err_match:
            return NormalizedFetchResult(
                url=url,
                status=FetchStatus.FAILED,
                error=str(err_match.get("error") or err_match.get("message") or "Provider fetch error"),
                fetched_at=now,
                provider_metadata=_safe_meta(payload),
            )
        body = payload
    else:
        inner = payload.get("data") if isinstance(payload.get("data"), dict) else None
        body = inner or payload

    content = (
        body.get("markdown")
        or body.get("content_markdown")
        or body.get("text")
        or body.get("html_text")
        or body.get("page_content")
        or body.get("content")
        or ""
    )
    if isinstance(content, dict):
        content = content.get("text") or content.get("markdown") or ""
    content = str(content).strip()

    status_raw = str(body.get("status") or body.get("fetch_status") or "").lower()
    provider_error = body.get("error") or body.get("message")

    if not content:
        return NormalizedFetchResult(
            url=url,
            status=FetchStatus.FAILED,
            error=str(provider_error or status_raw or "No content returned by provider"),
            fetched_at=now,
            provider_metadata=_safe_meta(payload),
        )

    title = body.get("title") or body.get("name") or None
    reserved = {
        "markdown", "content_markdown", "text", "html_text", "page_content",
        "content", "title", "name", "status", "fetch_status", "error", "message",
    }
    meta = {k: v for k, v in payload.items() if k not in reserved}
    return NormalizedFetchResult(
        url=url,
        status=FetchStatus.SUCCESS,
        content_markdown=content,
        content_chars=len(content),
        title=str(title) if title else None,
        fetched_at=now,
        provider_metadata=meta,
    )


def _safe_meta(payload: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in payload.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)[:200]
    return out


def extract_relevant_excerpts(
    text: str, keywords: list[str], max_excerpts: int = 3, window: int = 320
) -> list[SourceExcerpt]:
    """Pull evidence windows around keyword hits (deterministic, no AI)."""
    if not text:
        return []
    lowered = text.lower()
    hits: list[tuple[int, str]] = []
    for kw in keywords:
        kw = kw.strip().lower()
        if len(kw) < 3:
            continue
        start = 0
        while True:
            i = lowered.find(kw, start)
            if i == -1:
                break
            hits.append((i, kw))
            start = i + len(kw)
    hits.sort()
    excerpts: list[SourceExcerpt] = []
    taken: list[tuple[int, int]] = []
    for pos, _kw in hits:
        if len(excerpts) >= max_excerpts:
            break
        s = max(0, pos - window // 2)
        e = min(len(text), pos + window)
        if any(not (e < a or s > b) for a, b in taken):
            continue
        taken.append((s, e))
        snippet = text[s:e].strip()
        if s > 0:
            snippet = "…" + snippet
        if e < len(text):
            snippet = snippet + "…"
        excerpts.append(
            SourceExcerpt(text=snippet, url="", char_start=s, char_end=e, note="keyword-window")
        )
    if not excerpts and text:
        head = text[: min(400, len(text))].strip()
        excerpts.append(
            SourceExcerpt(
                text=head + ("…" if len(text) > 400 else ""),
                url="",
                char_start=0,
                char_end=min(400, len(text)),
                note="opening-passage",
            )
        )
    return excerpts


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class TinyFishClient:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.settings = get_settings()
        self._client = client
        self._owns_client = client is None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.tinyfish_timeout_seconds),
                follow_redirects=True,
            )
        return self._client

    async def __aenter__(self) -> "TinyFishClient":
        self._ensure_client()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require_credentials(self) -> str:
        if not self.settings.tinyfish_api_key:
            raise TinyFishConfigError(
                "TINYFISH_API_KEY is not configured. Add it to backend/.env "
                "(see .env.example) and restart the server. No simulated results "
                "will be returned."
            )
        return self.settings.tinyfish_api_key

    @property
    def configured(self) -> bool:
        return bool(self.settings.tinyfish_api_key)

    # ----- Search --------------------------------------------------------
    async def search_legal_sources(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[NormalizedSearchResult]:
        """Run a live TinyFish Search and return normalized results."""
        key = self._require_credentials()
        settings = self.settings
        params: dict[str, Any] = {"query": query}
        if jurisdiction:
            params["location"] = jurisdiction
        if filters:
            for k, v in filters.items():
                if v is not None:
                    params[k] = v
        headers = {"X-API-Key": key, "Accept": "application/json"}

        start = time.monotonic()
        client = self._ensure_client()
        try:
            resp = await client.get(settings.tinyfish_search_endpoint, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise TinyFishTimeoutError(f"TinyFish Search timed out after {settings.tinyfish_timeout_seconds}s") from exc
        except httpx.HTTPError as exc:
            raise TinyFishProviderError(f"TinyFish Search network error: {exc}") from exc

        self._raise_for_status(resp, "Search")

        try:
            payload = resp.json()
        except ValueError as exc:
            raise TinyFishProviderError("TinyFish Search returned non-JSON payload") from exc

        results = normalize_search_results(payload, query=query)
        logger.info(
            "tinyfish_search query=%r jurisdiction=%r results=%d elapsed=%.2fs",
            query, jurisdiction, len(results), time.monotonic() - start,
        )
        if not results:
            raise TinyFishEmptyResultError(
                "TinyFish Search responded successfully but returned zero results for this query."
            )
        return results

    # ----- Fetch ---------------------------------------------------------
    async def fetch_source(self, url: str) -> NormalizedFetchResult:
        """Fetch a single URL through TinyFish Fetch (SSRF-validated first)."""
        key = self._require_credentials()
        settings = self.settings

        try:
            validate_public_url(url)
        except UnsafeURLException as exc:
            return NormalizedFetchResult(
                url=url, status=FetchStatus.SKIPPED, error=f"Blocked unsafe URL: {exc}"
            )

        headers = {"X-API-Key": key, "Accept": "application/json"}
        client = self._ensure_client()
        try:
            resp = await client.post(
                settings.tinyfish_fetch_endpoint, json={"urls": [url], "url": url}, headers=headers
            )
            if resp.status_code == 405:
                # Some deployments expose fetch as GET ?url=
                resp = await client.get(
                    settings.tinyfish_fetch_endpoint, params={"url": url}, headers=headers
                )
        except httpx.TimeoutException:
            return NormalizedFetchResult(
                url=url,
                status=FetchStatus.FAILED,
                error=f"Fetch timed out after {settings.tinyfish_timeout_seconds}s",
            )
        except httpx.HTTPError as exc:
            return NormalizedFetchResult(
                url=url, status=FetchStatus.FAILED, error=f"Fetch network error: {exc}"
            )

        if resp.status_code in (401, 403):
            return NormalizedFetchResult(
                url=url, status=FetchStatus.FAILED,
                error="TinyFish Fetch rejected credentials (401/403).",
            )
        if resp.status_code == 429:
            return NormalizedFetchResult(
                url=url, status=FetchStatus.FAILED,
                error="TinyFish Fetch rate-limited the request (429).",
            )
        if resp.status_code >= 400:
            return NormalizedFetchResult(
                url=url, status=FetchStatus.FAILED,
                error=f"TinyFish Fetch returned HTTP {resp.status_code} for this URL.",
            )

        try:
            payload = resp.json()
        except ValueError:
            payload = resp.text

        result = normalize_fetch_result(url, payload)
        logger.info(
            "tinyfish_fetch url=%s status=%s chars=%s",
            url, result.status.value, result.content_chars if hasattr(result, "content_chars") else None,
        )
        return result

    async def fetch_multiple_sources(
        self, urls: list[str], max_concurrency: int = 4
    ) -> list[NormalizedFetchResult]:
        """Fetch multiple URLs efficiently using TinyFish's native batch API."""
        urls = urls[: self.settings.tinyfish_max_fetch_urls]
        if not urls:
            return []

        key = self._require_credentials()
        headers = {"X-API-Key": key, "Accept": "application/json"}
        client = self._ensure_client()
        out_map: dict[str, NormalizedFetchResult] = {}
        valid_urls: list[str] = []

        for u in urls:
            try:
                validate_public_url(u)
                valid_urls.append(u)
            except UnsafeURLException as exc:
                out_map[u] = NormalizedFetchResult(
                    url=u, status=FetchStatus.SKIPPED, error=f"Blocked unsafe URL: {exc}"
                )

        if valid_urls:
            try:
                # Use a responsive timeout for the batch call
                batch_timeout = min(self.settings.tinyfish_timeout_seconds, 25.0)
                resp = await client.post(
                    self.settings.tinyfish_fetch_endpoint,
                    json={"urls": valid_urls},
                    headers=headers,
                    timeout=httpx.Timeout(batch_timeout),
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    results_list = payload.get("results", [])
                    results_by_url = {item.get("url"): item for item in results_list if isinstance(item, dict)}
                    results_by_final = {item.get("final_url"): item for item in results_list if isinstance(item, dict)}

                    errors_list = payload.get("errors", [])
                    errors_by_url = {item.get("url"): item.get("error") for item in errors_list if isinstance(item, dict)}

                    for u in valid_urls:
                        item = results_by_url.get(u) or results_by_final.get(u)
                        if item:
                            out_map[u] = normalize_fetch_result(u, item)
                        elif u in errors_by_url:
                            out_map[u] = NormalizedFetchResult(
                                url=u, status=FetchStatus.FAILED, error=str(errors_by_url[u])
                            )
                        else:
                            out_map[u] = NormalizedFetchResult(
                                url=u, status=FetchStatus.FAILED, error="No content returned by provider"
                            )
                else:
                    # Fallback to individual fetches with bounded concurrency
                    sem = asyncio.Semaphore(max_concurrency)
                    async def _one(u: str) -> NormalizedFetchResult:
                        async with sem:
                            return await self.fetch_source(u)
                    fallback_results = await asyncio.gather(*[_one(u) for u in valid_urls])
                    for r in fallback_results:
                        out_map[r.url] = r
            except Exception as exc:
                logger.warning("Batch fetch failed (%s); falling back to individual fetches", exc)
                sem = asyncio.Semaphore(max_concurrency)
                async def _one(u: str) -> NormalizedFetchResult:
                    async with sem:
                        return await self.fetch_source(u)
                fallback_results = await asyncio.gather(*[_one(u) for u in valid_urls])
                for r in fallback_results:
                    out_map[r.url] = r

        return [out_map.get(u) or NormalizedFetchResult(url=u, status=FetchStatus.FAILED, error="Fetch failed") for u in urls]

    # ----- helpers -------------------------------------------------------
    @staticmethod
    def _raise_for_status(resp: httpx.Response, op: str) -> None:
        if resp.status_code in (401, 403):
            raise TinyFishAuthError(
                f"TinyFish {op} authentication failed (HTTP {resp.status_code}). Check TINYFISH_API_KEY."
            )
        if resp.status_code == 429:
            raise TinyFishRateLimitError(f"TinyFish {op} rate limited (HTTP 429). Retry later.")
        if resp.status_code >= 400:
            body = resp.text[:300]
            raise TinyFishProviderError(f"TinyFish {op} returned HTTP {resp.status_code}: {body}")


def rank_for_fetch(
    results: list[NormalizedSearchResult], limit: int, prefer_official: bool = True
) -> list[NormalizedSearchResult]:
    """Deduplicated, authority-weighted selection with domain diversity."""
    ordered = sorted(
        results,
        key=lambda r: (
            (-r.authority_score if prefer_official else 0),
            r.rank or 9999,
        ),
    )
    selected: list[NormalizedSearchResult] = []
    domain_counts: dict[str, int] = {}

    for r in ordered:
        domain = (urlparse(r.url).hostname or "").lower()
        if domain_counts.get(domain, 0) < 2:
            selected.append(r)
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            if len(selected) >= limit:
                break

    if len(selected) < limit:
        for r in ordered:
            if r not in selected:
                selected.append(r)
                if len(selected) >= limit:
                    break

    return selected[:limit]

# Re-export used by workflow for source construction
__all__ = [
    "NormalizedSearchResult",
    "NormalizedFetchResult",
    "TinyFishClient",
    "TinyFishError",
    "TinyFishConfigError",
    "TinyFishAuthError",
    "TinyFishRateLimitError",
    "TinyFishTimeoutError",
    "TinyFishProviderError",
    "TinyFishEmptyResultError",
    "normalize_search_results",
    "normalize_fetch_result",
    "extract_relevant_excerpts",
    "classify_source",
    "officialness_score",
    "rank_for_fetch",
]