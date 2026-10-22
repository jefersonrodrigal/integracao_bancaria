"""Cria dados SINTÉTICOS de desenvolvimento (banco 341, conta, perfil carteira 109, títulos).

Uso: python -m scripts.seed_dev   (após ``alembic upgrade head``)
Agência/conta 0057/12345-7 vêm do exemplo do Anexo 2 do manual; não é uma conta real.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.application import setup_service, title_service
from app.application.schemas import (
    BankAccountCreate,
    BankCreate,
    PayerIn,
    ProfileCreate,
    TitleCreate,
)
from app.core.config import get_settings
from app.domain.enums import DocumentType
from app.infrastructure.database.models import Bank, BankIntegrationProfile
from app.infrastructure.database.session import build_engine, build_session_factory

ACTOR = "seed"


def main() -> None:
    engine = build_engine(get_settings().database_url)
    with build_session_factory(engine)() as session:
        if session.scalars(select(Bank).where(Bank.code == "341")).first():
            print("Dados já existem; nada a fazer.")
            return
        bank = setup_service.create_bank(
            session, BankCreate(code="341", name="ITAU UNIBANCO"), ACTOR
        )
        account = setup_service.create_account(
            session,
            BankAccountCreate(
                bank_id=bank.id,
                agency="0057",
                account="12345",
                account_dac="7",
                holder_name="EMPRESA SINTETICA LTDA",
                holder_document_type=DocumentType.CNPJ,
                holder_document="11222333000181",
            ),
            ACTOR,
        )
        profile: BankIntegrationProfile = setup_service.create_profile(
            session,
            ProfileCreate(
                bank_account_id=account.id,
                name="Itaú 109 (sintético)",
                layout_id="ITAU_CNAB400",
                wallet="109",
                company_name="EMPRESA SINTETICA LTDA",
            ),
            ACTOR,
        )
        payer = PayerIn(
            name="Cliente Sintético da Silva",
            document_type=DocumentType.CPF,
            document="52998224725",
            street="Rua Exemplo, 100",
            district="Centro",
            zip_code="01001000",
            city="São Paulo",
            state="SP",
        )
        for index in range(1, 4):
            title_service.create_title(
                session,
                TitleCreate(
                    profile_id=profile.id,
                    document_number=f"DEV{index:04d}",
                    issue_date=date.today(),
                    due_date=date.today() + timedelta(days=30),
                    amount=Decimal(f"{100 * index}.00"),
                    payer=payer,
                ),
                ACTOR,
            )
        session.commit()
        print(f"Perfil {profile.id} criado com 3 títulos OPEN.")
    engine.dispose()


if __name__ == "__main__":
    main()
