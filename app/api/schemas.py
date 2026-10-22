"""Modelos de resposta da API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BankOut(_Out):
    id: int
    code: str
    name: str


class BankAccountOut(_Out):
    id: int
    bank_id: int
    agency: str
    account: str
    account_dac: str
    holder_name: str
    holder_document_type: str


class ProfileOut(_Out):
    id: int
    bank_account_id: int
    name: str
    layout_id: str
    manual_version: str
    wallet: str
    company_name: str
    nosso_numero_min: int | None
    nosso_numero_max: int | None
    next_nosso_numero: int | None
    line_terminator: str
    active: bool


class CustomerOut(_Out):
    id: int
    name: str
    document_type: str
    document: str
    email: str | None
    street: str
    district: str
    zip_code: str
    city: str
    state: str


class TitleOut(_Out):
    id: int
    profile_id: int
    company_reference: str
    document_number: str
    species: str
    acceptance: str
    issue_date: date
    due_date: date
    amount: Decimal
    nosso_numero: str | None
    nosso_numero_dac: str | None
    status: str
    is_overdue: bool = False
    customer: CustomerOut
    send_email: bool
    guarantor: dict[str, Any] | None
    interest_per_day: Decimal | None
    interest_start_date: date | None
    discount_amount: Decimal | None
    discount_limit_date: date | None
    rebate_amount: Decimal | None
    iof_amount: Decimal | None
    fine_type: str | None
    fine_date: date | None
    fine_value: Decimal | None
    instruction1: str | None
    instruction2: str | None
    protest_days: int | None
    last_bank_message: list[dict[str, str]] | None
    paid_amount: Decimal | None
    paid_at: date | None
    credit_date: date | None
    created_at: datetime
    updated_at: datetime


class RemittanceItemOut(_Out):
    title_id: int
    command: str
    occurrence_code: str
    line_number: int
    previous_status: str
    new_status: str
    new_due_date: date | None


class BankFileOut(_Out):
    id: int
    direction: str
    layout_id: str
    manual_version: str
    filename: str
    sha256: str
    size: int
    status: str
    validation_report: dict[str, Any] | None
    created_by: str
    created_at: datetime


class RemittanceOut(_Out):
    id: int
    profile_id: int
    status: str
    record_count: int
    title_count: int
    total_amount: Decimal
    created_by: str
    created_at: datetime
    sent_at: datetime | None
    bank_file: BankFileOut
    items: list[RemittanceItemOut]


class AttemptOut(_Out):
    id: int
    status: str
    actor: str
    started_at: datetime
    finished_at: datetime | None
    summary: dict[str, Any] | None
    error: str | None


class ReturnOut(BankFileOut):
    header_info: dict[str, Any] | None
    attempts: list[AttemptOut]


class OccurrenceOut(_Out):
    id: int
    bank_file_id: int
    line_number: int
    record_type: str
    occurrence_code: str
    occurrence_description: str | None
    effect: str | None
    occurrence_date: date | None
    title_id: int | None
    profile_id: int | None
    nosso_numero: str | None
    company_reference: str | None
    wallet: str | None
    amount: Decimal | None
    principal_amount: Decimal | None
    fee_amount: Decimal | None
    processing_status: str
    message: str | None
    parsed: dict[str, Any]
    raw_line: str
    created_at: datetime


class ReconciliationOut(_Out):
    id: int
    occurrence_id: int
    title_id: int | None
    status: str
    expected_amount: Decimal | None
    received_amount: Decimal | None
    difference: Decimal | None
    reasons: list[str]
    resolved: bool
    resolution_note: str | None
    resolved_by: str | None
    created_at: datetime


class MovementOut(_Out):
    id: int
    occurrence_id: int
    title_id: int | None
    kind: str
    amount: Decimal
    movement_date: date | None
    credit_date: date | None


class ValidationOut(BaseModel):
    valid: bool
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
