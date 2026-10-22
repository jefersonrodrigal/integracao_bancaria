from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.cnab.base import FineData
from app.cnab.layouts.itau.cnab400.adapter import ItauCnab400Adapter
from app.domain.enums import FineType
from tests.unit.test_itau_remittance import PROFILE, REGISTER

adapter = ItauCnab400Adapter()


def codes(item: object = REGISTER, profile: object = PROFILE) -> set[str]:
    return {i.code for i in adapter.validate_item(profile, item)}  # type: ignore[arg-type]


def test_valid_item_has_no_issues() -> None:
    assert codes() == set()


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"amount": Decimal("0")}, "AMOUNT"),
        ({"amount": Decimal("10000000.01")}, "AMOUNT_MAX"),
        ({"species": "10"}, "SPECIES"),
        ({"acceptance": "S"}, "ACCEPTANCE"),
        ({"due_date": date(2026, 9, 1)}, "DUE_BEFORE_ISSUE"),
        ({"document_number": "12345678901"}, "DOCUMENT_NUMBER"),
        ({"discount_amount": Decimal("120.00")}, "DISCOUNT_MAX"),
        ({"discount_limit_date": None}, "DISCOUNT_DATE"),
        ({"rebate_amount": Decimal("123.45")}, "REBATE"),
        ({"iof_amount": Decimal("1.00")}, "IOF_WALLET"),
        ({"payer_email": "pagador@example.com"}, "EMAIL_WALLET"),
        ({"instruction1": "93"}, "INSTRUCTION_UNSUPPORTED"),
        ({"instruction1": "01"}, "INSTRUCTION"),
        ({"instruction2": "66"}, "PROTEST_AND_NEGATIVATION"),
        ({"instruction1": "05", "protest_days": 5}, "DAYS_WITHOUT_INSTRUCTION"),
        ({"nosso_numero": None}, "NOSSO_NUMERO_REQUIRED"),
        ({"fine": FineData(FineType.PERCENT, date(2026, 10, 30), Decimal("2"))}, "FINE_DATE"),
        ({"fine": FineData(FineType.PERCENT, date(2026, 11, 2), Decimal("100"))}, "FINE_VALUE"),
        ({"fine": FineData(FineType.FIXED, date(2026, 11, 2), Decimal("123.45"))}, "FINE_VALUE"),
        ({"species": "18"}, "PROPOSAL_INSTRUCTIONS"),
    ],
)
def test_item_rules(changes: dict[str, object], expected: str) -> None:
    assert expected in codes(replace(REGISTER, **changes))  # type: ignore[arg-type]


def test_payer_rules() -> None:
    payer = replace(
        REGISTER.payer, document="52998224724", zip_code="0100100", state="XX", street=" ", name=""
    )
    found = codes(replace(REGISTER, payer=payer))
    assert {"DOCUMENT", "ZIP_CODE", "STATE", "STREET_REQUIRED", "NAME_REQUIRED"} <= found


def test_escritural_wallet_rejects_company_nosso_numero_and_accepts_email() -> None:
    profile = replace(PROFILE, wallet="112")
    assert "NOSSO_NUMERO_BY_BANK" in codes(REGISTER, profile)
    ok = replace(REGISTER, nosso_numero=None, payer_email="pagador@example.com")
    assert codes(ok, profile) == set()


def test_wallet_115_is_escritural_with_free_nosso_numero() -> None:
    assert codes(REGISTER, replace(PROFILE, wallet="115")) == set()


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"account_dac": "8"}, "ACCOUNT_DAC_MISMATCH"),
        ({"wallet": "104"}, "WALLET_UNSUPPORTED"),
        ({"wallet": "150"}, "WALLET_UNSUPPORTED"),
        ({"wallet": "999"}, "WALLET"),
        ({"wallet": "108"}, "NOSSO_NUMERO_RANGE"),
        ({"company_name": "X" * 31}, "COMPANY_NAME"),
        ({"company_document": "11222333000180"}, "COMPANY_DOCUMENT"),
    ],
)
def test_profile_rules(changes: dict[str, object], expected: str) -> None:
    issues = adapter.validate_profile(replace(PROFILE, **changes))  # type: ignore[arg-type]
    assert expected in {i.code for i in issues}


def test_every_issue_carries_a_reference() -> None:
    bad = replace(REGISTER, amount=Decimal("0"), species="10", instruction1="93")
    assert all(i.reference for i in adapter.validate_item(PROFILE, bad))
