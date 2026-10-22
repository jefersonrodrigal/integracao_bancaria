"""Registros do leiaute Itaú CNAB 400 de cobrança.

Fonte: "Cobrança Bancária — Intercâmbio Eletrônico de Arquivos — Layout de Arquivos —
CNAB 400", Itaú Unibanco, versão JANEIRO 2017. ``reference`` indica a página do manual.
A cobertura contígua 1-400 de cada registro é verificada em ``RecordLayout``.
"""

from __future__ import annotations

from app.cnab.fields import Field, RecordLayout
from app.cnab.fields import FieldType as T

N, X, D6, D8 = T.NUMERIC, T.ALPHA, T.DATE_DDMMYY, T.DATE_DDMMYYYY


def _blank(name: str, start: int, end: int, ref: str) -> Field:
    return Field(name, start, end, X, constant=" " * (end - start + 1), reference=ref)


def _zeros(name: str, start: int, end: int, ref: str) -> Field:
    return Field(name, start, end, N, constant="0" * (end - start + 1), reference=ref)


# --------------------------------------------------------------------------- remessa
P7, P8, P9, P12 = "p.7", "p.8", "p.9", "p.12"

REMITTANCE_HEADER = RecordLayout(
    "remessa_header",
    (
        Field("tipo_registro", 1, 1, N, constant="0", reference=P7),
        Field("operacao", 2, 2, N, constant="1", reference=P7),
        Field("literal_remessa", 3, 9, X, constant="REMESSA", reference=P7),
        Field("codigo_servico", 10, 11, N, constant="01", reference=P7),
        Field("literal_servico", 12, 26, X, constant="COBRANCA".ljust(15), reference=P7),
        Field("agencia", 27, 30, N, reference=P7),
        _zeros("zeros", 31, 32, P7),
        Field("conta", 33, 37, N, reference=P7),
        Field("dac", 38, 38, N, reference=P7),
        _blank("brancos_1", 39, 46, P7),
        Field("nome_empresa", 47, 76, X, reference=P7),
        Field("codigo_banco", 77, 79, N, constant="341", reference=P7),
        Field("nome_banco", 80, 94, X, constant="BANCO ITAU SA".ljust(15), reference=P7),
        Field("data_geracao", 95, 100, D6, reference=P7),
        _blank("brancos_2", 101, 394, P7),
        Field("numero_sequencial", 395, 400, N, reference=P7),
    ),
    reference=P7,
)

REMITTANCE_DETAIL = RecordLayout(
    "remessa_detalhe_1",
    (
        Field("tipo_registro", 1, 1, N, constant="1", reference=P8),
        Field("codigo_inscricao", 2, 3, N, reference="p.8, Nota 1"),
        Field("numero_inscricao", 4, 17, N, reference="p.8, Nota 1"),
        Field("agencia", 18, 21, N, reference=P8),
        _zeros("zeros", 22, 23, P8),
        Field("conta", 24, 28, N, reference=P8),
        Field("dac", 29, 29, N, reference=P8),
        _blank("brancos_1", 30, 33, P8),
        Field("instrucao_alegacao", 34, 37, N, reference="p.8, Nota 27"),
        Field("uso_empresa", 38, 62, X, uppercase=False, reference="p.8, Nota 2"),
        Field("nosso_numero", 63, 70, N, reference="p.8, Nota 3"),
        Field("qtde_moeda", 71, 83, N, decimals=5, reference="p.8, Nota 4"),
        Field("numero_carteira", 84, 86, N, reference="p.8, Nota 5"),
        Field("uso_banco", 87, 107, X, reference=P8),
        Field("codigo_carteira", 108, 108, X, reference="p.8, Nota 5"),
        Field("codigo_ocorrencia", 109, 110, N, reference="p.8, Nota 6"),
        Field("numero_documento", 111, 120, X, reference="p.8, Nota 18"),
        Field("vencimento", 121, 126, D6, reference="p.8, Nota 7"),
        Field("valor_titulo", 127, 139, N, decimals=2, reference="p.8, Nota 8"),
        Field("codigo_banco", 140, 142, N, constant="341", reference=P8),
        Field("agencia_cobradora", 143, 147, N, reference="p.8, Nota 9"),
        Field("especie", 148, 149, X, reference="p.8, Nota 10"),
        Field("aceite", 150, 150, X, reference=P8),
        Field("data_emissao", 151, 156, D6, reference="p.8, Nota 31"),
        Field("instrucao_1", 157, 158, X, reference="p.8, Nota 11"),
        Field("instrucao_2", 159, 160, X, reference="p.8, Nota 11"),
        Field("juros_1_dia", 161, 173, N, decimals=2, reference="p.8, Nota 12"),
        Field("desconto_ate", 174, 179, D6, reference=P8),
        Field("valor_desconto", 180, 192, N, decimals=2, reference="p.8, Nota 13"),
        Field("valor_iof", 193, 205, N, decimals=2, reference="p.8, Nota 14"),
        Field("abatimento", 206, 218, N, decimals=2, reference="p.8, Nota 13"),
        Field("codigo_inscricao_pagador", 219, 220, N, reference=P8),
        Field("numero_inscricao_pagador", 221, 234, N, reference=P8),
        # Nome (235-264) + brancos (265-274) agrupados conforme Nota 15 (p.23).
        Field("nome_pagador", 235, 274, X, reference="p.8, Nota 15"),
        Field("logradouro", 275, 314, X, truncate=True, reference=P8),
        Field("bairro", 315, 326, X, truncate=True, reference=P8),
        Field("cep", 327, 334, N, reference=P8),
        Field("cidade", 335, 349, X, truncate=True, reference=P8),
        Field("estado", 350, 351, X, reference=P8),
        Field("sacador_avalista", 352, 381, X, reference="p.8, Nota 16"),
        _blank("brancos_3", 382, 385, P8),
        Field("data_mora", 386, 391, D6, reference=P8),
        Field("prazo", 392, 393, N, reference="p.8, Nota 11 (A)"),
        _blank("brancos_4", 394, 394, P8),
        Field("numero_sequencial", 395, 400, N, reference=P8),
    ),
    reference=P8,
)

REMITTANCE_FINE = RecordLayout(
    "remessa_detalhe_2_multa",
    (
        Field("tipo_registro", 1, 1, N, constant="2", reference=P9),
        Field("codigo_multa", 2, 2, X, reference="p.9, Nota 35"),
        Field("data_multa", 3, 10, D8, reference="p.9, Nota 35"),
        Field("multa", 11, 23, N, decimals=2, reference="p.9, Nota 35"),
        _blank("brancos", 24, 394, P9),
        Field("numero_sequencial", 395, 400, N, reference=P9),
    ),
    reference=P9,
)

REMITTANCE_EMAIL_GUARANTOR = RecordLayout(
    "remessa_detalhe_5",
    (
        Field("tipo_registro", 1, 1, N, constant="5", reference=P12),
        Field("email", 2, 121, X, uppercase=False, reference="p.12, Nota 29"),
        Field("codigo_inscricao_sacador", 122, 123, N, reference="p.12, Nota 30"),
        Field("numero_inscricao_sacador", 124, 137, N, reference="p.12, Nota 30"),
        Field("logradouro_sacador", 138, 177, X, truncate=True, reference="p.12, Nota 30"),
        Field("bairro_sacador", 178, 189, X, truncate=True, reference="p.12, Nota 30"),
        Field("cep_sacador", 190, 197, N, reference="p.12, Nota 30"),
        Field("cidade_sacador", 198, 212, X, truncate=True, reference="p.12, Nota 30"),
        Field("estado_sacador", 213, 214, X, reference="p.12, Nota 30"),
        _blank("brancos", 215, 394, P12),
        Field("numero_sequencial", 395, 400, N, reference=P12),
    ),
    reference=P12,
)

REMITTANCE_TRAILER = RecordLayout(
    "remessa_trailer",
    (
        Field("tipo_registro", 1, 1, N, constant="9", reference=P12),
        _blank("brancos", 2, 394, P12),
        Field("numero_sequencial", 395, 400, N, reference=P12),
    ),
    reference=P12,
)

# --------------------------------------------------------------------------- retorno
P13, P14, P15, P16, P17 = "p.13", "p.14", "p.15", "p.16", "p.17"

RETURN_HEADER = RecordLayout(
    "retorno_header",
    (
        Field("tipo_registro", 1, 1, N, constant="0", reference=P13),
        Field("codigo_retorno", 2, 2, N, constant="2", reference=P13),
        Field("literal_retorno", 3, 9, X, constant="RETORNO", reference=P13),
        Field("codigo_servico", 10, 11, N, constant="01", reference=P13),
        Field("literal_servico", 12, 26, X, reference=P13),
        Field("agencia", 27, 30, N, reference=P13),
        Field("zeros", 31, 32, N, reference=P13),
        Field("conta", 33, 37, N, reference=P13),
        Field("dac", 38, 38, N, reference=P13),
        Field("brancos_1", 39, 46, X, reference=P13),
        Field("nome_empresa", 47, 76, X, reference=P13),
        Field("codigo_banco", 77, 79, N, constant="341", reference=P13),
        Field("nome_banco", 80, 94, X, reference=P13),
        Field("data_geracao", 95, 100, D6, reference=P13),
        Field("densidade", 101, 105, N, reference=P13),
        Field("unidade_densidade", 106, 108, X, reference=P13),
        Field("sequencial_arquivo", 109, 113, N, reference=P13),
        Field("data_credito", 114, 119, D6, reference="p.13, indicador 40.6"),
        Field("brancos_2", 120, 394, X, reference=P13),
        Field("numero_sequencial", 395, 400, N, reference=P13),
    ),
    reference=P13,
)

RETURN_DETAIL = RecordLayout(
    "retorno_detalhe_1",
    (
        Field("tipo_registro", 1, 1, N, constant="1", reference=P14),
        Field("codigo_inscricao", 2, 3, N, reference=P14),
        Field("numero_inscricao", 4, 17, N, reference=P14),
        Field("agencia", 18, 21, N, reference=P14),
        Field("zeros_1", 22, 23, N, reference=P14),
        Field("conta", 24, 28, N, reference=P14),
        Field("dac", 29, 29, N, reference=P14),
        Field("brancos_1", 30, 37, X, reference=P14),
        Field("uso_empresa", 38, 62, X, reference="p.14, Nota 2"),
        Field("nosso_numero_1", 63, 70, N, reference=P14),
        Field("brancos_2", 71, 82, X, reference=P14),
        Field("numero_carteira", 83, 85, N, reference="p.14, Nota 5"),
        Field("nosso_numero", 86, 93, N, reference="p.14, Nota 3"),
        Field("dac_nosso_numero", 94, 94, N, reference="p.14, Nota 3"),
        Field("brancos_3", 95, 106, X, reference=P14),
        # Posição 107: I (informativo) / C (contábil) quando indicador 23.2 = 2 (p.41).
        Field("indicador_lancamento", 107, 107, X, reference="p.41, indicador 23.2"),
        Field("codigo_carteira", 108, 108, X, reference="p.14, Nota 5"),
        Field("codigo_ocorrencia", 109, 110, N, reference="p.14, Nota 17"),
        Field("data_ocorrencia", 111, 116, D6, reference=P14),
        Field("numero_documento", 117, 126, X, reference="p.14, Nota 18"),
        Field("nosso_numero_confirmacao", 127, 134, N, reference=P14),
        Field("brancos_4", 135, 146, X, reference=P14),
        Field("vencimento", 147, 152, D6, reference=P14),
        Field("valor_titulo", 153, 165, N, decimals=2, reference=P14),
        Field("codigo_banco", 166, 168, N, reference=P14),
        Field("agencia_cobradora", 169, 172, N, reference="p.14, Nota 9"),
        Field("dac_agencia_cobradora", 173, 173, N, reference=P14),
        Field("especie", 174, 175, N, reference="p.14, Nota 10"),
        Field("tarifa_cobranca", 176, 188, N, decimals=2, reference=P14),
        Field("brancos_5", 189, 214, X, reference=P14),
        Field("valor_iof", 215, 227, N, decimals=2, reference=P14),
        Field("valor_abatimento", 228, 240, N, decimals=2, reference="p.14, Nota 19"),
        Field("valor_desconto", 241, 253, N, decimals=2, reference="p.14, Nota 19"),
        Field("valor_principal", 254, 266, N, decimals=2, reference=P14),
        Field("juros_mora_multa", 267, 279, N, decimals=2, reference=P14),
        Field("outros_creditos", 280, 292, N, decimals=2, reference=P14),
        Field("boleto_dda", 293, 293, X, reference="p.14, Nota 34"),
        Field("brancos_6", 294, 295, X, reference=P14),
        Field("data_credito", 296, 301, X, reference=P14),
        # 302-311 e 312-324 carregam complementos nas ocorrências 24, 25 e 57 (Nota 20, p.26).
        Field("instrucao_cancelada", 302, 305, X, reference="p.14, Nota 20"),
        Field("complemento_data", 306, 311, X, reference="p.26, Nota 20"),
        Field("complemento_valor", 312, 324, X, reference="p.26, Nota 20"),
        Field("nome_pagador", 325, 354, X, reference=P14),
        Field("brancos_7", 355, 377, X, reference=P14),
        Field("erros_mensagem", 378, 385, X, reference="p.14, Nota 20"),
        Field("brancos_8", 386, 392, X, reference=P14),
        Field("codigo_liquidacao", 393, 394, X, reference="p.14, Nota 28"),
        Field("numero_sequencial", 395, 400, N, reference=P14),
    ),
    reference=P14,
)

# Registro de transação opcional — cheque devolvido (69) / compensado (76), p.15.
RETURN_CHEQUE = RecordLayout(
    "retorno_detalhe_1_cheque",
    (
        Field("tipo_registro", 1, 1, N, constant="1", reference=P15),
        Field("codigo_inscricao", 2, 3, N, reference=P15),
        Field("numero_inscricao", 4, 17, N, reference=P15),
        Field("agencia", 18, 21, N, reference=P15),
        Field("zeros_1", 22, 23, N, reference=P15),
        Field("conta", 24, 28, N, reference=P15),
        Field("dac", 29, 29, N, reference=P15),
        Field("brancos_1", 30, 37, X, reference=P15),
        Field("uso_empresa", 38, 62, X, reference=P15),
        Field("nosso_numero_1", 63, 70, N, reference=P15),
        Field("agencia_conta_cheque", 71, 82, X, reference="p.15, Nota 33"),
        Field("numero_carteira", 83, 85, N, reference=P15),
        Field("nosso_numero", 86, 93, N, reference=P15),
        Field("dac_nosso_numero", 94, 94, N, reference=P15),
        Field("brancos_3", 95, 107, X, reference=P15),
        Field("codigo_carteira", 108, 108, X, reference=P15),
        Field("codigo_ocorrencia", 109, 110, N, reference=P15),
        Field("data_ocorrencia", 111, 116, D6, reference=P15),
        Field("numero_documento", 117, 126, X, reference=P15),
        Field("nosso_numero_confirmacao", 127, 134, N, reference=P15),
        Field("brancos_4", 135, 146, X, reference=P15),
        Field("zeros_2", 147, 152, N, reference=P15),
        Field("valor_titulo", 153, 165, N, decimals=2, reference=P15),
        Field("codigo_banco", 166, 168, N, reference=P15),
        Field("agencia_cobradora", 169, 172, N, reference=P15),
        Field("dac_agencia_cobradora", 173, 173, N, reference=P15),
        Field("brancos_5", 174, 175, X, reference=P15),
        Field("zeros_3", 176, 253, N, reference=P15),
        Field("valor_cheque", 254, 266, N, decimals=2, reference=P15),
        Field("zeros_4", 267, 292, N, reference=P15),
        Field("brancos_6", 293, 301, X, reference=P15),
        Field("zeros_5", 302, 324, N, reference=P15),
        Field("cmc7", 325, 354, X, reference=P15),
        Field("brancos_7", 355, 377, X, reference=P15),
        Field("motivo_devolucao", 378, 379, X, reference="p.15, Nota 20 Tabela 9"),
        Field("brancos_8", 380, 394, X, reference=P15),
        Field("numero_sequencial", 395, 400, N, reference=P15),
    ),
    reference=P15,
)

# Registro 4 (rateio de crédito) do retorno: lido apenas até a ocorrência; rateio não é
# suportado nesta versão e o restante é preservado na linha original.
RETURN_SPLIT = RecordLayout(
    "retorno_detalhe_4_rateio",
    (
        Field("tipo_registro", 1, 1, N, constant="4", reference=P16),
        Field("codigo_inscricao", 2, 3, N, reference=P16),
        Field("numero_inscricao", 4, 17, N, reference=P16),
        Field("agencia", 18, 21, N, reference=P16),
        Field("zeros_1", 22, 23, N, reference=P16),
        Field("conta", 24, 28, N, reference=P16),
        Field("dac", 29, 29, N, reference=P16),
        Field("brancos_1", 30, 37, X, reference=P16),
        Field("uso_empresa", 38, 62, X, reference=P16),
        Field("nosso_numero_1", 63, 70, N, reference=P16),
        Field("brancos_2", 71, 82, X, reference=P16),
        Field("numero_carteira", 83, 85, N, reference=P16),
        Field("nosso_numero", 86, 93, N, reference=P16),
        Field("dac_nosso_numero", 94, 94, N, reference=P16),
        Field("brancos_3", 95, 107, X, reference=P16),
        Field("codigo_carteira", 108, 108, X, reference=P16),
        Field("codigo_ocorrencia", 109, 110, N, reference=P16),
        Field("dados_rateio", 111, 394, X, reference="p.16-17"),
        Field("numero_sequencial", 395, 400, N, reference=P16),
    ),
    reference="p.16-17",
)

RETURN_TRAILER = RecordLayout(
    "retorno_trailer",
    (
        Field("tipo_registro", 1, 1, N, constant="9", reference=P17),
        Field("codigo_retorno", 2, 2, N, constant="2", reference=P17),
        Field("codigo_servico", 3, 4, N, constant="01", reference=P17),
        Field("codigo_banco", 5, 7, N, constant="341", reference=P17),
        Field("brancos_1", 8, 17, X, reference=P17),
        Field("qtde_simples", 18, 25, N, reference="p.17, Nota 21"),
        Field("valor_simples", 26, 39, N, decimals=2, reference="p.17, Nota 21"),
        Field("aviso_simples", 40, 47, X, reference="p.17, Nota 22"),
        Field("brancos_2", 48, 57, X, reference=P17),
        Field("qtde_vinculada", 58, 65, N, reference="p.17, Nota 21"),
        Field("valor_vinculada", 66, 79, N, decimals=2, reference="p.17, Nota 21"),
        Field("aviso_vinculada", 80, 87, X, reference="p.17, Nota 22"),
        Field("brancos_3", 88, 177, X, reference=P17),
        Field("qtde_direta", 178, 185, N, reference="p.17, Nota 21"),
        Field("valor_direta", 186, 199, N, decimals=2, reference="p.17, Nota 21"),
        Field("aviso_direta", 200, 207, X, reference="p.17, Nota 22"),
        Field("controle_arquivo", 208, 212, N, reference=P17),
        Field("qtde_detalhes", 213, 220, N, reference=P17),
        Field("valor_total_informado", 221, 234, N, decimals=2, reference=P17),
        Field("brancos_4", 235, 394, X, reference=P17),
        Field("numero_sequencial", 395, 400, N, reference=P17),
    ),
    reference=P17,
)

ALL_LAYOUTS = (
    REMITTANCE_HEADER,
    REMITTANCE_DETAIL,
    REMITTANCE_FINE,
    REMITTANCE_EMAIL_GUARANTOR,
    REMITTANCE_TRAILER,
    RETURN_HEADER,
    RETURN_DETAIL,
    RETURN_CHEQUE,
    RETURN_SPLIT,
    RETURN_TRAILER,
)
