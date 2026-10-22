from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.cnab.layouts.itau.cnab400.adapter import ItauCnab400Adapter
from app.cnab.occurrence_codes import OccurrenceEffect
from tests.fixtures.builders import (
    Detail,
    return_detail,
    return_file,
    return_header,
    return_trailer,
)

adapter = ItauCnab400Adapter()


def test_parses_settlement() -> None:
    parsed = adapter.parse_return(
        return_file(
            [
                Detail(
                    "06",
                    nosso_numero="00000123",
                    reference="REF1",
                    principal=12345,
                    fee=250,
                    credit_date="241026",
                    liquidation="BL",
                ),
            ]
        )
    )
    assert parsed.report.is_valid, parsed.report.as_dict()
    d = parsed.details[0]
    assert d.info is not None and d.info.effect is OccurrenceEffect.SETTLEMENT
    assert (d.nosso_numero, d.company_reference, d.wallet) == ("00000123", "REF1", "109")
    assert d.amount == Decimal("123.45") and d.principal_amount == Decimal("123.45")
    assert d.fee_amount == Decimal("2.50")
    assert d.occurrence_date == date(2026, 10, 23) and d.credit_date == date(2026, 10, 24)
    assert d.extra["liquidation"]["resource"] == "DISPONÍVEL"
    assert parsed.header["sequencial_arquivo"] == "00001"


def test_rejection_codes_are_decoded_with_table_1() -> None:
    parsed = adapter.parse_return(return_file([Detail("03", messages="0811    ")]))
    codes = parsed.details[0].message_codes
    assert [c["code"] for c in codes] == ["08", "11"]
    assert all(c["table"] == "Tabela 1" for c in codes)


def test_payer_claim_complement_uses_table_6() -> None:
    parsed = adapter.parse_return(return_file([Detail("25", complement="1404")]))
    assert parsed.details[0].message_codes[0]["description"] == "NÃO RECEBEU A FATURA"


def test_unknown_code_has_no_info() -> None:
    parsed = adapter.parse_return(return_file([Detail("01")]))
    assert parsed.report.is_valid and parsed.details[0].info is None


def test_informational_flag_position_107() -> None:
    parsed = adapter.parse_return(return_file([Detail("06", flag107="I")]))
    assert parsed.details[0].informational_only


def test_invalid_detail_field_does_not_invalidate_file() -> None:
    parsed = adapter.parse_return(return_file([Detail("06", amount_raw="00000ABC12345")]))
    assert parsed.report.is_valid
    assert not parsed.details[0].is_valid
    assert any(w.code == "INVALID_DETAIL" for w in parsed.report.warnings)


def test_nosso_numero_dac_mismatch_is_warning() -> None:
    parsed = adapter.parse_return(
        return_file([Detail("02", nosso_numero="98712345", nn_dac="1", account="72192", dac="2")])
    )
    assert any(i.code == "NOSSO_NUMERO_DAC" for i in parsed.details[0].issues)
    good = adapter.parse_return(
        return_file([Detail("02", nosso_numero="98712345", nn_dac="8", account="72192", dac="2")])
    )
    assert not good.details[0].issues


def test_structural_errors_invalidate_file() -> None:
    content = return_file([Detail("06")]).replace(b"\r\n", b"\n", 1)
    assert "MIXED_TERMINATORS" in {i.code for i in adapter.parse_return(content).report.errors}
    lines = return_file([Detail("06")]).split(b"\r\n")
    lines[1] = lines[1][:-1]
    report = adapter.parse_return(b"\r\n".join(lines)).report
    assert "INVALID_RECORD_LENGTH" in {i.code for i in report.errors}


def test_lf_and_eof_char_accepted() -> None:
    content = return_file([Detail("06")], terminator="\n") + b"\x1a"
    report = adapter.parse_return(content).report
    assert report.is_valid and any(w.code == "EOF_CHAR" for w in report.warnings)


def test_trailer_count_mismatch_is_warning() -> None:
    lines = [return_header(), return_detail(Detail("06"), 2), return_trailer(details=5, seq=3)]
    parsed = adapter.parse_return("".join(x + "\r\n" for x in lines).encode())
    assert parsed.report.is_valid
    assert any(w.code == "DETAIL_COUNT" for w in parsed.report.warnings)


def test_cheque_record_layout_for_code_69() -> None:
    line = return_detail(Detail("69"), 2)
    line = line[:377] + "11" + line[379:]  # motivo de devolução (Tabela 9)
    lines = [return_header(), line, return_trailer(details=1, seq=3)]
    content = "".join(x + "\r\n" for x in lines).encode()
    detail = adapter.parse_return(content).details[0]
    assert detail.extra["layout"] == "retorno_detalhe_1_cheque"
    assert detail.message_codes[0]["description"].startswith("CHEQUE SEM FUNDOS")


def test_detection() -> None:
    assert adapter.looks_like_return(return_file([Detail("06")]))
    assert not adapter.looks_like_return(b"01REMESSA" + b" " * 391)
