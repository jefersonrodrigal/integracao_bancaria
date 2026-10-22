from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, UploadFile, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.core.security import Principal, authenticate
from app.infrastructure.storage.local import LocalFileStorage

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_session(request: Request) -> Iterator[Session]:
    """Sessão por requisição. Rotas que alteram dados fazem ``commit`` explicitamente."""
    session: Session = request.app.state.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_storage(request: Request) -> LocalFileStorage:
    storage: LocalFileStorage = request.app.state.storage
    return storage


def require(role: str) -> Callable[..., Principal]:
    def dependency(
        request: Request, api_key: Annotated[str | None, Depends(api_key_header)]
    ) -> Principal:
        principal = authenticate(api_key, request.app.state.api_keys)
        if principal is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave de API ausente ou inválida")
        if not principal.has_role(role):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requer papel {role}")
        return principal

    return dependency


def read_upload(request: Request, file: UploadFile) -> bytes:
    limit: int = request.app.state.settings.max_upload_bytes
    content = file.file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"Arquivo excede {limit} bytes")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Arquivo vazio")
    return content


SessionDep = Annotated[Session, Depends(get_session)]
StorageDep = Annotated[LocalFileStorage, Depends(get_storage)]
Reader = Annotated[Principal, Depends(require("reader"))]
Operator = Annotated[Principal, Depends(require("operator"))]
Admin = Annotated[Principal, Depends(require("admin"))]
