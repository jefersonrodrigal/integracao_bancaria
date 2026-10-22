from datetime import date
from decimal import Decimal

import pytest

from app.cnab.fields import Field, FieldFormatError, FieldType, RecordLayout

N, X = FieldType.NUMERIC, FieldType.ALPHA


def test_numeric_left_zero_padded() -> None:
    assert Field("f", 1, 5, N).format("42") == "00042"
    assert Field("f", 1, 5, N).format(None) == "00000"


def test_numeric_rejects_overflow_and_non_digits() -> None:
    with pytest.raises(FieldFormatError):
        Field("f", 1, 2, N).format("123")
    with pytest.raises(FieldFormatError):
        Field("f", 1, 4, N).format("12a")
    with pytest.raises(FieldFormatError):
        Field("f", 1, 4, N).format(-1)


def test_assumed_decimal_matches_manual_example() -> None:
    # Manual p.5: 9(5)V9(2) com 876,54 => "0087654".
    assert Field("v", 1, 7, N, decimals=2).format(Decimal("876.54")) == "0087654"


def test_money_never_rounds() -> None:
    with pytest.raises(FieldFormatError, match="casas decimais"):
        Field("v", 1, 13, N, decimals=2).format(Decimal("1.005"))
    with pytest.raises(FieldFormatError):
        Field("v", 1, 13, N, decimals=2).format(Decimal("-1.00"))
    with pytest.raises(FieldFormatError):
        Field("v", 1, 3, N, decimals=2).format(Decimal("10.00"))


def test_alpha_uppercase_without_accents() -> None:
    assert Field("a", 1, 12, X).format("São João  ç") == "SAO JOAO C  "
    assert Field("a", 1, 3, X).format(None) == "   "


def test_alpha_rejects_invalid_chars_and_overflow() -> None:
    with pytest.raises(FieldFormatError, match="não permitidos"):
        Field("a", 1, 10, X).format("A|B")
    with pytest.raises(FieldFormatError, match="excede"):
        Field("a", 1, 3, X).format("ABCD")


def test_alpha_truncation_is_explicit_and_reported() -> None:
    warnings: list[str] = []
    assert Field("a", 1, 3, X, truncate=True).format("ABCDE", warnings) == "ABC"
    assert warnings and "truncado" in warnings[0]


def test_dates() -> None:
    assert Field("d", 1, 6, FieldType.DATE_DDMMYY).format(date(2026, 11, 1)) == "011126"
    assert Field("d", 1, 8, FieldType.DATE_DDMMYYYY).format(date(2026, 11, 1)) == "01112026"
    assert Field("d", 1, 6, FieldType.DATE_DDMMYY).format(None) == "000000"
    assert Field("d", 1, 6, FieldType.DATE_DDMMYY).parse("000000") is None
    assert Field("d", 1, 6, FieldType.DATE_DDMMYY).parse("281226") == date(2026, 12, 28)
    with pytest.raises(FieldFormatError):
        Field("d", 1, 6, FieldType.DATE_DDMMYY).parse("290226")  # 2026 não é bissexto
    with pytest.raises(FieldFormatError):
        Field("d", 1, 6, FieldType.DATE_DDMMYY).format(date(1999, 1, 1))


def test_layout_must_cover_all_positions_contiguously() -> None:
    with pytest.raises(ValueError, match="posição"):
        RecordLayout("x", (Field("a", 1, 2, X), Field("b", 4, 10, X)), length=10)
    with pytest.raises(ValueError, match="cobre"):
        RecordLayout("x", (Field("a", 1, 2, X),), length=10)


def test_layout_rejects_unknown_fields_and_checks_constants() -> None:
    layout = RecordLayout("x", (Field("t", 1, 1, N, constant="1"), Field("a", 2, 4, X)), 4)
    with pytest.raises(KeyError):
        layout.render({"zz": 1})
    assert layout.render({"a": "ok"}) == "1OK "
    _, errors = layout.parse("2OK ")
    assert [e.field for e in errors] == ["t"]
