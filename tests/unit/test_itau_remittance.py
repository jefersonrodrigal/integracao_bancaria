from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.cnab.base import CollectionProfileData, FineData, PartyData, RemittanceItemData
from app.cnab.layouts.itau.cnab400.adapter import ItauCnab400Adapter
from app.domain.enums import DocumentType, FineType, RemittanceCommand
from app.domain.errors import ValidationFailed
from tests.fixtures.builders import remittance_golden

GOLDEN = Path(__file__).parents[1] / "fixtures" / "golden" / "itau_cnab400_remessa_sintetica.rem"
adapter = ItauCnab400Adapter()

PROFILE = CollectionProfileData(
    agency="0057",
    account="12345",
    account_dac="7",
    company_name="EMPRESA SINTETICA LTDA",
    company_document_type=DocumentType.CNPJ,
    company_document="11222333000181",
    wallet="109",
)
PAYER = PartyData(
    "José da Silva",
    DocumentType.CPF,
    "52998224725",
    "Rua das Flores, 10",
    "Centro",
    "01001000",
    "São Paulo",
    "SP",
)
GUARANTOR = PartyData(
    "Avalista Sintético SA",
    DocumentType.CNPJ,
    "11444777000161",
    "Av Paulista, 1000",
    "Bela Vista",
    "01310100",
    "São Paulo",
    "SP",
)
REGISTER = RemittanceItemData(
    command=RemittanceCommand.REGISTER,
    company_reference="REF0000000000000000000001",
    nosso_numero="123",
    document_number="NF0001",
    issue_date=date(2026, 10, 1),
    due_date=date(2026, 11, 1),
    amount=Decimal("123.45"),
    species="01",
    acceptance="N",
    payer=PAYER,
    guarantor=GUARANTOR,
    instruction1="09",
    protest_days=5,
    interest_per_day=Decimal("0.05"),
    interest_start_date=date(2026, 11, 2),
    discount_amount=Decimal("10.00"),
    discount_limit_date=date(2026, 10, 25),
    fine=FineData(FineType.PERCENT, date(2026, 11, 2), Decimal("2.00")),
)
WRITE_OFF = replace(
    REGISTER,
    command=RemittanceCommand.WRITE_OFF,
    nosso_numero="00000077",
    company_reference="REF2",
    amount=Decimal("500.00"),
)
DUE_CHANGE = replace(
    REGISTER,
    command=RemittanceCommand.CHANGE_DUE_DATE,
    nosso_numero="78",
    company_reference="REF3",
    amount=Decimal("70.00"),
    new_due_date=date(2026, 12, 15),
)


def _generate() -> bytes:
    return adapter.generate_remittance(
        PROFILE, [REGISTER, WRITE_OFF, DUE_CHANGE], date(2026, 10, 22)
    ).content


def test_golden_file_matches_independent_builder() -> None:
    assert GOLDEN.read_bytes() == remittance_golden()


def test_generated_remittance_matches_golden_byte_for_byte() -> None:
    assert _generate() == GOLDEN.read_bytes()


def test_generated_remittance_passes_validation() -> None:
    report = adapter.validate_remittance(_generate())
    assert report.is_valid, report.as_dict()
    assert not report.warnings


def test_lf_terminator_profile() -> None:
    content = adapter.generate_remittance(
        replace(PROFILE, line_terminator="LF"), [REGISTER], date(2026, 10, 22)
    ).content
    assert b"\r" not in content and content.count(b"\n") == 5
    assert adapter.validate_remittance(content).is_valid


def test_generation_refuses_invalid_items_with_context() -> None:
    bad = replace(REGISTER, amount=Decimal("0"), reference_id=99)
    with pytest.raises(ValidationFailed) as exc:
        adapter.generate_remittance(PROFILE, [bad], date(2026, 10, 22))
    assert any(i.code == "AMOUNT" and i.context["title_id"] == 99 for i in exc.value.issues)


def test_generation_refuses_duplicated_nosso_numero() -> None:
    with pytest.raises(ValidationFailed) as exc:
        adapter.generate_remittance(
            PROFILE, [REGISTER, replace(REGISTER, company_reference="X")], date(2026, 10, 22)
        )
    assert {"NOSSO_NUMERO_DUPLICATED", "REFERENCE_DUPLICATED"} & {i.code for i in exc.value.issues}


def _lines() -> list[str]:
    return GOLDEN.read_bytes().decode("ascii").split("\r\n")[:-1]


def _join(lines: list[str]) -> bytes:
    return "".join(line + "\r\n" for line in lines).encode("ascii")


def _codes(content: bytes) -> set[str]:
    return {i.code for i in adapter.validate_remittance(content).errors}


def _patch(line: str, start: int, value: str) -> str:
    return line[: start - 1] + value + line[start - 1 + len(value) :]


def test_validation_detects_wrong_length() -> None:
    lines = _lines()
    lines[1] = lines[1][:399]
    assert "INVALID_RECORD_LENGTH" in _codes(_join(lines))


def test_validation_detects_sequence_error() -> None:
    lines = _lines()
    lines[2] = _patch(lines[2], 395, "000009")
    assert "INVALID_SEQUENCE" in _codes(_join(lines))


def test_validation_detects_missing_trailer_and_header() -> None:
    assert "TRAILER_MISSING" in _codes(_join(_lines()[:-1]))
    assert "HEADER_MISSING" in _codes(_join(_lines()[1:]))


def test_validation_detects_non_ascii() -> None:
    lines = _lines()
    content = _join(lines).replace(b"JOSE", "JOSÉ".encode("latin-1")[:4])
    assert "NON_ASCII" in _codes(content)


def test_validation_detects_wallet_code_mismatch() -> None:
    lines = _lines()
    lines[1] = _patch(lines[1], 108, "U")
    assert "WALLET_CODE" in _codes(_join(lines))


def test_validation_detects_escritural_with_nosso_numero() -> None:
    lines = _lines()
    lines[1] = _patch(lines[1], 84, "112")
    assert "NOSSO_NUMERO" in _codes(_join(lines))


def test_validation_detects_duplicated_and_orphan_type2() -> None:
    lines = _lines()
    dup = [*lines[:3], lines[2], *lines[3:]]
    dup = [_patch(line, 395, f"{i + 1:06d}") for i, line in enumerate(dup)]
    assert "DUPLICATED_FINE" in _codes(_join(dup))
    orphan = [lines[0], lines[2], lines[-1]]
    orphan = [_patch(line, 395, f"{i + 1:06d}") for i, line in enumerate(orphan)]
    assert "ORPHAN_RECORD" in _codes(_join(orphan))


def test_validation_detects_fine_before_due_date() -> None:
    lines = _lines()
    lines[2] = _patch(lines[2], 3, "31102026")
    assert "FINE_DATE" in _codes(_join(lines))


def test_validation_detects_missing_payer_data() -> None:
    lines = _lines()
    lines[1] = _patch(lines[1], 235, " " * 40)
    lines[1] = _patch(lines[1], 350, "XX")
    codes = _codes(_join(lines))
    assert {"PAYER_NAME", "STATE"} <= codes


def test_validation_detects_unknown_occurrence() -> None:
    lines = _lines()
    lines[1] = _patch(lines[1], 109, "99")
    assert "OCCURRENCE" in _codes(_join(lines))
