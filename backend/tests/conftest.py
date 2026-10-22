"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_legal_buddy.db")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture(autouse=True)
def fresh_settings():
    """Give every test a fresh Settings singleton (tests mutate settings)."""
    from app.core.config import reset_settings

    reset_settings()
    yield
    reset_settings()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def anyio_backend():
    return "asyncio"