"""Construtores de arquivos CNAB 400 Itaú **SINTÉTICOS** para testes.

Não são arquivos oficiais do Itaú. As posições foram digitadas diretamente das tabelas do
manual (JANEIRO 2017, p.7-17), sem reutilizar os leiautes de ``app.cnab``, para que os
testes verifiquem a implementação de forma independente.
"""

from __future__ import annotations

from dataclasses import dataclass


def seg(*parts: str) -> str:
    line = "".join(parts)
    assert len(line) == 400, f"linha com {len(line)} posições"
    return line


def a(value: str, size: int) -> str:
    assert len(value) <= size
    return value.ljust(size)


def n(value: int | str, size: int) -> str:
    text = str(value)
    assert text.isdigit() and len(text) <= size
    return text.zfill(size)


def sp(size: int) -> str:
    return " " * size


def z(size: int) -> str:
    return "0" * size


# ------------------------------------------------------------------ retorno (p.13-17)
def return_header(
    agency: str = "0057",
    account: str = "12345",
    dac: str = "7",
    generated: str = "221026",
    credit: str = "231026",
    file_seq: int = 1,
) -> str:
    return seg(
        "0",
        "2",
        "RETORNO",
        "01",
        a("COBRANCA", 15),
        agency,
        "00",
        account,
        dac,
        sp(8),
        a("EMPRESA SINTETICA LTDA", 30),
        "341",
        a("BANCO ITAU SA", 15),
        generated,
        n(1600, 5),
        "BPI",
        n(file_seq, 5),
        credit,
        sp(275),
        n(1, 6),
    )


@dataclass
class Detail:
    code: str
    nosso_numero: str = "00000001"
    nn_dac: str = "0"
    wallet: str = "109"
    wallet_code: str = "I"
    reference: str = ""
    document: str = "NF0001"
    occurred: str = "231026"
    due: str = "011126"
    amount: int = 12345  # centavos
    fee: int = 0
    rebate: int = 0
    discount: int = 0
    principal: int = 0
    interest: int = 0
    credit_date: str = "      "
    messages: str = sp(8)
    complement: str = sp(4)
    liquidation: str = "  "
    flag107: str = " "
    agency: str = "0057"
    account: str = "12345"
    dac: str = "7"
    amount_raw: str | None = None


def return_detail(d: Detail, seq: int) -> str:
    amount = d.amount_raw if d.amount_raw is not None else n(d.amount, 13)
    return seg(
        "1",
        "02",
        "11222333000181",
        d.agency,
        "00",
        d.account,
        d.dac,
        sp(8),
        a(d.reference, 25),
        d.nosso_numero,
        sp(12),
        d.wallet,
        d.nosso_numero,
        d.nn_dac,
        sp(12),
        d.flag107,
        d.wallet_code,
        d.code,
        d.occurred,
        a(d.document, 10),
        d.nosso_numero,
        sp(12),
        d.due,
        amount,
        "341",
        "0057",
        "0",
        "01",
        n(d.fee, 13),
        sp(26),
        z(13),
        n(d.rebate, 13),
        n(d.discount, 13),
        n(d.principal, 13),
        n(d.interest, 13),
        z(13),
        " ",
        sp(2),
        d.credit_date,
        d.complement,
        sp(6),
        z(13),
        a("PAGADOR SINTETICO", 30),
        sp(23),
        d.messages,
        sp(7),
        d.liquidation,
        n(seq, 6),
    )


def return_trailer(details: int, seq: int, total_cents: int = 0) -> str:
    return seg(
        "9",
        "2",
        "01",
        "341",
        sp(10),
        z(8),
        z(14),
        sp(8),
        sp(10),
        z(8),
        z(14),
        sp(8),
        sp(90),
        z(8),
        z(14),
        sp(8),
        n(1, 5),
        n(details, 8),
        n(total_cents, 14),
        sp(160),
        n(seq, 6),
    )


def return_file(details: list[Detail], terminator: str = "\r\n", **header: str) -> bytes:
    lines = [return_header(**header)]
    lines += [return_detail(d, i + 2) for i, d in enumerate(details)]
    lines.append(return_trailer(len(details), len(lines) + 1))
    return "".join(line + terminator for line in lines).encode("latin-1")


# ------------------------------------------------------------------ remessa (p.7-12)
def remittance_golden() -> bytes:
    """Remessa esperada para o cenário de ``tests/unit/test_itau_remittance.py``."""
    header = seg(
        "0",
        "1",
        "REMESSA",
        "01",
        a("COBRANCA", 15),
        "0057",
        "00",
        "12345",
        "7",
        sp(8),
        a("EMPRESA SINTETICA LTDA", 30),
        "341",
        a("BANCO ITAU SA", 15),
        "221026",
        sp(294),
        n(1, 6),
    )
    register = seg(
        "1",
        "02",
        "11222333000181",
        "0057",
        "00",
        "12345",
        "7",
        sp(4),
        "0000",
        a("REF0000000000000000000001", 25),
        "00000123",
        z(13),
        "109",
        sp(21),
        "I",
        "01",
        a("NF0001", 10),
        "011126",
        n(12345, 13),
        "341",
        "00000",
        "01",
        "N",
        "011026",
        "09",
        sp(2),
        n(5, 13),
        "251026",
        n(1000, 13),
        z(13),
        z(13),
        "01",
        n("52998224725", 14),
        a("JOSE DA SILVA", 40),
        a("RUA DAS FLORES, 10", 40),
        a("CENTRO", 12),
        "01001000",
        a("SAO PAULO", 15),
        "SP",
        a("AVALISTA SINTETICO SA", 30),
        sp(4),
        "021126",
        "05",
        " ",
        n(2, 6),
    )
    fine = seg("2", "2", "02112026", n(200, 13), sp(371), n(3, 6))
    type5 = seg(
        "5",
        sp(120),
        "02",
        "11444777000161",
        a("AV PAULISTA, 1000", 40),
        a("BELA VISTA", 12),
        "01310100",
        a("SAO PAULO", 15),
        "SP",
        sp(180),
        n(4, 6),
    )
    write_off = seg(
        "1",
        "00",
        z(14),
        "0057",
        "00",
        "12345",
        "7",
        sp(4),
        "0000",
        sp(25),
        "00000077",
        z(13),
        "109",
        sp(21),
        "I",
        "02",
        sp(10),
        z(6),
        n(50000, 13),
        "341",
        "00000",
        sp(2),
        " ",
        z(6),
        sp(2),
        sp(2),
        z(13),
        z(6),
        z(13),
        z(13),
        z(13),
        "00",
        z(14),
        sp(40),
        sp(40),
        sp(12),
        z(8),
        sp(15),
        sp(2),
        sp(30),
        sp(4),
        z(6),
        "00",
        " ",
        n(5, 6),
    )
    due_change = seg(
        "1",
        "00",
        z(14),
        "0057",
        "00",
        "12345",
        "7",
        sp(4),
        "0000",
        sp(25),
        "00000078",
        z(13),
        "109",
        sp(21),
        "I",
        "06",
        sp(10),
        "151226",
        n(7000, 13),
        "341",
        "00000",
        sp(2),
        " ",
        z(6),
        sp(2),
        sp(2),
        z(13),
        z(6),
        z(13),
        z(13),
        z(13),
        "00",
        z(14),
        sp(40),
        sp(40),
        sp(12),
        z(8),
        sp(15),
        sp(2),
        sp(30),
        sp(4),
        z(6),
        "00",
        " ",
        n(6, 6),
    )
    trailer = seg("9", sp(393), n(7, 6))
    lines = [header, register, fine, type5, write_off, due_change, trailer]
    return "".join(line + "\r\n" for line in lines).encode("ascii")
