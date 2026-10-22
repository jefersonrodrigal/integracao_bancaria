from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    ConflictError,
    DomainError,
    InvalidStateTransition,
    NotFoundError,
    ValidationFailed,
)
from app.infrastructure.storage.local import StorageIntegrityError

log = logging.getLogger(__name__)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ValidationFailed)
    def _validation(_: Request, exc: ValidationFailed) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exc), "issues": [i.as_dict() for i in exc.issues]}, status_code=422
        )

    @app.exception_handler(ConflictError)
    def _conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse({"detail": str(exc), "context": exc.context}, status_code=409)

    @app.exception_handler(InvalidStateTransition)
    def _transition(_: Request, exc: InvalidStateTransition) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(DomainError)
    def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(StorageIntegrityError)
    def _storage(_: Request, exc: StorageIntegrityError) -> JSONResponse:
        log.error("Falha de integridade no armazenamento", extra={"error": str(exc)})
        return JSONResponse(
            {"detail": "Falha de integridade do arquivo armazenado"}, status_code=500
        )
