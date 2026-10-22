from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["operação"])


@router.get("/health", summary="Processo ativo")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Dependências (banco de dados e armazenamento) disponíveis")
def ready(request: Request) -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        with request.app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
    checks["storage"] = "ok" if request.app.state.storage.is_writable() else "unavailable"
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if ok else "unavailable", "checks": checks}, status_code=200 if ok else 503
    )
