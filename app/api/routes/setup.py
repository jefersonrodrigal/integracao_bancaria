from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.dependencies import Admin, Reader, SessionDep
from app.api.schemas import BankAccountOut, BankOut, ProfileOut
from app.application import setup_service
from app.application.schemas import BankAccountCreate, BankCreate, ProfileCreate
from app.cnab.registry import available_layouts, get_adapter
from app.infrastructure.database.models import Bank, BankAccount, BankIntegrationProfile
from app.infrastructure.repositories import get_or_404

router = APIRouter(tags=["configuração"])


@router.get("/layouts", summary="Leiautes bancários disponíveis")
def list_layouts(_: Reader) -> list[dict[str, Any]]:
    return [
        {
            "layout_id": a.layout_id,
            "bank_code": a.bank_code,
            "family": a.family.value,
            "manual_version": a.manual_version,
        }
        for a in (get_adapter(layout) for layout in available_layouts())
    ]


@router.post("/banks", response_model=BankOut, status_code=status.HTTP_201_CREATED)
def create_bank(data: BankCreate, session: SessionDep, principal: Admin) -> Bank:
    bank = setup_service.create_bank(session, data, principal.actor)
    session.commit()
    return bank


@router.get("/banks", response_model=list[BankOut])
def list_banks(session: SessionDep, _: Reader) -> list[Bank]:
    return list(session.scalars(select(Bank).order_by(Bank.id)))


@router.post("/bank-accounts", response_model=BankAccountOut, status_code=status.HTTP_201_CREATED)
def create_account(data: BankAccountCreate, session: SessionDep, principal: Admin) -> BankAccount:
    account = setup_service.create_account(session, data, principal.actor)
    session.commit()
    return account


@router.get("/bank-accounts", response_model=list[BankAccountOut])
def list_accounts(session: SessionDep, _: Reader) -> list[BankAccount]:
    return list(session.scalars(select(BankAccount).order_by(BankAccount.id)))


@router.post(
    "/profiles",
    response_model=ProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria perfil de cobrança (conta + carteira + leiaute)",
)
def create_profile(
    data: ProfileCreate, session: SessionDep, principal: Admin
) -> BankIntegrationProfile:
    profile = setup_service.create_profile(session, data, principal.actor)
    session.commit()
    return profile


@router.get("/profiles", response_model=list[ProfileOut])
def list_profiles(session: SessionDep, _: Reader) -> list[BankIntegrationProfile]:
    return list(session.scalars(select(BankIntegrationProfile).order_by(BankIntegrationProfile.id)))


@router.get("/profiles/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: int, session: SessionDep, _: Reader) -> BankIntegrationProfile:
    return get_or_404(session, BankIntegrationProfile, profile_id, "Perfil")
