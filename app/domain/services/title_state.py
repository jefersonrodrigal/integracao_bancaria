"""Máquina de estados dos títulos (regra interna da aplicação).

``OVERDUE`` não é persistido: é derivado (``REGISTERED`` com vencimento passado), para não
confundir uma condição temporal com um evento confirmado pelo banco.
"""

from __future__ import annotations

from datetime import date

from app.domain.enums import TitleStatus as S
from app.domain.errors import InvalidStateTransition

ALLOWED_TRANSITIONS: dict[S, frozenset[S]] = {
    S.OPEN: frozenset({S.REMITTANCE_GENERATED}),
    # OPEN: remessa descartada antes do envio.
    S.REMITTANCE_GENERATED: frozenset({S.SENT_TO_BANK, S.OPEN, S.REGISTERED, S.REJECTED, S.PAID}),
    S.SENT_TO_BANK: frozenset({S.REGISTERED, S.REJECTED, S.PAID}),
    # OPEN: dados corrigidos após rejeição, prontos para nova remessa.
    S.REJECTED: frozenset({S.OPEN}),
    S.REGISTERED: frozenset({S.CANCEL_REQUESTED, S.PAID, S.CANCELLED}),
    # REGISTERED: baixa rejeitada pelo banco ou remessa de baixa descartada.
    S.CANCEL_REQUESTED: frozenset({S.REGISTERED, S.CANCELLED, S.PAID}),
    # PAID após baixa: pagamento recebido depois da baixa — sempre sinalizado na conciliação.
    S.CANCELLED: frozenset({S.PAID}),
    S.PAID: frozenset(),
}


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: S, target: S) -> None:
    if not can_transition(current, target):
        raise InvalidStateTransition(current.value, target.value)


def is_overdue(status: S, due_date: date, today: date) -> bool:
    return status in (S.REGISTERED, S.SENT_TO_BANK) and due_date < today
