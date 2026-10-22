from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import Operator, Reader, SessionDep
from app.api.schemas import TitleOut
from app.application import title_service
from app.application.schemas import TitleCreate, TitlePatch
from app.domain.enums import TitleStatus
from app.domain.services.title_state import is_overdue
from app.infrastructure.database.models import ReceivableTitle
from app.infrastructure.repositories import get_or_404

router = APIRouter(prefix="/titles", tags=["títulos"])


def _out(title: ReceivableTitle) -> TitleOut:
    out = TitleOut.model_validate(title)
    out.is_overdue = is_overdue(TitleStatus(title.status), title.due_date, date.today())
    return out


@router.post("", response_model=TitleOut, status_code=status.HTTP_201_CREATED)
def create_title(data: TitleCreate, session: SessionDep, principal: Operator) -> TitleOut:
    title = title_service.create_title(session, data, principal.actor)
    session.commit()
    return _out(title)


@router.get("", response_model=list[TitleOut])
def list_titles(
    session: SessionDep,
    _: Reader,
    status_: Annotated[TitleStatus | None, Query(alias="status")] = None,
    profile_id: int | None = None,
    document_number: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TitleOut]:
    titles = title_service.list_titles(
        session,
        status=status_,
        profile_id=profile_id,
        document_number=document_number,
        limit=limit,
        offset=offset,
    )
    return [_out(t) for t in titles]


@router.get("/{title_id}", response_model=TitleOut)
def get_title(title_id: int, session: SessionDep, _: Reader) -> TitleOut:
    return _out(get_or_404(session, ReceivableTitle, title_id, "Título"))


@router.patch(
    "/{title_id}",
    response_model=TitleOut,
    summary="Altera título OPEN/REJECTED (REJECTED volta a OPEN)",
)
def update_title(
    title_id: int, data: TitlePatch, session: SessionDep, principal: Operator
) -> TitleOut:
    title = title_service.update_title(session, title_id, data, principal.actor)
    session.commit()
    return _out(title)
