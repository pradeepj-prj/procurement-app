from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import get_backend
from app.db.backend import DataBackend

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    """Liveness check — always fast, no dependencies."""
    return {
        "status": "healthy",
        "version": request.app.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def ready(backend: DataBackend = Depends(get_backend)):
    """Readiness check — verifies downstream dependencies."""
    checks: dict[str, str] = {}

    # Database check
    try:
        try:
            backend.execute_sql("SELECT 1 FROM DUMMY")
        except NotImplementedError:
            # NetworkXBackend doesn't support SQL — use a typed method instead
            backend.get_vertex_counts()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    status = "ready" if all_ok else "not_ready"
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={"status": status, "checks": checks},
        status_code=status_code,
    )
