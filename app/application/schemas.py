"""Comandos de entrada dos casos de uso (também usados como corpo das requisições)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import DocumentType, FineType, RemittanceCommand
from app.domain.value_objects import only_digits

MoneyIn = Annotated[Decimal, Field(ge=0, max_digits=13, decimal_places=2)]


class _In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class PartyIn(_In):
    name: str = Field(min_length=1, max_length=100)
    document_type: DocumentType
    document: str = Field(description="CPF (11) ou CNPJ (14); pontuação é removida")
    street: str = Field(min_length=1, max_length=100)
    district: str = Field(default="", max_length=60)
    zip_code: str
    city: str = Field(min_length=1, max_length=60)
    state: str = Field(min_length=2, max_length=2)

    @field_validator("document", "zip_code")
    @classmethod
    def _digits(cls, value: str) -> str:
        return only_digits(value)

    @field_validator("state")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class PayerIn(PartyIn):
    email: str | None = Field(default=None, max_length=120)


class FineIn(_In):
    type: FineType
    start_date: date
    value: Annotated[Decimal, Field(gt=0, max_digits=13, decimal_places=2)]


class BankCreate(_In):
    code: str = Field(pattern=r"^\d{3}$")
    name: str = Field(min_length=1, max_length=100)


class BankAccountCreate(_In):
    bank_id: int
    agency: str = Field(pattern=r"^\d{4}$")
    account: str = Field(pattern=r"^\d{5}$")
    account_dac: str = Field(pattern=r"^\d$")
    holder_name: str = Field(min_length=1, max_length=100)
    holder_document_type: DocumentType
    holder_document: str

    @field_validator("holder_document")
    @classmethod
    def _digits(cls, value: str) -> str:
        return only_digits(value)


class ProfileCreate(_In):
    bank_account_id: int
    name: str = Field(min_length=1, max_length=100)
    layout_id: str = Field(description="Ex.: ITAU_CNAB400")
    wallet: str = Field(pattern=r"^\d{3}$")
    company_name: str = Field(min_length=1, max_length=30)
    nosso_numero_min: int | None = Field(default=None, ge=1, le=99_999_999)
    nosso_numero_max: int | None = Field(default=None, ge=1, le=99_999_999)
    line_terminator: Literal["CRLF", "LF"] = "CRLF"


class TitleFields(_In):
    document_number: str = Field(min_length=1, max_length=10)
    species: str = Field(default="01", pattern=r"^\d{2}$")
    acceptance: Literal["A", "N"] = "N"
    issue_date: date
    due_date: date
    amount: Annotated[Decimal, Field(gt=0, max_digits=13, decimal_places=2)]
    nosso_numero: str | None = Field(default=None, pattern=r"^\d{1,8}$")
    payer: PayerIn
    send_boleto_by_email: bool = False
    guarantor: PartyIn | None = None
    interest_per_day: MoneyIn | None = None
    interest_start_date: date | None = None
    discount_amount: MoneyIn | None = None
    discount_limit_date: date | None = None
    rebate_amount: MoneyIn | None = None
    iof_amount: MoneyIn | None = None
    fine: FineIn | None = None
    instruction1: str | None = Field(default=None, pattern=r"^\d{2}$")
    instruction2: str | None = Field(default=None, pattern=r"^\d{2}$")
    protest_days: int | None = Field(default=None, ge=0, le=99)


class TitleCreate(TitleFields):
    profile_id: int


class TitlePatch(_In):
    """Atualização parcial; somente títulos OPEN ou REJECTED podem ser alterados."""

    document_number: str | None = Field(default=None, min_length=1, max_length=10)
    species: str | None = Field(default=None, pattern=r"^\d{2}$")
    acceptance: Literal["A", "N"] | None = None
    issue_date: date | None = None
    due_date: date | None = None
    amount: Annotated[Decimal, Field(gt=0, max_digits=13, decimal_places=2)] | None = None
    nosso_numero: str | None = Field(default=None, pattern=r"^\d{1,8}$")
    payer: PayerIn | None = None
    send_boleto_by_email: bool | None = None
    guarantor: PartyIn | None = None
    interest_per_day: MoneyIn | None = None
    interest_start_date: date | None = None
    discount_amount: MoneyIn | None = None
    discount_limit_date: date | None = None
    rebate_amount: MoneyIn | None = None
    iof_amount: MoneyIn | None = None
    fine: FineIn | None = None
    instruction1: str | None = Field(default=None, pattern=r"^\d{2}$")
    instruction2: str | None = Field(default=None, pattern=r"^\d{2}$")
    protest_days: int | None = Field(default=None, ge=0, le=99)


class RemittanceItemIn(_In):
    title_id: int
    command: RemittanceCommand = RemittanceCommand.REGISTER
    new_due_date: date | None = None


class RemittanceCreate(_In):
    profile_id: int
    items: list[RemittanceItemIn] = Field(min_length=1, max_length=5000)


class ResolveIn(_In):
    note: str = Field(min_length=3, max_length=2000)
