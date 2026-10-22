"""Verifica os leiautes declarados contra posições conferidas manualmente no manual."""

import pytest

from app.cnab.layouts.itau.cnab400 import records as r

EXPECTED = [
    # (leiaute, campo, início, fim) — conferidos nas páginas indicadas do manual.
    (r.REMITTANCE_HEADER, "data_geracao", 95, 100),  # p.7
    (r.REMITTANCE_DETAIL, "uso_empresa", 38, 62),  # p.8
    (r.REMITTANCE_DETAIL, "nosso_numero", 63, 70),
    (r.REMITTANCE_DETAIL, "codigo_carteira", 108, 108),
    (r.REMITTANCE_DETAIL, "codigo_ocorrencia", 109, 110),
    (r.REMITTANCE_DETAIL, "valor_titulo", 127, 139),
    (r.REMITTANCE_DETAIL, "codigo_inscricao_pagador", 219, 220),
    (r.REMITTANCE_DETAIL, "cep", 327, 334),
    (r.REMITTANCE_DETAIL, "prazo", 392, 393),
    (r.REMITTANCE_FINE, "data_multa", 3, 10),  # p.9
    (r.REMITTANCE_FINE, "multa", 11, 23),
    (r.REMITTANCE_EMAIL_GUARANTOR, "email", 2, 121),  # p.12
    (r.REMITTANCE_EMAIL_GUARANTOR, "estado_sacador", 213, 214),
    (r.RETURN_HEADER, "data_credito", 114, 119),  # p.13
    (r.RETURN_DETAIL, "nosso_numero", 86, 93),  # p.14
    (r.RETURN_DETAIL, "codigo_ocorrencia", 109, 110),
    (r.RETURN_DETAIL, "tarifa_cobranca", 176, 188),
    (r.RETURN_DETAIL, "valor_principal", 254, 266),
    (r.RETURN_DETAIL, "data_credito", 296, 301),
    (r.RETURN_DETAIL, "erros_mensagem", 378, 385),
    (r.RETURN_DETAIL, "codigo_liquidacao", 393, 394),
    (r.RETURN_CHEQUE, "motivo_devolucao", 378, 379),  # p.15
    (r.RETURN_TRAILER, "qtde_detalhes", 213, 220),  # p.17
    (r.RETURN_TRAILER, "valor_total_informado", 221, 234),
]


@pytest.mark.parametrize(("layout", "name", "start", "end"), EXPECTED)
def test_positions(layout: r.RecordLayout, name: str, start: int, end: int) -> None:
    field = layout.field(name)
    assert (field.start, field.end) == (start, end)


@pytest.mark.parametrize("layout", r.ALL_LAYOUTS, ids=lambda x: x.name)
def test_every_field_is_traceable_to_the_manual(layout: r.RecordLayout) -> None:
    assert layout.length == 400
    assert all(f.reference.startswith("p.") for f in layout.fields)
    assert layout.fields[-1].name == "numero_sequencial"
