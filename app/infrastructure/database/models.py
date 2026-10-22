"""Modelos persistentes."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, Money, TimestampMixin, utcnow


class Bank(Base, TimestampMixin):
    __tablename__ = "bank"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class BankAccount(Base, TimestampMixin):
    __tablename__ = "bank_account"
    __table_args__ = (UniqueConstraint("bank_id", "agency", "account", "account_dac"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id"))
    agency: Mapped[str] = mapped_column(String(4))
    account: Mapped[str] = mapped_column(String(5))
    account_dac: Mapped[str] = mapped_column(String(1))
    holder_name: Mapped[str] = mapped_column(String(100))
    holder_document_type: Mapped[str] = mapped_column(String(4))
    holder_document: Mapped[str] = mapped_column(String(14))
    bank: Mapped[Bank] = relationship()


class BankIntegrationProfile(Base, TimestampMixin):
    """Perfil de cobrança: conta + carteira + leiaute/versão do manual."""

    __tablename__ = "bank_integration_profile"
    __table_args__ = (UniqueConstraint("bank_account_id", "wallet"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("bank_account.id"))
    name: Mapped[str] = mapped_column(String(100))
    layout_id: Mapped[str] = mapped_column(String(40))
    manual_version: Mapped[str] = mapped_column(String(20))
    wallet: Mapped[str] = mapped_column(String(3))
    company_name: Mapped[str] = mapped_column(String(30))
    nosso_numero_min: Mapped[int | None] = mapped_column(Integer)
    nosso_numero_max: Mapped[int | None] = mapped_column(Integer)
    next_nosso_numero: Mapped[int | None] = mapped_column(Integer)
    line_terminator: Mapped[str] = mapped_column(String(4), default="CRLF")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    bank_account: Mapped[BankAccount] = relationship()


class Customer(Base, TimestampMixin):
    __tablename__ = "customer"
    __table_args__ = (UniqueConstraint("document_type", "document"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    document_type: Mapped[str] = mapped_column(String(4))
    document: Mapped[str] = mapped_column(String(14))
    email: Mapped[str | None] = mapped_column(String(120))
    street: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(60), default="")
    zip_code: Mapped[str] = mapped_column(String(8))
    city: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(2))


class ReceivableTitle(Base, TimestampMixin):
    __tablename__ = "receivable_title"
    __table_args__ = (
        UniqueConstraint("profile_id", "nosso_numero"),
        Index("ix_receivable_title_status", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("bank_integration_profile.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"))
    company_reference: Mapped[str] = mapped_column(String(25), unique=True)
    document_number: Mapped[str] = mapped_column(String(10))
    species: Mapped[str] = mapped_column(String(2))
    acceptance: Mapped[str] = mapped_column(String(1))
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Money())
    nosso_numero: Mapped[str | None] = mapped_column(String(8))
    nosso_numero_dac: Mapped[str | None] = mapped_column(String(1))
    interest_per_day: Mapped[Decimal | None] = mapped_column(Money())
    interest_start_date: Mapped[date | None] = mapped_column(Date)
    discount_amount: Mapped[Decimal | None] = mapped_column(Money())
    discount_limit_date: Mapped[date | None] = mapped_column(Date)
    rebate_amount: Mapped[Decimal | None] = mapped_column(Money())
    iof_amount: Mapped[Decimal | None] = mapped_column(Money())
    fine_type: Mapped[str | None] = mapped_column(String(10))
    fine_date: Mapped[date | None] = mapped_column(Date)
    fine_value: Mapped[Decimal | None] = mapped_column(Money())
    instruction1: Mapped[str | None] = mapped_column(String(2))
    instruction2: Mapped[str | None] = mapped_column(String(2))
    protest_days: Mapped[int | None] = mapped_column(Integer)
    guarantor: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    send_email: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30))
    last_bank_message: Mapped[list[dict[str, str]] | None] = mapped_column(JSON)
    paid_amount: Mapped[Decimal | None] = mapped_column(Money())
    paid_at: Mapped[date | None] = mapped_column(Date)
    credit_date: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    customer: Mapped[Customer] = relationship()
    profile: Mapped[BankIntegrationProfile] = relationship()

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012


class BankFile(Base):
    __tablename__ = "bank_file"
    id: Mapped[int] = mapped_column(primary_key=True)
    direction: Mapped[str] = mapped_column(String(12))
    layout_id: Mapped[str] = mapped_column(String(40))
    manual_version: Mapped[str] = mapped_column(String(20))
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("bank_integration_profile.id"))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    # Preenchido só em retornos: impede reimportação do mesmo arquivo.
    dedup_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    size: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30))
    validation_report: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    header_info: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    attempts: Mapped[list[FileProcessingAttempt]] = relationship(
        back_populates="bank_file", order_by="FileProcessingAttempt.id"
    )


class FileProcessingAttempt(Base):
    __tablename__ = "file_processing_attempt"
    id: Mapped[int] = mapped_column(primary_key=True)
    bank_file_id: Mapped[int] = mapped_column(ForeignKey("bank_file.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String(100))
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    bank_file: Mapped[BankFile] = relationship(back_populates="attempts")


class RemittanceBatch(Base):
    __tablename__ = "remittance_batch"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("bank_integration_profile.id"))
    bank_file_id: Mapped[int] = mapped_column(ForeignKey("bank_file.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20))
    record_count: Mapped[int] = mapped_column(Integer)
    title_count: Mapped[int] = mapped_column(Integer)
    total_amount: Mapped[Decimal] = mapped_column(Money())
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bank_file: Mapped[BankFile] = relationship()
    items: Mapped[list[RemittanceBatchItem]] = relationship(
        back_populates="batch", order_by="RemittanceBatchItem.line_number"
    )


class RemittanceBatchItem(Base):
    __tablename__ = "remittance_batch_item"
    __table_args__ = (UniqueConstraint("batch_id", "title_id", "command"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("remittance_batch.id"))
    title_id: Mapped[int] = mapped_column(ForeignKey("receivable_title.id"), index=True)
    command: Mapped[str] = mapped_column(String(20))
    occurrence_code: Mapped[str] = mapped_column(String(2))
    line_number: Mapped[int] = mapped_column(Integer)
    previous_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    new_due_date: Mapped[date | None] = mapped_column(Date)
    batch: Mapped[RemittanceBatch] = relationship(back_populates="items")


class BankOccurrence(Base):
    __tablename__ = "bank_occurrence"
    id: Mapped[int] = mapped_column(primary_key=True)
    bank_file_id: Mapped[int] = mapped_column(ForeignKey("bank_file.id"), index=True)
    line_number: Mapped[int] = mapped_column(Integer)
    raw_line: Mapped[str] = mapped_column(String(400))
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("bank_integration_profile.id"))
    title_id: Mapped[int | None] = mapped_column(ForeignKey("receivable_title.id"), index=True)
    record_type: Mapped[str] = mapped_column(String(1))
    occurrence_code: Mapped[str] = mapped_column(String(4), index=True)
    occurrence_description: Mapped[str | None] = mapped_column(String(200))
    effect: Mapped[str | None] = mapped_column(String(30))
    occurrence_date: Mapped[date | None] = mapped_column(Date)
    nosso_numero: Mapped[str | None] = mapped_column(String(8))
    company_reference: Mapped[str | None] = mapped_column(String(25))
    wallet: Mapped[str | None] = mapped_column(String(3))
    amount: Mapped[Decimal | None] = mapped_column(Money())
    principal_amount: Mapped[Decimal | None] = mapped_column(Money())
    fee_amount: Mapped[Decimal | None] = mapped_column(Money())
    processing_status: Mapped[str] = mapped_column(String(30), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    parsed: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_result"
    id: Mapped[int] = mapped_column(primary_key=True)
    occurrence_id: Mapped[int] = mapped_column(ForeignKey("bank_occurrence.id"), unique=True)
    title_id: Mapped[int | None] = mapped_column(ForeignKey("receivable_title.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    expected_amount: Mapped[Decimal | None] = mapped_column(Money())
    received_amount: Mapped[Decimal | None] = mapped_column(Money())
    difference: Mapped[Decimal | None] = mapped_column(Money())
    reasons: Mapped[list[str]] = mapped_column(JSON)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FinancialMovement(Base):
    __tablename__ = "financial_movement"
    __table_args__ = (UniqueConstraint("occurrence_id", "kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    occurrence_id: Mapped[int] = mapped_column(ForeignKey("bank_occurrence.id"))
    title_id: Mapped[int | None] = mapped_column(ForeignKey("receivable_title.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    # Positivo = crédito ao beneficiário; negativo = débito (tarifas/custas).
    amount: Mapped[Decimal] = mapped_column(Money())
    movement_date: Mapped[date | None] = mapped_column(Date)
    credit_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_event"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(40))
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
