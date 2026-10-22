"""Enumerações internas do domínio. Não confundir com códigos bancários."""

from __future__ import annotations

from enum import StrEnum


class TitleStatus(StrEnum):
    OPEN = "OPEN"
    REMITTANCE_GENERATED = "REMITTANCE_GENERATED"
    SENT_TO_BANK = "SENT_TO_BANK"
    REGISTERED = "REGISTERED"
    REJECTED = "REJECTED"
    PAID = "PAID"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class DocumentType(StrEnum):
    CPF = "CPF"
    CNPJ = "CNPJ"


class RemittanceCommand(StrEnum):
    """Comandos internos convertidos em códigos de ocorrência pelo adaptador."""

    REGISTER = "REGISTER"
    WRITE_OFF = "WRITE_OFF"
    CHANGE_DUE_DATE = "CHANGE_DUE_DATE"


class FineType(StrEnum):
    FIXED = "FIXED"
    PERCENT = "PERCENT"


class BatchStatus(StrEnum):
    GENERATED = "GENERATED"
    SENT = "SENT"
    DISCARDED = "DISCARDED"


class FileDirection(StrEnum):
    REMITTANCE = "REMITTANCE"
    RETURN = "RETURN"


class FileStatus(StrEnum):
    GENERATED = "GENERATED"
    RECEIVED = "RECEIVED"
    INVALID = "INVALID"
    PROCESSED = "PROCESSED"
    PARTIALLY_PROCESSED = "PARTIALLY_PROCESSED"


class AttemptStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class OccurrenceStatus(StrEnum):
    APPLIED = "APPLIED"
    INFORMATIONAL = "INFORMATIONAL"
    UNMATCHED = "UNMATCHED"
    UNKNOWN_CODE = "UNKNOWN_CODE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INVALID = "INVALID"


class ReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    DIVERGENT = "DIVERGENT"
    UNMATCHED = "UNMATCHED"


class MovementKind(StrEnum):
    SETTLEMENT = "SETTLEMENT"
    PARTIAL_SETTLEMENT = "PARTIAL_SETTLEMENT"
    FEE = "FEE"
