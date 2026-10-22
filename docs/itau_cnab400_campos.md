# Itaú CNAB 400 — campos e posições

Gerado por `scripts/export_layout_doc.py` a partir de `app/cnab/layouts/itau/cnab400/records.py`. Manual: *Cobrança Bancária — Intercâmbio Eletrônico de Arquivos — Layout CNAB 400*, versão 2017-01. A coluna Referência indica página/nota do manual. Não edite à mão.

## `remessa_header` (p.7)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `0` | p.7 |
| operacao | 002-002 | 9(01) | `1` | p.7 |
| literal_remessa | 003-009 | X(07) | `REMESSA` | p.7 |
| codigo_servico | 010-011 | 9(02) | `01` | p.7 |
| literal_servico | 012-026 | X(15) | `COBRANCA` | p.7 |
| agencia | 027-030 | 9(04) |  | p.7 |
| zeros | 031-032 | 9(02) | `00` | p.7 |
| conta | 033-037 | 9(05) |  | p.7 |
| dac | 038-038 | 9(01) |  | p.7 |
| brancos_1 | 039-046 | X(08) | `(brancos)` | p.7 |
| nome_empresa | 047-076 | X(30) |  | p.7 |
| codigo_banco | 077-079 | 9(03) | `341` | p.7 |
| nome_banco | 080-094 | X(15) | `BANCO ITAU SA` | p.7 |
| data_geracao | 095-100 | DDMMAA |  | p.7 |
| brancos_2 | 101-394 | X(294) | `(brancos)` | p.7 |
| numero_sequencial | 395-400 | 9(06) |  | p.7 |

## `remessa_detalhe_1` (p.8)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `1` | p.8 |
| codigo_inscricao | 002-003 | 9(02) |  | p.8, Nota 1 |
| numero_inscricao | 004-017 | 9(14) |  | p.8, Nota 1 |
| agencia | 018-021 | 9(04) |  | p.8 |
| zeros | 022-023 | 9(02) | `00` | p.8 |
| conta | 024-028 | 9(05) |  | p.8 |
| dac | 029-029 | 9(01) |  | p.8 |
| brancos_1 | 030-033 | X(04) | `(brancos)` | p.8 |
| instrucao_alegacao | 034-037 | 9(04) |  | p.8, Nota 27 |
| uso_empresa | 038-062 | X(25) |  | p.8, Nota 2 |
| nosso_numero | 063-070 | 9(08) |  | p.8, Nota 3 |
| qtde_moeda | 071-083 | 9(08)V9(5) |  | p.8, Nota 4 |
| numero_carteira | 084-086 | 9(03) |  | p.8, Nota 5 |
| uso_banco | 087-107 | X(21) |  | p.8 |
| codigo_carteira | 108-108 | X(01) |  | p.8, Nota 5 |
| codigo_ocorrencia | 109-110 | 9(02) |  | p.8, Nota 6 |
| numero_documento | 111-120 | X(10) |  | p.8, Nota 18 |
| vencimento | 121-126 | DDMMAA |  | p.8, Nota 7 |
| valor_titulo | 127-139 | 9(11)V9(2) |  | p.8, Nota 8 |
| codigo_banco | 140-142 | 9(03) | `341` | p.8 |
| agencia_cobradora | 143-147 | 9(05) |  | p.8, Nota 9 |
| especie | 148-149 | X(02) |  | p.8, Nota 10 |
| aceite | 150-150 | X(01) |  | p.8 |
| data_emissao | 151-156 | DDMMAA |  | p.8, Nota 31 |
| instrucao_1 | 157-158 | X(02) |  | p.8, Nota 11 |
| instrucao_2 | 159-160 | X(02) |  | p.8, Nota 11 |
| juros_1_dia | 161-173 | 9(11)V9(2) |  | p.8, Nota 12 |
| desconto_ate | 174-179 | DDMMAA |  | p.8 |
| valor_desconto | 180-192 | 9(11)V9(2) |  | p.8, Nota 13 |
| valor_iof | 193-205 | 9(11)V9(2) |  | p.8, Nota 14 |
| abatimento | 206-218 | 9(11)V9(2) |  | p.8, Nota 13 |
| codigo_inscricao_pagador | 219-220 | 9(02) |  | p.8 |
| numero_inscricao_pagador | 221-234 | 9(14) |  | p.8 |
| nome_pagador | 235-274 | X(40) |  | p.8, Nota 15 |
| logradouro | 275-314 | X(40) |  | p.8 |
| bairro | 315-326 | X(12) |  | p.8 |
| cep | 327-334 | 9(08) |  | p.8 |
| cidade | 335-349 | X(15) |  | p.8 |
| estado | 350-351 | X(02) |  | p.8 |
| sacador_avalista | 352-381 | X(30) |  | p.8, Nota 16 |
| brancos_3 | 382-385 | X(04) | `(brancos)` | p.8 |
| data_mora | 386-391 | DDMMAA |  | p.8 |
| prazo | 392-393 | 9(02) |  | p.8, Nota 11 (A) |
| brancos_4 | 394-394 | X(01) | `(brancos)` | p.8 |
| numero_sequencial | 395-400 | 9(06) |  | p.8 |

## `remessa_detalhe_2_multa` (p.9)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `2` | p.9 |
| codigo_multa | 002-002 | X(01) |  | p.9, Nota 35 |
| data_multa | 003-010 | DDMMAAAA |  | p.9, Nota 35 |
| multa | 011-023 | 9(11)V9(2) |  | p.9, Nota 35 |
| brancos | 024-394 | X(371) | `(brancos)` | p.9 |
| numero_sequencial | 395-400 | 9(06) |  | p.9 |

## `remessa_detalhe_5` (p.12)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `5` | p.12 |
| email | 002-121 | X(120) |  | p.12, Nota 29 |
| codigo_inscricao_sacador | 122-123 | 9(02) |  | p.12, Nota 30 |
| numero_inscricao_sacador | 124-137 | 9(14) |  | p.12, Nota 30 |
| logradouro_sacador | 138-177 | X(40) |  | p.12, Nota 30 |
| bairro_sacador | 178-189 | X(12) |  | p.12, Nota 30 |
| cep_sacador | 190-197 | 9(08) |  | p.12, Nota 30 |
| cidade_sacador | 198-212 | X(15) |  | p.12, Nota 30 |
| estado_sacador | 213-214 | X(02) |  | p.12, Nota 30 |
| brancos | 215-394 | X(180) | `(brancos)` | p.12 |
| numero_sequencial | 395-400 | 9(06) |  | p.12 |

## `remessa_trailer` (p.12)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `9` | p.12 |
| brancos | 002-394 | X(393) | `(brancos)` | p.12 |
| numero_sequencial | 395-400 | 9(06) |  | p.12 |

## `retorno_header` (p.13)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `0` | p.13 |
| codigo_retorno | 002-002 | 9(01) | `2` | p.13 |
| literal_retorno | 003-009 | X(07) | `RETORNO` | p.13 |
| codigo_servico | 010-011 | 9(02) | `01` | p.13 |
| literal_servico | 012-026 | X(15) |  | p.13 |
| agencia | 027-030 | 9(04) |  | p.13 |
| zeros | 031-032 | 9(02) |  | p.13 |
| conta | 033-037 | 9(05) |  | p.13 |
| dac | 038-038 | 9(01) |  | p.13 |
| brancos_1 | 039-046 | X(08) |  | p.13 |
| nome_empresa | 047-076 | X(30) |  | p.13 |
| codigo_banco | 077-079 | 9(03) | `341` | p.13 |
| nome_banco | 080-094 | X(15) |  | p.13 |
| data_geracao | 095-100 | DDMMAA |  | p.13 |
| densidade | 101-105 | 9(05) |  | p.13 |
| unidade_densidade | 106-108 | X(03) |  | p.13 |
| sequencial_arquivo | 109-113 | 9(05) |  | p.13 |
| data_credito | 114-119 | DDMMAA |  | p.13, indicador 40.6 |
| brancos_2 | 120-394 | X(275) |  | p.13 |
| numero_sequencial | 395-400 | 9(06) |  | p.13 |

## `retorno_detalhe_1` (p.14)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `1` | p.14 |
| codigo_inscricao | 002-003 | 9(02) |  | p.14 |
| numero_inscricao | 004-017 | 9(14) |  | p.14 |
| agencia | 018-021 | 9(04) |  | p.14 |
| zeros_1 | 022-023 | 9(02) |  | p.14 |
| conta | 024-028 | 9(05) |  | p.14 |
| dac | 029-029 | 9(01) |  | p.14 |
| brancos_1 | 030-037 | X(08) |  | p.14 |
| uso_empresa | 038-062 | X(25) |  | p.14, Nota 2 |
| nosso_numero_1 | 063-070 | 9(08) |  | p.14 |
| brancos_2 | 071-082 | X(12) |  | p.14 |
| numero_carteira | 083-085 | 9(03) |  | p.14, Nota 5 |
| nosso_numero | 086-093 | 9(08) |  | p.14, Nota 3 |
| dac_nosso_numero | 094-094 | 9(01) |  | p.14, Nota 3 |
| brancos_3 | 095-106 | X(12) |  | p.14 |
| indicador_lancamento | 107-107 | X(01) |  | p.41, indicador 23.2 |
| codigo_carteira | 108-108 | X(01) |  | p.14, Nota 5 |
| codigo_ocorrencia | 109-110 | 9(02) |  | p.14, Nota 17 |
| data_ocorrencia | 111-116 | DDMMAA |  | p.14 |
| numero_documento | 117-126 | X(10) |  | p.14, Nota 18 |
| nosso_numero_confirmacao | 127-134 | 9(08) |  | p.14 |
| brancos_4 | 135-146 | X(12) |  | p.14 |
| vencimento | 147-152 | DDMMAA |  | p.14 |
| valor_titulo | 153-165 | 9(11)V9(2) |  | p.14 |
| codigo_banco | 166-168 | 9(03) |  | p.14 |
| agencia_cobradora | 169-172 | 9(04) |  | p.14, Nota 9 |
| dac_agencia_cobradora | 173-173 | 9(01) |  | p.14 |
| especie | 174-175 | 9(02) |  | p.14, Nota 10 |
| tarifa_cobranca | 176-188 | 9(11)V9(2) |  | p.14 |
| brancos_5 | 189-214 | X(26) |  | p.14 |
| valor_iof | 215-227 | 9(11)V9(2) |  | p.14 |
| valor_abatimento | 228-240 | 9(11)V9(2) |  | p.14, Nota 19 |
| valor_desconto | 241-253 | 9(11)V9(2) |  | p.14, Nota 19 |
| valor_principal | 254-266 | 9(11)V9(2) |  | p.14 |
| juros_mora_multa | 267-279 | 9(11)V9(2) |  | p.14 |
| outros_creditos | 280-292 | 9(11)V9(2) |  | p.14 |
| boleto_dda | 293-293 | X(01) |  | p.14, Nota 34 |
| brancos_6 | 294-295 | X(02) |  | p.14 |
| data_credito | 296-301 | X(06) |  | p.14 |
| instrucao_cancelada | 302-305 | X(04) |  | p.14, Nota 20 |
| complemento_data | 306-311 | X(06) |  | p.26, Nota 20 |
| complemento_valor | 312-324 | X(13) |  | p.26, Nota 20 |
| nome_pagador | 325-354 | X(30) |  | p.14 |
| brancos_7 | 355-377 | X(23) |  | p.14 |
| erros_mensagem | 378-385 | X(08) |  | p.14, Nota 20 |
| brancos_8 | 386-392 | X(07) |  | p.14 |
| codigo_liquidacao | 393-394 | X(02) |  | p.14, Nota 28 |
| numero_sequencial | 395-400 | 9(06) |  | p.14 |

## `retorno_detalhe_1_cheque` (p.15)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `1` | p.15 |
| codigo_inscricao | 002-003 | 9(02) |  | p.15 |
| numero_inscricao | 004-017 | 9(14) |  | p.15 |
| agencia | 018-021 | 9(04) |  | p.15 |
| zeros_1 | 022-023 | 9(02) |  | p.15 |
| conta | 024-028 | 9(05) |  | p.15 |
| dac | 029-029 | 9(01) |  | p.15 |
| brancos_1 | 030-037 | X(08) |  | p.15 |
| uso_empresa | 038-062 | X(25) |  | p.15 |
| nosso_numero_1 | 063-070 | 9(08) |  | p.15 |
| agencia_conta_cheque | 071-082 | X(12) |  | p.15, Nota 33 |
| numero_carteira | 083-085 | 9(03) |  | p.15 |
| nosso_numero | 086-093 | 9(08) |  | p.15 |
| dac_nosso_numero | 094-094 | 9(01) |  | p.15 |
| brancos_3 | 095-107 | X(13) |  | p.15 |
| codigo_carteira | 108-108 | X(01) |  | p.15 |
| codigo_ocorrencia | 109-110 | 9(02) |  | p.15 |
| data_ocorrencia | 111-116 | DDMMAA |  | p.15 |
| numero_documento | 117-126 | X(10) |  | p.15 |
| nosso_numero_confirmacao | 127-134 | 9(08) |  | p.15 |
| brancos_4 | 135-146 | X(12) |  | p.15 |
| zeros_2 | 147-152 | 9(06) |  | p.15 |
| valor_titulo | 153-165 | 9(11)V9(2) |  | p.15 |
| codigo_banco | 166-168 | 9(03) |  | p.15 |
| agencia_cobradora | 169-172 | 9(04) |  | p.15 |
| dac_agencia_cobradora | 173-173 | 9(01) |  | p.15 |
| brancos_5 | 174-175 | X(02) |  | p.15 |
| zeros_3 | 176-253 | 9(78) |  | p.15 |
| valor_cheque | 254-266 | 9(11)V9(2) |  | p.15 |
| zeros_4 | 267-292 | 9(26) |  | p.15 |
| brancos_6 | 293-301 | X(09) |  | p.15 |
| zeros_5 | 302-324 | 9(23) |  | p.15 |
| cmc7 | 325-354 | X(30) |  | p.15 |
| brancos_7 | 355-377 | X(23) |  | p.15 |
| motivo_devolucao | 378-379 | X(02) |  | p.15, Nota 20 Tabela 9 |
| brancos_8 | 380-394 | X(15) |  | p.15 |
| numero_sequencial | 395-400 | 9(06) |  | p.15 |

## `retorno_detalhe_4_rateio` (p.16-17)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `4` | p.16 |
| codigo_inscricao | 002-003 | 9(02) |  | p.16 |
| numero_inscricao | 004-017 | 9(14) |  | p.16 |
| agencia | 018-021 | 9(04) |  | p.16 |
| zeros_1 | 022-023 | 9(02) |  | p.16 |
| conta | 024-028 | 9(05) |  | p.16 |
| dac | 029-029 | 9(01) |  | p.16 |
| brancos_1 | 030-037 | X(08) |  | p.16 |
| uso_empresa | 038-062 | X(25) |  | p.16 |
| nosso_numero_1 | 063-070 | 9(08) |  | p.16 |
| brancos_2 | 071-082 | X(12) |  | p.16 |
| numero_carteira | 083-085 | 9(03) |  | p.16 |
| nosso_numero | 086-093 | 9(08) |  | p.16 |
| dac_nosso_numero | 094-094 | 9(01) |  | p.16 |
| brancos_3 | 095-107 | X(13) |  | p.16 |
| codigo_carteira | 108-108 | X(01) |  | p.16 |
| codigo_ocorrencia | 109-110 | 9(02) |  | p.16 |
| dados_rateio | 111-394 | X(284) |  | p.16-17 |
| numero_sequencial | 395-400 | 9(06) |  | p.16 |

## `retorno_trailer` (p.17)

| Campo | Posição | Picture | Conteúdo fixo | Referência |
|---|---|---|---|---|
| tipo_registro | 001-001 | 9(01) | `9` | p.17 |
| codigo_retorno | 002-002 | 9(01) | `2` | p.17 |
| codigo_servico | 003-004 | 9(02) | `01` | p.17 |
| codigo_banco | 005-007 | 9(03) | `341` | p.17 |
| brancos_1 | 008-017 | X(10) |  | p.17 |
| qtde_simples | 018-025 | 9(08) |  | p.17, Nota 21 |
| valor_simples | 026-039 | 9(12)V9(2) |  | p.17, Nota 21 |
| aviso_simples | 040-047 | X(08) |  | p.17, Nota 22 |
| brancos_2 | 048-057 | X(10) |  | p.17 |
| qtde_vinculada | 058-065 | 9(08) |  | p.17, Nota 21 |
| valor_vinculada | 066-079 | 9(12)V9(2) |  | p.17, Nota 21 |
| aviso_vinculada | 080-087 | X(08) |  | p.17, Nota 22 |
| brancos_3 | 088-177 | X(90) |  | p.17 |
| qtde_direta | 178-185 | 9(08) |  | p.17, Nota 21 |
| valor_direta | 186-199 | 9(12)V9(2) |  | p.17, Nota 21 |
| aviso_direta | 200-207 | X(08) |  | p.17, Nota 22 |
| controle_arquivo | 208-212 | 9(05) |  | p.17 |
| qtde_detalhes | 213-220 | 9(08) |  | p.17 |
| valor_total_informado | 221-234 | 9(12)V9(2) |  | p.17 |
| brancos_4 | 235-394 | X(160) |  | p.17 |
| numero_sequencial | 395-400 | 9(06) |  | p.17 |

## Carteiras (Nota 5, p.18)

| Carteira | Código (pos. 108) | Modalidade | Descrição | Obs | Suportada | Motivo |
|---|---|---|---|---|---|---|
| 108 | I | DIRETA | DIRETA ELETRÔNICA EMISSÃO INTEGRAL – CARNÊ | D,E | sim |  |
| 180 | I | DIRETA | DIRETA ELETRÔNICA EMISSÃO INTEGRAL – SIMPLES | E | sim |  |
| 121 | I | DIRETA | DIRETA ELETRÔNICA EMISSÃO PARCIAL – SIMPLES |  | sim |  |
| 150 | U | DIRETA | DIRETA ELETRÔNICA SEM EMISSÃO – DÓLAR | E | não | Moeda variável (dólar) não suportada nesta versão |
| 109 | I | DIRETA | DIRETA ELETRÔNICA SEM EMISSÃO – SIMPLES |  | sim |  |
| 191 | 1 | — | DUPLICATAS - TRANSFERÊNCIA DE DESCONTO |  | não | Carteira sem modalidade definida na Nota 5 |
| 104 | I | ESCRITURAL | ESCRITURAL ELETRÔNICA – CARNÊ | D | não | Conflito documental: Nota 3 (escritural envia nosso número zerado) x obs (D) |
| 188 | I | ESCRITURAL | ESCRITURAL ELETRÔNICA - COBRANÇA INTELIGENTE (B2B) | F | sim |  |
| 147 | E | ESCRITURAL | ESCRITURAL ELETRÔNICA – DÓLAR |  | não | Moeda variável (dólar) não suportada nesta versão |
| 112 | I | ESCRITURAL | ESCRITURAL ELETRÔNICA – SIMPLES |  | sim |  |
| 115 | I | ESCRITURAL | ESCRITURAL ELETRÔNICA – SIMPLES – FAIXA NOSSO NÚMERO LIVRE |  | sim |  |

## Ocorrências de retorno (Nota 17, p.23-25) e efeito aplicado

O **efeito** é regra interna da aplicação (ver `docs/itau_cnab400.md`).

| Código | Descrição (manual) | Efeito interno |
|---|---|---|
| 02 | ENTRADA CONFIRMADA COM POSSIBILIDADE DE MENSAGEM | ENTRY_CONFIRMED |
| 03 | ENTRADA REJEITADA | ENTRY_REJECTED |
| 04 | ALTERAÇÃO DE DADOS – NOVA ENTRADA OU ALTERAÇÃO/EXCLUSÃO DE DADOS ACATADA | INFORMATIONAL |
| 05 | ALTERAÇÃO DE DADOS – BAIXA | REVIEW_REQUIRED |
| 06 | LIQUIDAÇÃO NORMAL | SETTLEMENT |
| 07 | LIQUIDAÇÃO PARCIAL – COBRANÇA INTELIGENTE (B2B) | PARTIAL_SETTLEMENT |
| 08 | LIQUIDAÇÃO EM CARTÓRIO | SETTLEMENT |
| 09 | BAIXA SIMPLES | WRITE_OFF |
| 10 | BAIXA POR TER SIDO LIQUIDADO | INFORMATIONAL |
| 11 | EM SER (SÓ NO RETORNO MENSAL) | INFORMATIONAL |
| 12 | ABATIMENTO CONCEDIDO | INFORMATIONAL |
| 13 | ABATIMENTO CANCELADO | INFORMATIONAL |
| 14 | VENCIMENTO ALTERADO | DUE_DATE_CHANGED |
| 15 | BAIXAS REJEITADAS | WRITE_OFF_REJECTED |
| 16 | INSTRUÇÕES REJEITADAS | INSTRUCTION_REJECTED |
| 17 | ALTERAÇÃO/EXCLUSÃO DE DADOS REJEITADOS | INSTRUCTION_REJECTED |
| 18 | COBRANÇA CONTRATUAL – INSTRUÇÕES/ALTERAÇÕES REJEITADAS/PENDENTES | INSTRUCTION_REJECTED |
| 19 | CONFIRMA RECEBIMENTO DE INSTRUÇÃO DE PROTESTO | INFORMATIONAL |
| 20 | CONFIRMA RECEBIMENTO DE INSTRUÇÃO DE SUSTAÇÃO DE PROTESTO /TARIFA | INFORMATIONAL |
| 21 | CONFIRMA RECEBIMENTO DE INSTRUÇÃO DE NÃO PROTESTAR | INFORMATIONAL |
| 23 | TÍTULO ENVIADO A CARTÓRIO/TARIFA | INFORMATIONAL |
| 24 | INSTRUÇÃO DE PROTESTO REJEITADA / SUSTADA / PENDENTE | INFORMATIONAL |
| 25 | ALEGAÇÕES DO PAGADOR | INFORMATIONAL |
| 26 | TARIFA DE AVISO DE COBRANÇA | FEE |
| 27 | TARIFA DE EXTRATO POSIÇÃO (B40X) | FEE |
| 28 | TARIFA DE RELAÇÃO DAS LIQUIDAÇÕES | FEE |
| 29 | TARIFA DE MANUTENÇÃO DE TÍTULOS VENCIDOS | FEE |
| 30 | DÉBITO MENSAL DE TARIFAS (PARA ENTRADAS E BAIXAS) | FEE |
| 32 | BAIXA POR TER SIDO PROTESTADO | WRITE_OFF |
| 33 | CUSTAS DE PROTESTO | FEE |
| 34 | CUSTAS DE SUSTAÇÃO | FEE |
| 35 | CUSTAS DE CARTÓRIO DISTRIBUIDOR | FEE |
| 36 | CUSTAS DE EDITAL | FEE |
| 37 | TARIFA DE EMISSÃO DE BOLETO/TARIFA DE ENVIO DE DUPLICATA | FEE |
| 38 | TARIFA DE INSTRUÇÃO | FEE |
| 39 | TARIFA DE OCORRÊNCIAS | FEE |
| 40 | TARIFA MENSAL DE EMISSÃO DE BOLETO/TARIFA MENSAL DE ENVIO DE DUPLICATA | FEE |
| 41 | DÉBITO MENSAL DE TARIFAS – EXTRATO DE POSIÇÃO (B4EP/B4OX) | FEE |
| 42 | DÉBITO MENSAL DE TARIFAS – OUTRAS INSTRUÇÕES | FEE |
| 43 | DÉBITO MENSAL DE TARIFAS – MANUTENÇÃO DE TÍTULOS VENCIDOS | FEE |
| 44 | DÉBITO MENSAL DE TARIFAS – OUTRAS OCORRÊNCIAS | FEE |
| 45 | DÉBITO MENSAL DE TARIFAS – PROTESTO | FEE |
| 46 | DÉBITO MENSAL DE TARIFAS – SUSTAÇÃO DE PROTESTO | FEE |
| 47 | BAIXA COM TRANSFERÊNCIA PARA DESCONTO | WRITE_OFF |
| 48 | CUSTAS DE SUSTAÇÃO JUDICIAL | FEE |
| 51 | TARIFA MENSAL REF A ENTRADAS BANCOS CORRESPONDENTES NA CARTEIRA | FEE |
| 52 | TARIFA MENSAL BAIXAS NA CARTEIRA | FEE |
| 53 | TARIFA MENSAL BAIXAS EM BANCOS CORRESPONDENTES NA CARTEIRA | FEE |
| 54 | TARIFA MENSAL DE LIQUIDAÇÕES NA CARTEIRA | FEE |
| 55 | TARIFA MENSAL DE LIQUIDAÇÕES EM BANCOS CORRESPONDENTES NA CARTEIRA | FEE |
| 56 | CUSTAS DE IRREGULARIDADE | FEE |
| 57 | INSTRUÇÃO CANCELADA | INFORMATIONAL |
| 59 | BAIXA POR CRÉDITO EM C/C ATRAVÉS DO SISPAG | REVIEW_REQUIRED |
| 60 | ENTRADA REJEITADA CARNÊ | ENTRY_REJECTED |
| 61 | TARIFA EMISSÃO AVISO DE MOVIMENTAÇÃO DE TÍTULOS (2154) | FEE |
| 62 | DÉBITO MENSAL DE TARIFA – AVISO DE MOVIMENTAÇÃO DE TÍTULOS (2154) | FEE |
| 63 | TÍTULO SUSTADO JUDICIALMENTE | REVIEW_REQUIRED |
| 64 | ENTRADA CONFIRMADA COM RATEIO DE CRÉDITO | ENTRY_CONFIRMED |
| 65 | PAGAMENTO COM CHEQUE – AGUARDANDO COMPENSAÇÃO | INFORMATIONAL |
| 69 | CHEQUE DEVOLVIDO | REVIEW_REQUIRED |
| 71 | ENTRADA REGISTRADA, AGUARDANDO AVALIAÇÃO | INFORMATIONAL |
| 72 | BAIXA POR CRÉDITO EM C/C ATRAVÉS DO SISPAG SEM TÍTULO CORRESPONDENTE | REVIEW_REQUIRED |
| 73 | CONFIRMAÇÃO DE ENTRADA NA COBRANÇA SIMPLES – ENTRADA NÃO ACEITA NA COBRANÇA CONTRATUAL | ENTRY_CONFIRMED |
| 74 | INSTRUÇÃO DE NEGATIVAÇÃO EXPRESSA REJEITADA | INFORMATIONAL |
| 75 | CONFIRMAÇÃO DE RECEBIMENTO DE INSTRUÇÃO DE ENTRADA EM NEGATIVAÇÃO EXPRESSA | INFORMATIONAL |
| 76 | CHEQUE COMPENSADO | INFORMATIONAL |
| 77 | CONFIRMAÇÃO DE RECEBIMENTO DE INSTRUÇÃO DE EXCLUSÃO DE ENTRADA EM NEGATIVAÇÃO EXPRESSA | INFORMATIONAL |
| 78 | CONFIRMAÇÃO DE RECEBIMENTO DE INSTRUÇÃO DE CANCELAMENTO DE NEGATIVAÇÃO EXPRESSA | INFORMATIONAL |
| 79 | NEGATIVAÇÃO EXPRESSA INFORMACIONAL | INFORMATIONAL |
| 80 | CONFIRMAÇÃO DE ENTRADA EM NEGATIVAÇÃO EXPRESSA – TARIFA | FEE |
| 82 | CONFIRMAÇÃO DO CANCELAMENTO DE NEGATIVAÇÃO EXPRESSA – TARIFA | FEE |
| 83 | CONFIRMAÇÃO DE EXCLUSÃO DE ENTRADA EM NEGATIVAÇÃO EXPRESSA POR LIQUIDAÇÃO – TARIFA | FEE |
| 85 | TARIFA POR BOLETO (ATÉ 03 ENVIOS) COBRANÇA ATIVA ELETRÔNICA | FEE |
| 86 | TARIFA EMAIL COBRANÇA ATIVA ELETRÔNICA | FEE |
| 87 | TARIFA SMS COBRANÇA ATIVA ELETRÔNICA | FEE |
| 88 | TARIFA MENSAL POR BOLETO (ATÉ 03 ENVIOS) COBRANÇA ATIVA ELETRÔNICA | FEE |
| 89 | TARIFA MENSAL EMAIL COBRANÇA ATIVA ELETRÔNICA | FEE |
| 90 | TARIFA MENSAL SMS COBRANÇA ATIVA ELETRÔNICA | FEE |
| 91 | TARIFA MENSAL DE EXCLUSÃO DE ENTRADA DE NEGATIVAÇÃO EXPRESSA | FEE |
| 92 | TARIFA MENSAL DE CANCELAMENTO DE NEGATIVAÇÃO EXPRESSA | FEE |
| 93 | TARIFA MENSAL DE EXCLUSÃO DE NEGATIVAÇÃO EXPRESSA POR LIQUIDAÇÃO | FEE |
