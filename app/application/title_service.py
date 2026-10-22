"""Casos de uso de títulos a receber."""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import audit
from app.application.mappers import item_data, profile_data
from app.application.schemas import PayerIn, TitleCreate, TitleFields, TitlePatch
from app.cnab.base import BankLayoutAdapter
from app.cnab.registry import get_adapter
from app.domain.enums import TitleStatus
from app.domain.errors import ConflictError, Issue, ValidationFailed
from app.domain.services.title_state import ensure_transition
from app.infrastructure.database.models import (
    BankIntegrationProfile,
    Customer,
    ReceivableTitle,
)
from app.infrastructure.repositories import get_or_404

_EDITABLE = (TitleStatus.OPEN, TitleStatus.REJECTED)
_SCALAR_FIELDS = (
    "document_number",
    "species",
    "acceptance",
    "issue_date",
    "due_date",
    "amount",
    "interest_per_day",
    "interest_start_date",
    "discount_amount",
    "discount_limit_date",
    "rebate_amount",
    "iof_amount",
    "instruction1",
    "instruction2",
    "protest_days",
)


def _upsert_customer(session: Session, payer: PayerIn) -> Customer:
    customer = session.scalars(
        select(Customer).where(
            Customer.document_type == payer.document_type.value,
            Customer.document == payer.document,
        )
    ).one_or_none()
    data = payer.model_dump(mode="json")
    if customer is None:
        customer = Customer(**data)
        session.add(customer)
    else:
        for key, value in data.items():
            setattr(customer, key, value)
    session.flush()
    return customer


def _allocate_nosso_numero(session: Session, profile: BankIntegrationProfile) -> str:
    """Aloca o próximo nosso número livre da faixa do perfil (bloqueando o perfil)."""
    locked = session.scalars(
        select(BankIntegrationProfile)
        .where(BankIntegrationProfile.id == profile.id)
        .with_for_update()
    ).one()
    candidate = locked.next_nosso_numero or locked.nosso_numero_min or 1
    upper = locked.nosso_numero_max or 99_999_999
    while candidate <= upper:
        number = str(candidate).zfill(8)
        taken = session.scalars(
            select(ReceivableTitle.id).where(
                ReceivableTitle.profile_id == profile.id, ReceivableTitle.nosso_numero == number
            )
        ).first()
        if taken is None:
            locked.next_nosso_numero = candidate + 1
            return number
        candidate += 1
    raise ValidationFailed(
        [
            Issue(
                "NOSSO_NUMERO_EXHAUSTED",
                "Faixa de nosso número esgotada",
                field="nosso_numero",
                reference="Nota 5 obs (D)",
            )
        ]
    )


def _apply_fields(
    title: ReceivableTitle, data: TitleFields | TitlePatch, *, only_sent: bool = True
) -> None:
    sent = data.model_fields_set if only_sent else set(type(data).model_fields)
    for name in _SCALAR_FIELDS:
        if name in sent:
            setattr(title, name, getattr(data, name))
    if "send_boleto_by_email" in sent and data.send_boleto_by_email is not None:
        title.send_email = data.send_boleto_by_email
    if "guarantor" in sent:
        title.guarantor = data.guarantor.model_dump(mode="json") if data.guarantor else None
    if "fine" in sent:
        fine = data.fine
        title.fine_type = fine.type.value if fine else None
        title.fine_date = fine.start_date if fine else None
        title.fine_value = fine.value if fine else None


def _validate(
    adapter: BankLayoutAdapter,
    profile: BankIntegrationProfile,
    title: ReceivableTitle,
    customer: Customer,
) -> None:
    issues = adapter.validate_item(profile_data(profile), item_data(title, customer))
    if title.send_email and not customer.email:
        issues.append(
            Issue(
                "EMAIL_REQUIRED",
                "Envio por e-mail exige e-mail do pagador",
                field="payer.email",
                reference="Nota 29 p.37",
            )
        )
    if issues:
        raise ValidationFailed(issues, "Título inválido para o perfil de cobrança")


def _ensure_unique_nosso_numero(session: Session, title: ReceivableTitle) -> None:
    if title.nosso_numero is None:
        return
    other = session.scalars(
        select(ReceivableTitle.id).where(
            ReceivableTitle.profile_id == title.profile_id,
            ReceivableTitle.nosso_numero == title.nosso_numero,
            ReceivableTitle.id != (title.id or 0),
        )
    ).first()
    if other is not None:
        raise ConflictError("Nosso número já utilizado neste perfil", title_id=other)


def create_title(session: Session, data: TitleCreate, actor: str) -> ReceivableTitle:
    profile = get_or_404(session, BankIntegrationProfile, data.profile_id, "Perfil")
    if not profile.active:
        raise ConflictError("Perfil inativo")
    adapter = get_adapter(profile.layout_id)
    customer = _upsert_customer(session, data.payer)
    title = ReceivableTitle(
        profile_id=profile.id,
        customer_id=customer.id,
        company_reference=secrets.token_hex(12).upper(),
        status=TitleStatus.OPEN.value,
        send_email=False,
    )
    title.profile = profile
    _apply_fields(title, data, only_sent=False)
    title.nosso_numero = data.nosso_numero.zfill(8) if data.nosso_numero else None
    if title.nosso_numero is None and not adapter.nosso_numero_assigned_by_bank(profile.wallet):
        # Alocação desfeita pelo rollback se a validação abaixo falhar.
        title.nosso_numero = _allocate_nosso_numero(session, profile)
    _validate(adapter, profile, title, customer)
    _ensure_unique_nosso_numero(session, title)
    if title.nosso_numero:
        title.nosso_numero_dac = adapter.nosso_numero_dac(
            profile.bank_account.agency,
            profile.bank_account.account,
            profile.wallet,
            title.nosso_numero,
        )
    session.add(title)
    session.flush()
    audit.record(
        session,
        actor,
        "title.create",
        "title",
        title.id,
        {"profile_id": profile.id, "amount": str(title.amount)},
    )
    return title


def update_title(session: Session, title_id: int, data: TitlePatch, actor: str) -> ReceivableTitle:
    title = get_or_404(session, ReceivableTitle, title_id, "Título")
    status = TitleStatus(title.status)
    if status not in _EDITABLE:
        raise ConflictError(f"Título em {status} não pode ser alterado", status=status.value)
    profile = title.profile
    adapter = get_adapter(profile.layout_id)
    customer = _upsert_customer(session, data.payer) if data.payer else title.customer
    title.customer_id = customer.id
    title.customer = customer
    _apply_fields(title, data)
    if "nosso_numero" in data.model_fields_set:
        title.nosso_numero = data.nosso_numero.zfill(8) if data.nosso_numero else None
    _validate(adapter, profile, title, customer)
    _ensure_unique_nosso_numero(session, title)
    if title.nosso_numero:
        title.nosso_numero_dac = adapter.nosso_numero_dac(
            profile.bank_account.agency,
            profile.bank_account.account,
            profile.wallet,
            title.nosso_numero,
        )
    if status is TitleStatus.REJECTED:
        ensure_transition(status, TitleStatus.OPEN)
        title.status = TitleStatus.OPEN.value
        title.last_bank_message = None
    session.flush()
    audit.record(
        session,
        actor,
        "title.update",
        "title",
        title.id,
        {"fields": sorted(data.model_fields_set), "previous_status": status.value},
    )
    return title


def list_titles(
    session: Session,
    *,
    status: TitleStatus | None = None,
    profile_id: int | None = None,
    document_number: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ReceivableTitle]:
    stmt = select(ReceivableTitle).order_by(ReceivableTitle.id)
    filters: list[Any] = []
    if status:
        filters.append(ReceivableTitle.status == status.value)
    if profile_id:
        filters.append(ReceivableTitle.profile_id == profile_id)
    if document_number:
        filters.append(ReceivableTitle.document_number == document_number)
    return list(session.scalars(stmt.where(*filters).limit(limit).offset(offset)))
