"""Centralized configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Load from current directory, backend directory, and project root
    _backend_dir = Path(__file__).resolve().parent.parent.parent
    _root_dir = _backend_dir.parent
    for _candidate in (
        Path(".env"),
        Path("backend/.env"),
        _backend_dir / ".env",
        _root_dir / ".env",
    ):
        if _candidate.is_file():
            load_dotenv(dotenv_path=_candidate, override=False)
except ImportError:
    pass


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is not None:
        value = value.strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    # Core
    app_name: str = _env("APP_NAME", "Legal Buddy") or "Legal Buddy"
    environment: str = _env("ENVIRONMENT", "development") or "development"
    debug: bool = (_env("DEBUG", "true") or "true").lower() == "true"
    database_url: str = _env("DATABASE_URL", "sqlite:///./legal_buddy.db") or "sqlite:///./legal_buddy.db"
    frontend_origin: str = _env("FRONTEND_ORIGIN", "http://localhost:3000") or "http://localhost:3000"

    # TinyFish
    tinyfish_api_key: str | None = _env("TINYFISH_API_KEY")
    tinyfish_search_endpoint: str = (
        _env("TINYFISH_SEARCH_ENDPOINT", "https://api.search.tinyfish.ai")
        or "https://api.search.tinyfish.ai"
    )
    tinyfish_fetch_endpoint: str = (
        _env("TINYFISH_FETCH_ENDPOINT", "https://api.fetch.tinyfish.ai")
        or "https://api.fetch.tinyfish.ai"
    )
    tinyfish_timeout_seconds: float = _env_float("TINYFISH_TIMEOUT_SECONDS", 30.0)
    tinyfish_search_limit: int = _env_int("TINYFISH_SEARCH_LIMIT", 8)
    tinyfish_fetch_limit: int = _env_int("TINYFISH_FETCH_LIMIT", 5)
    tinyfish_max_fetch_urls: int = 10  # provider-documented maximum per request

    # Gemini
    gemini_api_key: str | None = _env("GEMINI_API_KEY")
    gemini_model: str = _env("GEMINI_MODEL", "gemini-3.8-flash") or "gemini-3.8-flash"
    gemini_timeout_seconds: float = _env_float("GEMINI_TIMEOUT_SECONDS", 60.0)
    gemini_max_excerpt_chars: int = _env_int("GEMINI_MAX_EXCERPT_CHARS", 9000)

    # PDF upload
    max_upload_bytes: int = _env_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)  # 10 MB
    allowed_upload_types: tuple[str, ...] = ("application/pdf",)

    # Rate limiting (simple in-process sliding window)
    rate_limit_requests: int = _env_int("RATE_LIMIT_REQUESTS", 30)
    rate_limit_window_seconds: float = _env_float("RATE_LIMIT_WINDOW_SECONDS", 60.0)

    # Usage / plans
    usage_daily_search_limit_free: int = _env_int("USAGE_DAILY_SEARCH_LIMIT_FREE", 10)
    usage_daily_fetch_limit_free: int = _env_int("USAGE_DAILY_FETCH_LIMIT_FREE", 25)
    usage_daily_search_limit_pro: int = _env_int("USAGE_DAILY_SEARCH_LIMIT_PRO", 100)
    usage_daily_fetch_limit_pro: int = _env_int("USAGE_DAILY_FETCH_LIMIT_PRO", 500)

    # Retention
    session_retention_days: int = _env_int("SESSION_RETENTION_DAYS", 30)

    official_domains: tuple[str, ...] = (
        "sci.gov.in",
        "ecommerce.gov.in",
        "ecourts.gov.in",
        "indiacode.nic.in",
        "legislative.gov.in",
        "indiankanoon.org",
        "dharyana.gov.in",
        "judiciary.delhi.nic.in",
        "bombayhighcourt.nic.gov.in",
        "calcuttahighcourt.nic.gov.in",
        "madraslycourts.gov.in",
        "karnataka.gov.in",
        "gov.in",
        "nic.in",
        "nclt.gov.in",
        "consumercomplaints.gov.in",
        "egyata.gov.in",
        "rdsa.gov.in",
        "asia",
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset cached settings (used by tests)."""
    global _settings
    _settings = None