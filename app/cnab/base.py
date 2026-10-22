"""Contratos entre a aplicação e os adaptadores de leiaute bancário.

Os DTOs são independentes do ORM e de qualquer leiaute: um adaptador CNAB 240 ou de outro
banco recebe os mesmos dados e devolve as mesmas estruturas.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol

from app.cnab.occurrence_codes import OccurrenceInfo
from app.domain.enums import DocumentType, FineType, RemittanceCommand
from app.domain.errors import Issue


class LayoutFamily(StrEnum):
    CNAB400 = "CNAB400"
    CNAB240 = "CNAB240"


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def error(self, code: str, message: str, **kwargs: Any) -> None:
        self.issues.append(Issue(code=code, message=message, severity="error", **kwargs))

    def warning(self, code: str, message: str, **kwargs: Any) -> None:
        self.issues.append(Issue(code=code, message=message, severity="warning", **kwargs))

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.is_valid,
            "errors": [i.as_dict() for i in self.errors],
            "warnings": [i.as_dict() for i in self.warnings],
        }


@dataclass(frozen=True, slots=True)
class PartyData:
    name: str
    document_type: DocumentType
    document: str
    street: str
    district: str
    zip_code: str
    city: str
    state: str


@dataclass(frozen=True, slots=True)
class FineData:
    type: FineType
    start_date: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class CollectionProfileData:
    agency: str
    account: str
    account_dac: str
    company_name: str
    company_document_type: DocumentType
    company_document: str
    wallet: str
    nosso_numero_min: int | None = None
    nosso_numero_max: int | None = None
    line_terminator: str = "CRLF"


@dataclass(frozen=True, slots=True)
class RemittanceItemData:
    command: RemittanceCommand
    company_reference: str
    nosso_numero: str | None
    document_number: str
    issue_date: date
    due_date: date
    amount: Decimal
    species: str
    acceptance: str
    payer: PartyData
    payer_email: str | None = None
    guarantor: PartyData | None = None
    instruction1: str | None = None
    instruction2: str | None = None
    protest_days: int | None = None
    interest_per_day: Decimal | None = None
    interest_start_date: date | None = None
    discount_amount: Decimal | None = None
    discount_limit_date: date | None = None
    rebate_amount: Decimal | None = None
    iof_amount: Decimal | None = None
    fine: FineData | None = None
    new_due_date: date | None = None
    reference_id: int | None = None  # id interno, apenas para mensagens de erro


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    content: bytes
    record_count: int
    line_numbers: dict[str, int]  # company_reference -> linha do registro detalhe
    warnings: list[Issue]


@dataclass
class ReturnDetail:
    """Registro de detalhe de retorno já interpretado pelo adaptador."""

    line_number: int
    raw_line: str
    record_type: str
    occurrence_code: str
    agency: str | None = None
    account: str | None = None
    account_dac: str | None = None
    wallet: str | None = None
    nosso_numero: str | None = None
    nosso_numero_dac: str | None = None
    company_reference: str | None = None
    document_number: str | None = None
    occurrence_date: date | None = None
    due_date: date | None = None
    credit_date: date | None = None
    amount: Decimal | None = None
    fee_amount: Decimal = Decimal("0")
    iof_amount: Decimal = Decimal("0")
    rebate_amount: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    principal_amount: Decimal = Decimal("0")
    interest_fine_amount: Decimal = Decimal("0")
    other_credits: Decimal = Decimal("0")
    payer_name: str | None = None
    liquidation_code: str | None = None
    accounting_flag: str | None = None
    informational_only: bool = False
    message_codes: list[dict[str, str]] = field(default_factory=list)
    info: OccurrenceInfo | None = None
    issues: list[Issue] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


@dataclass
class ParsedReturn:
    report: ValidationReport
    header: dict[str, Any] = field(default_factory=dict)
    trailer: dict[str, Any] = field(default_factory=dict)
    details: list[ReturnDetail] = field(default_factory=list)


class BankLayoutAdapter(Protocol):
    """Interface implementada por cada par banco/leiaute (ex.: Itaú CNAB 400)."""

    layout_id: str
    bank_code: str
    family: LayoutFamily
    manual_version: str

    def validate_profile(self, profile: CollectionProfileData) -> list[Issue]: ...

    def nosso_numero_assigned_by_bank(self, wallet: str) -> bool: ...

    def validate_item(
        self, profile: CollectionProfileData, item: RemittanceItemData
    ) -> list[Issue]: ...

    def generate_remittance(
        self,
        profile: CollectionProfileData,
        items: Sequence[RemittanceItemData],
        generated_on: date,
    ) -> GeneratedFile: ...

    def validate_remittance(self, content: bytes) -> ValidationReport: ...

    def parse_return(self, content: bytes) -> ParsedReturn: ...

    def validate_return(self, content: bytes) -> ValidationReport: ...

    def describe_occurrence(self, code: str) -> OccurrenceInfo | None: ...

    def nosso_numero_dac(
        self, agency: str, account: str, wallet: str, nosso_numero: str
    ) -> str: ...

    def looks_like_return(self, content: bytes) -> bool: ...
