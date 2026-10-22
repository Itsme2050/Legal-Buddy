"""FastAPI application entrypoint for Legal Buddy."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import RateLimiter, cors_origins, error_response
from app.repositories.database import engine, get_session, init_db
from app.repositories.session_repository import DISCLAIMER, SessionRepository
from app.schemas import (
    DocumentAnalyzeResponse,
    GraphPayload,
    HealthResponse,
    HistoryResponse,
    IntegrationStatus,
    ResearchRequest,
    ResearchResult,
    SessionStatus,
)
from app.services.documents import DocumentValidationError, analyze_uploaded_pdf
from app.services.gemini_client import GeminiConfigError
from app.services.research_workflow import ResearchWorkflow
from app.services.tinyfish_client import TinyFishConfigError

logging.basicConfig(
    level=logging.INFO if get_settings().debug else logging.WARNING,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("legal_buddy")

settings = get_settings()
rate_limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
        logger.exception("database unavailable")
    if not db_ok:
        logger.warning("database check failed — continuing with degraded health")
    yield


app = FastAPI(
    title="Legal Buddy API",
    version="0.1.0",
    description=(
        "Evidence-backed legal research: TinyFish Search/Fetch discovery, "
        "Gemini analysis, and React Flow relationship graphs. "
        "Informational research assistance only — not legal advice."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(settings.frontend_origin),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Rate limiting dependency
# ---------------------------------------------------------------------------

def _client_key(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    rate_limit(request)


# Use FastAPI's HTTPException for clarity
from fastapi import HTTPException  # noqa: E402


def rate_limit(request: Request) -> None:
    key = _client_key(request)
    if not rate_limiter.check(key):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": (
                    f"Too many requests. Limit is {settings.rate_limit_requests} "
                    f"per {int(settings.rate_limit_window_seconds)}s — try again shortly."
                ),
            },
        )


# ---------------------------------------------------------------------------
# Health & integration status
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    integrations = [
        IntegrationStatus(
            provider="tinyfish_search",
            configured=bool(settings.tinyfish_api_key),
            endpoint=settings.tinyfish_search_endpoint if settings.tinyfish_api_key else None,
            detail=None if settings.tinyfish_api_key else "TINYFISH_API_KEY missing — live search disabled",
        ),
        IntegrationStatus(
            provider="tinyfish_fetch",
            configured=bool(settings.tinyfish_api_key),
            endpoint=settings.tinyfish_fetch_endpoint if settings.tinyfish_api_key else None,
            detail=None if settings.tinyfish_api_key else "TINYFISH_API_KEY missing — live fetch disabled",
        ),
        IntegrationStatus(
            provider="gemini",
            configured=bool(settings.gemini_api_key),
            endpoint=None,
            detail=None if settings.gemini_api_key else "GEMINI_API_KEY missing — analysis disabled",
        ),
    ]
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        db_status = "ok"
    except Exception:
        db_status = "unavailable"

    ok = all(i.configured for i in integrations) and db_status == "ok"
    return HealthResponse(
        status="ok" if ok else "degraded",
        app=settings.app_name,
        environment=settings.environment,
        integrations=integrations,
        database=db_status,
        server_time=datetime.now(timezone.utc),
    )


@app.get("/api/integrations/status", tags=["meta"])
def integrations_status() -> dict:
    """Non-sensitive integration status — never returns keys or secrets."""
    return {
        "tinyfish": {
            "configured": bool(settings.tinyfish_api_key),
            "search_endpoint": settings.tinyfish_search_endpoint if settings.tinyfish_api_key else None,
            "fetch_endpoint": settings.tinyfish_fetch_endpoint if settings.tinyfish_api_key else None,
            "search_limit": settings.tinyfish_search_limit,
            "fetch_limit": settings.tinyfish_fetch_limit,
            "timeout_seconds": settings.tinyfish_timeout_seconds,
        },
        "gemini": {
            "configured": bool(settings.gemini_api_key),
            "model": settings.gemini_model,
            "timeout_seconds": settings.gemini_timeout_seconds,
        },
        "database": "ok",
        "demo_mode": True,
        "demo_mode_note": (
            "No authentication in this MVP — session IDs are not authorization. "
            "Treat history as demo data."
        ),
    }


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

@app.post("/api/research", tags=["research"], dependencies=[Depends(rate_limit)])
async def start_research(
    request_body: ResearchRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    repo = SessionRepository(db)

    # Enforce configurable daily plan limits (honest, per documented plans)
    daily = repo.daily_usage(request_body.plan)
    if daily["search_requests"] >= daily["search_limit"]:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "plan_limit_search",
                "message": (
                    f"Daily research limit reached for the {request_body.plan} plan "
                    f"({daily['search_limit']} searches/day). Limits depend on API "
                    "usage costs — see Pricing."
                ),
            },
        )

    workflow = ResearchWorkflow(db)
    session_id = await workflow.run(request_body)
    row = repo.get(session_id)
    if row is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail={"code": "internal_error", "message": "Session lost"})
    result = repo.to_result(row)
    return {
        "session_id": result.session_id,
        "status": result.status.value,
        "result": result.model_dump(mode="json"),
    }


@app.get("/api/research/{session_id}", tags=["research"])
def get_research(session_id: str, db: Session = Depends(get_session)) -> dict:
    repo = SessionRepository(db)
    row = repo.get(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Session not found"})
    return {"result": repo.to_result(row).model_dump(mode="json")}


@app.get("/api/research/{session_id}/sources", tags=["research"])
def get_sources(session_id: str, db: Session = Depends(get_session)) -> dict:
    repo = SessionRepository(db)
    row = repo.get(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Session not found"})
    sources = repo.get_sources(session_id)
    return {"sources": [s.model_dump(mode="json") for s in sources]}


@app.get("/api/research/{session_id}/graph", tags=["research"])
def get_graph(session_id: str, db: Session = Depends(get_session)) -> GraphPayload:
    repo = SessionRepository(db)
    row = repo.get(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Session not found"})
    graph = row.graph or {"nodes": [], "edges": []}
    return GraphPayload.model_validate(graph)


@app.get("/api/research/{session_id}/stream")
async def research_stream(session_id: str, db: Session = Depends(get_session)) -> StreamingResponse:
    """SSE stream of the research session (polling loop over stored status)."""
    repo = SessionRepository(db)

    async def event_gen():
        last_sent = None

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        for _ in range(600):  # ~120s max
            try:
                db.expire_all()
            except Exception:
                pass
            row = repo.get(session_id)
            if row is None:
                yield sse("error", {"message": "not found"})
                return
            payload = repo.to_result(row)
            stages_dump = [s.model_dump(mode="json") for s in payload.stages]
            snap = (payload.status.value, json.dumps(stages_dump))
            if snap != last_sent:
                last_sent = snap
                yield sse(
                    "status",
                    {
                        "status": payload.status.value,
                        "stages": stages_dump,
                        "sources": len(payload.sources),
                    },
                )
            if payload.status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.PARTIAL):
                yield sse("done", {"session_id": session_id, "status": payload.status.value})
                return
            await asyncio.sleep(0.5)
        yield sse("timeout", {})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@app.post("/api/documents/analyze", tags=["documents"], dependencies=[Depends(rate_limit)])
async def analyze_document(
    file: UploadFile = File(...),
    plan: str = Form(default="free"),
    db: Session = Depends(get_session),
) -> DocumentAnalyzeResponse:
    data = await file.read()
    try:
        result = await analyze_uploaded_pdf(data, file.filename or "upload.pdf")
        repo = SessionRepository(db)
        repo.save_document(
            document_id=result.document_id,
            filename=result.filename,
            size_bytes=result.size_bytes,
            text_chars=result.text_chars,
            status=result.status,
            preview_markdown=result.preview_markdown,
            analysis=result.analysis,
            graph=result.graph,
            error=result.error,
        )
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_document", "message": str(exc)},
        )
    return result


# ---------------------------------------------------------------------------
# History & usage
# ---------------------------------------------------------------------------

@app.get("/api/history", tags=["history"], response_model=HistoryResponse)
def history(db: Session = Depends(get_session)) -> HistoryResponse:
    return SessionRepository(db).history()


@app.delete("/api/history/{session_id}", tags=["history"])
def delete_session(session_id: str, db: Session = Depends(get_session)) -> dict:
    ok = SessionRepository(db).delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Session not found"})
    return {"deleted": True, "session_id": session_id}


@app.get("/api/usage/summary", tags=["usage"])
def usage_summary(db: Session = Depends(get_session)) -> dict:
    repo = SessionRepository(db)
    by_plan = repo.usage_summary()
    return {
        "by_plan": by_plan,
        "daily": {
            "free": repo.daily_usage("free"),
            "professional": repo.daily_usage("professional"),
        },
        "assumptions": (
            "Cost estimates use documented placeholder rates; viability of the "
            "₹999/month plan depends on actual TinyFish + Gemini pricing and "
            "average source counts per session."
        ),
    }


# ---------------------------------------------------------------------------
# Error handling — consistent schema
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": detail["code"], "message": detail.get("message", "")}},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(detail)}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Unexpected server error."}},
    )


DISCLAIMER_SENTINEL = DISCLAIMER  # re-export for tests

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)