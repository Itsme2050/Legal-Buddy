"""Error-handling tests for the TinyFish client using a mocked HTTP transport."""

from __future__ import annotations

import httpx
import pytest

from app.services.tinyfish_client import (
    TinyFishAuthError,
    TinyFishClient,
    TinyFishConfigError,
    TinyFishEmptyResultError,
    TinyFishRateLimitError,
    TinyFishTimeoutError,
)


def _client(handler, api_key: str | None = "test-key") -> TinyFishClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    c = TinyFishClient(client=http)
    # Always assign explicitly: settings is a shared singleton, so a test
    # that nulls the key must not leak that into later tests.
    c.settings.tinyfish_api_key = api_key
    return c


def test_missing_credentials_raises_config_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    c = _client(handler, api_key=None)
    with pytest.raises(TinyFishConfigError) as ei:
        c._require_credentials()
    assert "TINYFISH_API_KEY" in str(ei.value)


@pytest.mark.asyncio
async def test_search_timeout_maps_to_tinyfish_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("boom", request=request)

    async with _client(handler) as c:
        with pytest.raises(TinyFishTimeoutError) as ei:
            await c.search_legal_sources("q")
        assert "timed out" in str(ei.value)


@pytest.mark.asyncio
async def test_search_429_maps_to_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="slow down")

    async with _client(handler) as c:
        with pytest.raises(TinyFishRateLimitError):
            await c.search_legal_sources("q")


@pytest.mark.asyncio
async def test_search_401_maps_to_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad key")

    async with _client(handler) as c:
        with pytest.raises(TinyFishAuthError) as ei:
            await c.search_legal_sources("q")
        assert "TINYFISH_API_KEY" in str(ei.value)


@pytest.mark.asyncio
async def test_search_empty_results_maps_to_empty_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    async with _client(handler) as c:
        with pytest.raises(TinyFishEmptyResultError) as ei:
            await c.search_legal_sources("obscure query")
        assert "zero results" in str(ei.value)


@pytest.mark.asyncio
async def test_search_success_sends_api_key_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get("X-API-Key")
        seen["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"results": [{"url": "https://gov.in/x", "title": "X", "snippet": "s"}]},
        )

    async with _client(handler) as c:
        results = await c.search_legal_sources("tenant law", jurisdiction="India")
        assert len(results) == 1
        assert seen["key"] == "test-key"
        assert "query=" in seen["url"]


@pytest.mark.asyncio
async def test_fetch_blocked_private_url_is_skipped_without_network():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"markdown": "hi"})

    async with _client(handler) as c:
        r = await c.fetch_source("http://169.254.169.254/latest/meta-data")
        assert r.status.value == "skipped"
        assert "unsafe" in (r.error or "").lower()
        assert calls["n"] == 0  # no network call was made


@pytest.mark.asyncio
async def test_fetch_http_error_returns_failed_result():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    async with _client(handler) as c:
        r = await c.fetch_source("https://gov.in/page")
        assert r.status.value == "failed"
        assert "HTTP 500" in (r.error or "")


@pytest.mark.asyncio
async def test_fetch_success_normalizes_content():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"markdown": "# ok", "title": "Page"})
        return httpx.Response(405)

    async with _client(handler) as c:
        r = await c.fetch_source("https://gov.in/page")
        assert r.status.value == "success"
        assert r.content_markdown == "# ok"


@pytest.mark.asyncio
async def test_fetch_multiple_respects_batch_limit():
    urls = [f"https://gov.in/p{i}" for i in range(20)]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"markdown": "x"})

    async with _client(handler) as c:
        results = await c.fetch_multiple_sources(urls)
        assert len(results) == c.settings.tinyfish_max_fetch_urls