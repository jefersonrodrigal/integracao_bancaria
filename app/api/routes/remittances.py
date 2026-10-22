from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, File, Query, Request, Response, UploadFile, status
from sqlalchemy import select

from app.api.dependencies import Operator, Reader, SessionDep, StorageDep, read_upload
from app.api.schemas import RemittanceOut, ValidationOut
from app.application import remittance_service
from app.application.schemas import RemittanceCreate
from app.cnab.registry import get_adapter
from app.domain.enums import BatchStatus
from app.infrastructure.database.models import RemittanceBatch
from app.infrastructure.repositories import get_or_404

router = APIRouter(prefix="/remittances", tags=["remessas"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Gera arquivo de remessa para os títulos informados",
)
def create_remittance(
    data: RemittanceCreate, session: SessionDep, storage: StorageDep, principal: Operator
) -> dict[str, Any]:
    batch, report = remittance_service.generate(session, storage, data, principal.actor)
    session.commit()
    return {
        "remittance": RemittanceOut.model_validate(batch).model_dump(mode="json"),
        "validation": report.as_dict(),
    }


@router.post(
    "/validate",
    response_model=ValidationOut,
    summary="Valida um arquivo de remessa (estrutura e regras do manual)",
)
def validate_remittance(
    request: Request,
    _: Reader,
    file: Annotated[UploadFile, File()],
    layout_id: Annotated[str, Query()] = "ITAU_CNAB400",
) -> dict[str, Any]:
    content = read_upload(request, file)
    return get_adapter(layout_id).validate_remittance(content).as_dict()


@router.get("", response_model=list[RemittanceOut])
def list_remittances(
    session: SessionDep,
    _: Reader,
    profile_id: int | None = None,
    status_: Annotated[BatchStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RemittanceBatch]:
    stmt = select(RemittanceBatch).order_by(RemittanceBatch.id.desc())
    if profile_id:
        stmt = stmt.where(RemittanceBatch.profile_id == profile_id)
    if status_:
        stmt = stmt.where(RemittanceBatch.status == status_.value)
    return list(session.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{remittance_id}", response_model=RemittanceOut)
def get_remittance(remittance_id: int, session: SessionDep, _: Reader) -> RemittanceBatch:
    return get_or_404(session, RemittanceBatch, remittance_id, "Remessa")


@router.get(
    "/{remittance_id}/download",
    response_class=Response,
    responses={200: {"content": {"text/plain": {}}}},
)
def download_remittance(
    remittance_id: int, session: SessionDep, storage: StorageDep, principal: Operator
) -> Response:
    filename, content = remittance_service.download(
        session, storage, remittance_id, principal.actor
    )
    session.commit()
    return Response(
        content,
        media_type="text/plain; charset=us-ascii",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{remittance_id}/mark-sent",
    response_model=RemittanceOut,
    summary="Registra que o arquivo foi enviado ao banco pelo canal autorizado",
)
def mark_sent(remittance_id: int, session: SessionDep, principal: Operator) -> RemittanceBatch:
    batch = remittance_service.mark_sent(session, remittance_id, principal.actor)
    session.commit()
    return batch


@router.post(
    "/{remittance_id}/discard",
    response_model=RemittanceOut,
    summary="Descarta remessa não enviada e restaura o status dos títulos",
)
def discard(remittance_id: int, session: SessionDep, principal: Operator) -> RemittanceBatch:
    batch = remittance_service.discard(session, remittance_id, principal.actor)
    session.commit()
    return batch
