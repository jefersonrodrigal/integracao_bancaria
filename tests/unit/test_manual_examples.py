"""Exemplos numéricos publicados no próprio manual Itaú CNAB 400 (JANEIRO 2017)."""

from app.cnab.checksums import mod10
from app.cnab.layouts.itau.cnab400.adapter import ItauCnab400Adapter


def test_nota_23_nosso_numero_dac() -> None:
    # Nota 23 (p.35): 0057 / 72192 / 109 / 98712345 => "109/98712345-8".
    assert ItauCnab400Adapter().nosso_numero_dac("0057", "72192", "109", "98712345") == "8"


def test_anexo_4_nosso_numero_dac() -> None:
    # Anexo 4 (p.56-57): 0057 / 12345 / 110 / 12345678 => DAC 8.
    assert mod10("00571234511012345678") == 8


def test_nota_18_seu_numero_dac() -> None:
    # Nota 18 (p.25): seu número 1108954 => "1108954-7"; nosso número 198/98712345-1.
    assert mod10("1108954") == 7
    assert mod10("00577219219898712345") == 1


def test_account_dac_from_anexo_2_example() -> None:
    # Anexo 2 (p.55): "0057/12345-7".
    assert mod10("005712345") == 7


def test_anexo_3_linha_digitavel_fields() -> None:
    # Anexo 3 (p.56): DACs dos campos 1, 2 e 3 = 1, 8, 1.
    assert (mod10("341911012"), mod10("3456788005"), mod10("7123457000")) == (1, 8, 1)


def test_escritural_dac_uses_wallet_and_nosso_numero_only() -> None:
    # Nota 23: carteiras escriturais usam apenas carteira + nosso número.
    assert ItauCnab400Adapter().nosso_numero_dac("0057", "12345", "112", "00000001") == str(
        mod10("11200000001")
    )
