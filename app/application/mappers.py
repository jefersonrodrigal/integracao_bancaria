"""Conversão entre o modelo persistente e os DTOs dos adaptadores."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.cnab.base import CollectionProfileData, FineData, PartyData, RemittanceItemData
from app.domain.enums import DocumentType, FineType, RemittanceCommand
from app.infrastructure.database.models import BankIntegrationProfile, Customer, ReceivableTitle


def profile_data(profile: BankIntegrationProfile) -> CollectionProfileData:
    account = profile.bank_account
    return CollectionProfileData(
        agency=account.agency,
        account=account.account,
        account_dac=account.account_dac,
        company_name=profile.company_name,
        company_document_type=DocumentType(account.holder_document_type),
        company_document=account.holder_document,
        wallet=profile.wallet,
        nosso_numero_min=profile.nosso_numero_min,
        nosso_numero_max=profile.nosso_numero_max,
        line_terminator=profile.line_terminator,
    )


def customer_party(customer: Customer) -> PartyData:
    return PartyData(
        name=customer.name,
        document_type=DocumentType(customer.document_type),
        document=customer.document,
        street=customer.street,
        district=customer.district,
        zip_code=customer.zip_code,
        city=customer.city,
        state=customer.state,
    )


def party_from_dict(data: dict[str, Any] | None) -> PartyData | None:
    if not data:
        return None
    return PartyData(
        name=data["name"],
        document_type=DocumentType(data["document_type"]),
        document=data["document"],
        street=data["street"],
        district=data.get("district", ""),
        zip_code=data["zip_code"],
        city=data["city"],
        state=data["state"],
    )


def item_data(
    title: ReceivableTitle,
    customer: Customer,
    command: RemittanceCommand = RemittanceCommand.REGISTER,
    new_due_date: date | None = None,
) -> RemittanceItemData:
    fine = None
    if title.fine_type and title.fine_date and title.fine_value is not None:
        fine = FineData(FineType(title.fine_type), title.fine_date, title.fine_value)
    return RemittanceItemData(
        command=command,
        company_reference=title.company_reference,
        nosso_numero=title.nosso_numero,
        document_number=title.document_number,
        issue_date=title.issue_date,
        due_date=title.due_date,
        amount=title.amount,
        species=title.species,
        acceptance=title.acceptance,
        payer=customer_party(customer),
        payer_email=customer.email if title.send_email else None,
        guarantor=party_from_dict(title.guarantor),
        instruction1=title.instruction1,
        instruction2=title.instruction2,
        protest_days=title.protest_days,
        interest_per_day=title.interest_per_day,
        interest_start_date=title.interest_start_date,
        discount_amount=title.discount_amount,
        discount_limit_date=title.discount_limit_date,
        rebate_amount=title.rebate_amount,
        iof_amount=title.iof_amount,
        fine=fine,
        new_due_date=new_due_date,
        reference_id=title.id,
    )
