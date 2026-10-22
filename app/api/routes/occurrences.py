from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import Operator, Reader, SessionDep
from app.api.schemas import MovementOut, OccurrenceOut, ReconciliationOut
from app.application import reconciliation_service
from app.application.schemas import ResolveIn
from app.domain.enums import OccurrenceStatus, ReconciliationStatus
from app.infrastructure.database.models import (
    BankOccurrence,
    FinancialMovement,
    ReconciliationResult,
)
from app.infrastructure.repositories import get_or_404

occurrences = APIRouter(prefix="/occurrences", tags=["ocorrências"])
reconciliation = APIRouter(prefix="/reconciliation", tags=["conciliação"])
movements = APIRouter(prefix="/movements", tags=["conciliação"])

Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]


@occurrences.get("", response_model=list[OccurrenceOut])
def list_occurrences(
    session: SessionDep,
    _: Reader,
    file_id: int | None = None,
    title_id: int | None = None,
    code: str | None = None,
    status_: Annotated[OccurrenceStatus | None, Query(alias="status")] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[BankOccurrence]:
    stmt = select(BankOccurrence).order_by(BankOccurrence.id)
    if file_id:
        stmt = stmt.where(BankOccurrence.bank_file_id == file_id)
    if title_id:
        stmt = stmt.where(BankOccurrence.title_id == title_id)
    if code:
        stmt = stmt.where(BankOccurrence.occurrence_code == code)
    if status_:
        stmt = stmt.where(BankOccurrence.processing_status == status_.value)
    return list(session.scalars(stmt.limit(limit).offset(offset)))


@occurrences.get("/{occurrence_id}", response_model=OccurrenceOut)
def get_occurrence(occurrence_id: int, session: SessionDep, _: Reader) -> BankOccurrence:
    return get_or_404(session, BankOccurrence, occurrence_id, "Ocorrência")


@reconciliation.get("", response_model=list[ReconciliationOut])
def list_reconciliation(
    session: SessionDep,
    _: Reader,
    status_: Annotated[ReconciliationStatus | None, Query(alias="status")] = None,
    resolved: bool | None = None,
    title_id: int | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[ReconciliationResult]:
    stmt = select(ReconciliationResult).order_by(ReconciliationResult.id)
    if status_:
        stmt = stmt.where(ReconciliationResult.status == status_.value)
    if resolved is not None:
        stmt = stmt.where(ReconciliationResult.resolved == resolved)
    if title_id:
        stmt = stmt.where(ReconciliationResult.title_id == title_id)
    return list(session.scalars(stmt.limit(limit).offset(offset)))


@reconciliation.get("/{reconciliation_id}", response_model=ReconciliationOut)
def get_reconciliation(
    reconciliation_id: int, session: SessionDep, _: Reader
) -> ReconciliationResult:
    return get_or_404(session, ReconciliationResult, reconciliation_id, "Conciliação")


@reconciliation.post(
    "/{reconciliation_id}/resolve",
    response_model=ReconciliationOut,
    summary="Marca divergência como analisada (com justificativa)",
)
def resolve(
    reconciliation_id: int, data: ResolveIn, session: SessionDep, principal: Operator
) -> ReconciliationResult:
    result = reconciliation_service.resolve(session, reconciliation_id, data.note, principal.actor)
    session.commit()
    return result


@movements.get("", response_model=list[MovementOut])
def list_movements(
    session: SessionDep,
    _: Reader,
    title_id: int | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[FinancialMovement]:
    stmt = select(FinancialMovement).order_by(FinancialMovement.id)
    if title_id:
        stmt = stmt.where(FinancialMovement.title_id == title_id)
    return list(session.scalars(stmt.limit(limit).offset(offset)))
