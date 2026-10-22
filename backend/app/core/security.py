"""Security helpers: SSRF-safe URL validation, prompt-injection guard, rate limiter, error schema, CORS."""

from __future__ import annotations

import ipaddress
import re
import time
from collections import defaultdict, deque
from typing import Any
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# SSRF-safe URL validation
# ---------------------------------------------------------------------------

_ALLOWED_SCHEMES = {"http", "https"}

# Patterns that must never be fetched server-side.
_BLOCKED_HOST_PATTERNS = (
    re.compile(r"^localhost$", re.I),
    re.compile(r"\.localhost$", re.I),
    re.compile(r"\.local$", re.I),
    re.compile(r"^metadata\.google\.internal$", re.I),
    re.compile(r"^metadata\.internal$", re.I),
)

_PRIVATE_NETWORKS = [
    ipaddress.IPv4Network("0.0.0.0/8"),
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("100.64.0.0/10"),
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.0.0.0/24"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("198.18.0.0/15"),
    ipaddress.IPv4Network("224.0.0.0/4"),
    ipaddress.IPv4Network("240.0.0.0/4"),
]

_PRIVATE_NETWORKS_V6 = [
    ipaddress.IPv6Network("::1/128"),
    ipaddress.IPv6Network("::/128"),
    ipaddress.IPv6Network("fc00::/7"),
    ipaddress.IPv6Network("fe80::/10"),
    ipaddress.IPv6Network("ff00::/8"),
]


class UnsafeURLException(ValueError):
    """Raised when a URL could not be safely fetched server-side."""


def _host_is_blocked(host: str) -> bool:
    return any(p.search(host) for p in _BLOCKED_HOST_PATTERNS)


def _ip_is_private(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.version == 4:
        return any(ip in net for net in _PRIVATE_NETWORKS)
    return any(ip in net for net in _PRIVATE_NETWORKS_V6)


def validate_public_url(url: str, allowed_domains: tuple[str, ...] | None = None) -> str:
    """Validate that ``url`` is safe to fetch (scheme, host, no private ranges).

    Args:
        url: Candidate URL.
        allowed_domains: Optional allowlist of host suffixes. When provided, the
            URL's host must match one of them.

    Returns:
        The validated URL.

    Raises:
        UnsafeURLException: If the URL must not be fetched.
    """
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise UnsafeURLException(f"Malformed URL: {exc}") from exc

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeURLException(f"Dangerous/unsupported scheme: {parsed.scheme!r}")

    if not parsed.hostname:
        raise UnsafeURLException("URL has no hostname")

    host = parsed.hostname

    if _host_is_blocked(host):
        raise UnsafeURLException(f"Blocked host: {host}")

    if allowed_domains:
        if not any(host == d or host.endswith("." + d) for d in allowed_domains):
            raise UnsafeURLException(f"Host not in allowlist: {host}")

    # If host looks like an IP literal, reject private ranges.
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None and _ip_is_private(ip):
        raise UnsafeURLException(f"URL resolves to private address: {host}")

    return url


# ---------------------------------------------------------------------------
# Prompt-injection guard
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = (
    r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions",
    r"disregard\s+(?:all\s+|the\s+)?(?:previous|prior|system|instructions)",
    r"you\s+must\s+ignore\s+previous",
    r"system\s+prompt",
    r"developer\s+mode",
    r"jailbreak",
    r"pretend\s+you\s+are\s+not\s+(?:an?\s+)?ai",
    r"api\s*key\s*[:=]",
    r"secret\s*key\s*[:=]",
)

_INJECTION_RE = [re.compile(p, re.I) for p in _INJECTION_PATTERNS]


def scan_for_prompt_injection(text: str) -> list[str]:
    """Return a list of suspicious injection phrases found in ``text``.

    Retrieved web content and uploaded PDFs are treated as untrusted data.
    This scan is advisory: the model system-instruction is always separated
    from source text regardless of the result.
    """
    return [m.group(0) for pat in _INJECTION_RE for m in pat.finditer(text)]


# ---------------------------------------------------------------------------
# Rate limiting (simple sliding-window, in-process)
# ---------------------------------------------------------------------------

class RateLimiter:
    """Sliding-window per-key rate limiter."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        dq = self._hits[key]
        while dq and now - dq[0] > self.window:
            dq.popleft()
        if len(dq) >= self.limit:
            return False
        dq.append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        dq = self._hits[key]
        while dq and now - dq[0] > self.window:
            dq.popleft()
        return max(0, self.limit - len(dq))


# ---------------------------------------------------------------------------
# Error schema
# ---------------------------------------------------------------------------

class ErrorBody(dict):
    """Lightweight dict subclass so we can annotate usage in docs."""


def error_response(
    status_code: int,
    code: str,
    message: str,
    detail: Any = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if detail is not None:
        payload["error"]["detail"] = detail
    return JSONResponse(status_code=status_code, content=payload)


# ---------------------------------------------------------------------------
# CORS helper
# ---------------------------------------------------------------------------

def cors_origins(frontend_origin: str) -> list[str]:
    """Build the CORS origin list from the configured frontend origin."""
    allow_dev = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if frontend_origin and frontend_origin not in allow_dev:
        allow_dev.append(frontend_origin)
    return allow_dev