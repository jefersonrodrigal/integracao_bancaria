"""Cadastro de bancos, contas e perfis de integração."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import audit
from app.application.mappers import profile_data
from app.application.schemas import BankAccountCreate, BankCreate, ProfileCreate
from app.cnab.registry import get_adapter
from app.domain.errors import ConflictError, Issue, ValidationFailed
from app.domain.value_objects import is_valid_document
from app.infrastructure.database.models import Bank, BankAccount, BankIntegrationProfile
from app.infrastructure.repositories import get_or_404


def create_bank(session: Session, data: BankCreate, actor: str) -> Bank:
    if session.scalars(select(Bank).where(Bank.code == data.code)).first():
        raise ConflictError(f"Banco {data.code} já cadastrado")
    bank = Bank(code=data.code, name=data.name)
    session.add(bank)
    session.flush()
    audit.record(session, actor, "bank.create", "bank", bank.id, {"code": bank.code})
    return bank


def create_account(session: Session, data: BankAccountCreate, actor: str) -> BankAccount:
    get_or_404(session, Bank, data.bank_id, "Banco")
    if not is_valid_document(data.holder_document_type, data.holder_document):
        raise ValidationFailed(
            [
                Issue(
                    "DOCUMENT",
                    "CPF/CNPJ do titular inválido",
                    field="holder_document",
                    reference="regra interna",
                )
            ]
        )
    exists = session.scalars(
        select(BankAccount).where(
            BankAccount.bank_id == data.bank_id,
            BankAccount.agency == data.agency,
            BankAccount.account == data.account,
            BankAccount.account_dac == data.account_dac,
        )
    ).first()
    if exists:
        raise ConflictError("Conta bancária já cadastrada", account_id=exists.id)
    account = BankAccount(**data.model_dump(mode="json"))
    session.add(account)
    session.flush()
    audit.record(session, actor, "bank_account.create", "bank_account", account.id)
    return account


def create_profile(session: Session, data: ProfileCreate, actor: str) -> BankIntegrationProfile:
    account = get_or_404(session, BankAccount, data.bank_account_id, "Conta bancária")
    adapter = get_adapter(data.layout_id)
    if account.bank.code != adapter.bank_code:
        raise ValidationFailed(
            [
                Issue(
                    "BANK_MISMATCH",
                    f"Leiaute {data.layout_id} é do banco {adapter.bank_code}",
                    field="layout_id",
                )
            ]
        )
    profile = BankIntegrationProfile(
        bank_account_id=account.id,
        name=data.name,
        layout_id=adapter.layout_id,
        manual_version=adapter.manual_version,
        wallet=data.wallet,
        company_name=data.company_name,
        nosso_numero_min=data.nosso_numero_min,
        nosso_numero_max=data.nosso_numero_max,
        next_nosso_numero=data.nosso_numero_min,
        line_terminator=data.line_terminator,
        active=True,
    )
    profile.bank_account = account
    issues = adapter.validate_profile(profile_data(profile))
    if issues:
        raise ValidationFailed(issues, "Perfil inválido para o leiaute")
    duplicate = session.scalars(
        select(BankIntegrationProfile).where(
            BankIntegrationProfile.bank_account_id == account.id,
            BankIntegrationProfile.wallet == data.wallet,
        )
    ).first()
    if duplicate:
        raise ConflictError("Já existe perfil para esta conta e carteira", profile_id=duplicate.id)
    session.add(profile)
    session.flush()
    audit.record(
        session,
        actor,
        "profile.create",
        "profile",
        profile.id,
        {"layout": profile.layout_id, "wallet": profile.wallet},
    )
    return profile
