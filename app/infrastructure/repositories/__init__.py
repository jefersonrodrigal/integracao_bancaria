"""Consultas reutilizadas pelos serviços de aplicação."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import NotFoundError
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    Bank,
    BankAccount,
    BankIntegrationProfile,
    ReceivableTitle,
)


def get_or_404[M: Base](session: Session, model: type[M], entity_id: int, label: str) -> M:
    entity = session.get(model, entity_id)
    if entity is None:
        raise NotFoundError(f"{label} {entity_id} não encontrado")
    return entity


def find_profile_for_detail(
    session: Session, bank_code: str, agency: str, account: str, dac: str, wallet: str
) -> BankIntegrationProfile | None:
    stmt = (
        select(BankIntegrationProfile)
        .join(BankAccount, BankIntegrationProfile.bank_account_id == BankAccount.id)
        .join(Bank, BankAccount.bank_id == Bank.id)
        .where(
            Bank.code == bank_code,
            BankAccount.agency == agency,
            BankAccount.account == account,
            BankAccount.account_dac == dac,
            BankIntegrationProfile.wallet == wallet,
        )
    )
    return session.scalars(stmt).one_or_none()


def find_title_by_reference(session: Session, reference: str) -> ReceivableTitle | None:
    return session.scalars(
        select(ReceivableTitle).where(ReceivableTitle.company_reference == reference)
    ).one_or_none()


def find_title_by_nosso_numero(
    session: Session, profile_id: int, nosso_numero: str
) -> ReceivableTitle | None:
    return session.scalars(
        select(ReceivableTitle).where(
            ReceivableTitle.profile_id == profile_id,
            ReceivableTitle.nosso_numero == nosso_numero,
        )
    ).one_or_none()
