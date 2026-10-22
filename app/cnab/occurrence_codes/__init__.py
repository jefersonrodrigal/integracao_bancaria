"""Classificação genérica (interna) dos efeitos de ocorrências bancárias.

Cada adaptador mapeia os códigos do seu manual para um destes efeitos. O efeito é uma
regra interna da aplicação; o significado do código vem do manual do banco.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OccurrenceEffect(StrEnum):
    ENTRY_CONFIRMED = "ENTRY_CONFIRMED"
    ENTRY_REJECTED = "ENTRY_REJECTED"
    SETTLEMENT = "SETTLEMENT"
    PARTIAL_SETTLEMENT = "PARTIAL_SETTLEMENT"
    WRITE_OFF = "WRITE_OFF"
    WRITE_OFF_REJECTED = "WRITE_OFF_REJECTED"
    DUE_DATE_CHANGED = "DUE_DATE_CHANGED"
    INSTRUCTION_REJECTED = "INSTRUCTION_REJECTED"
    FEE = "FEE"
    INFORMATIONAL = "INFORMATIONAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class OccurrenceInfo:
    code: str
    description: str
    effect: OccurrenceEffect
    reference: str
