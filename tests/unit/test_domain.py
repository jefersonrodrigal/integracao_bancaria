from datetime import date

import pytest

from app.domain.enums import TitleStatus as S
from app.domain.errors import InvalidStateTransition
from app.domain.services.title_state import can_transition, ensure_transition, is_overdue
from app.domain.value_objects import is_valid_cnpj, is_valid_cpf


def test_documents() -> None:
    assert is_valid_cpf("52998224725")
    assert not is_valid_cpf("52998224724")
    assert not is_valid_cpf("11111111111")
    assert is_valid_cnpj("11222333000181")
    assert not is_valid_cnpj("11222333000180")
    assert not is_valid_cnpj("12ABC34501DE35")  # CNPJ alfanumérico não cabe em 9(14)


@pytest.mark.parametrize(
    ("current", "target", "allowed"),
    [
        (S.OPEN, S.REMITTANCE_GENERATED, True),
        (S.OPEN, S.REGISTERED, False),
        (S.SENT_TO_BANK, S.REGISTERED, True),
        (S.REGISTERED, S.CANCEL_REQUESTED, True),
        (S.CANCEL_REQUESTED, S.REGISTERED, True),
        (S.PAID, S.CANCELLED, False),
        (S.REJECTED, S.OPEN, True),
        (S.REJECTED, S.PAID, False),
    ],
)
def test_transitions(current: S, target: S, allowed: bool) -> None:
    assert can_transition(current, target) is allowed


def test_ensure_transition_raises() -> None:
    with pytest.raises(InvalidStateTransition):
        ensure_transition(S.PAID, S.OPEN)


def test_overdue_is_derived() -> None:
    assert is_overdue(S.REGISTERED, date(2026, 1, 1), date(2026, 1, 2))
    assert not is_overdue(S.PAID, date(2026, 1, 1), date(2026, 1, 2))
