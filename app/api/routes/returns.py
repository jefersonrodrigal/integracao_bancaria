from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import Operator, Reader, SessionDep, StorageDep, read_upload
from app.api.schemas import AttemptOut, ReturnOut
from app.application import return_service
from app.domain.enums import FileDirection
from app.domain.errors import NotFoundError
from app.infrastructure.database.models import BankFile, FileProcessingAttempt

router = APIRouter(prefix="/returns", tags=["retornos"])


def _get_return(session: Session, return_id: int) -> BankFile:
    bank_file = session.get(BankFile, return_id)
    if bank_file is None or bank_file.direction != FileDirection.RETURN.value:
        raise NotFoundError(f"Retorno {return_id} não encontrado")
    return bank_file


@router.post(
    "",
    response_model=ReturnOut,
    status_code=status.HTTP_201_CREATED,
    summary="Importa e processa arquivo de retorno",
    responses={409: {"description": "Arquivo já importado"}},
)
def upload_return(
    request: Request,
    session: SessionDep,
    storage: StorageDep,
    principal: Operator,
    file: Annotated[UploadFile, File()],
    layout_id: Annotated[str | None, Query(description="Obrigatório se houver ambiguidade")] = None,
) -> BankFile:
    content = read_upload(request, file)
    bank_file = return_service.import_return(
        session, storage, content, file.filename or "retorno.ret", principal.actor, layout_id
    )
    session.refresh(bank_file)
    return bank_file


@router.get("", response_model=list[ReturnOut])
def list_returns(
    session: SessionDep,
    _: Reader,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BankFile]:
    stmt = (
        select(BankFile)
        .where(BankFile.direction == FileDirection.RETURN.value)
        .order_by(BankFile.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt))


@router.get("/{return_id}", response_model=ReturnOut)
def get_return(return_id: int, session: SessionDep, _: Reader) -> BankFile:
    return _get_return(session, return_id)


@router.get("/{return_id}/report", summary="Relatório do processamento do retorno")
def get_report(return_id: int, session: SessionDep, _: Reader) -> dict[str, Any]:
    _get_return(session, return_id)
    return return_service.build_report(session, return_id)


@router.post(
    "/{return_id}/reprocess",
    response_model=AttemptOut,
    summary="Reprocessa o retorno; ocorrências já gravadas são ignoradas",
)
def reprocess(
    return_id: int, session: SessionDep, storage: StorageDep, principal: Operator
) -> FileProcessingAttempt:
    _get_return(session, return_id)
    return return_service.process(session, storage, return_id, principal.actor)
