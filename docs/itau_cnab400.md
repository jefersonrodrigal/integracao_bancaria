# Adaptador Itaú CNAB 400 — cobrança

**Status: implementado e testado com dados sintéticos. NÃO homologado com o Itaú.**

## 1. Fonte documental

| Item | Valor |
|---|---|
| Documento | *Cobrança Bancária — Intercâmbio Eletrônico de Arquivos — Layout de Arquivos — CNAB 400* |
| Emissor | Itaú Unibanco S.A. (Itaú Empresas) |
| Versão | JANEIRO 2017 (rodapé de todas as páginas); inclui novidades de fev/2016 e jan/2017 |
| Origem | PDF fornecido pelo usuário (`layout_cobranca_400bytes_cnab_itau.pdf`, 65 páginas) |
| Identificador no código | `layout_id = "ITAU_CNAB400"`, `manual_version = "2017-01"` |
| Produto | Cobrança bancária registrada (remessa e retorno) |

O documento CNAB 240 citado no pedido (`cobranca_cnab240.pdf`) **não** foi usado em nenhuma
regra deste adaptador. Antes de ir para produção, confirme com o Itaú se existe versão mais
recente do manual CNAB 400 (ver §8).

A tabela completa de campos, posições, pictures e referência de página fica em
[`itau_cnab400_campos.md`](itau_cnab400_campos.md). Ela é **gerada a partir do código**, e um
teste falha se o código e o documento divergirem.

## 2. Convenções do arquivo

| Regra | Origem |
|---|---|
| Registro de 400 posições, um por linha, arquivo texto sem compactação | Manual p.5 |
| Alfanumérico (X): alinhado à esquerda, brancos à direita, maiúsculo, sem acentos | Manual p.5 |
| Numérico (9): alinhado à direita, zeros à esquerda; não utilizado = zeros | Manual p.5 |
| Vírgula assumida (V): `9(5)V9(2)` com 876,54 → `0087654` | Manual p.5 (coberto por teste) |
| Datas `DDMMAA`; multa usa `DDMMAAAA` | Manual p.8, p.9 / Nota 35 |
| Sequencial 395-400 começando em 000001 no header | Manual p.7 |
| **Encoding da remessa: ASCII** (acentos removidos; caracteres fora do conjunto permitido são rejeitados) | Regra interna derivada da p.5 |
| **Encoding do retorno: lido como latin-1** (1 byte = 1 posição); bytes não ASCII geram aviso | Regra interna (o manual não especifica) |
| **Fim de linha: CRLF por padrão (configurável LF por perfil), inclusive após o último registro** | Regra interna (o manual não especifica) |
| Retorno: aceita CRLF ou LF; mistura é erro; 0x1A final é ignorado com aviso | Regra interna |

## 3. Registros

| Arquivo | Tipo | Uso no adaptador |
|---|---|---|
| Remessa | 0 Header | Gerado e validado (p.7) |
| Remessa | 1 Detalhe | Gerado e validado (p.8) |
| Remessa | 2 Multa (opcional) | Gerado quando o título tem multa (p.9, Nota 35) |
| Remessa | 4 Rateio de crédito | **Não gerado**; o validador só avisa (p.10-11) |
| Remessa | 5 E-mail / sacador-avalista | Gerado com e-mail (só escritural) e/ou sacador completo (p.12, Notas 29-30) |
| Remessa | 9 Trailer | Gerado e validado (p.12) |
| Remessa | 6 (emissão de boleto, seção 6) | **Não suportado** |
| Retorno | 0 Header, 1 Detalhe, 9 Trailer | Interpretados (p.13-14, 17) |
| Retorno | 1 Cheque devolvido/compensado (69/76) | Interpretado com o leiaute da p.15 |
| Retorno | 4 Rateio | Lido até a ocorrência; marcado para revisão manual |

Ordem gerada para cada título: `1`, depois `2` (se houver multa), depois `5` (se houver e-mail ou
sacador). O manual diz apenas que esses registros seguem o registro 1 ("sequência lógica"), sem
fixar a ordem entre 2 e 5.

## 4. Comandos de remessa suportados (Nota 6, p.19)

| Comando interno | Ocorrência | Campos preenchidos |
|---|---|---|
| `REGISTER` | 01 Remessa | Todos os campos do registro 1 |
| `WRITE_OFF` | 02 Pedido de baixa | Obs (A): tipo, agência/conta/DAC, nosso número, carteira, código da carteira, valor; demais campos zeros/brancos |
| `CHANGE_DUE_DATE` | 06 Alteração do vencimento | Obs (A) + vencimento |

As demais ocorrências da Nota 6 (abatimento, protesto, negativação etc.) passam no validador de
remessa com o aviso "sem validação semântica", mas **não são geradas** nesta versão.

## 5. Regras de validação do título

Toda `Issue` devolvida pela API traz `reference`, com a página/nota do manual ou o texto
`regra interna`.

**Confirmadas no manual:** valor > 0 (Nota 8); valor ≤ 10.000.000,00 (Tabela 1 cód. 07);
vencimento obrigatório (Nota 7); espécie da Nota 10; aceite A/N (p.8); nome, logradouro, CEP e UF
do pagador (Tabela 1 cód. 08/10/11/04); nome do pagador com até 40 posições (Nota 15); desconto
≤ 90% (Nota 13); abatimento menor que o valor (Tabela 3 cód. 10); IOF só na carteira 188 (Nota 14,
obs F) e ≤ 5% (Tabela 1 cód. 35); multa com data ≥ vencimento, valor < título e percentual < 100%
(Nota 35); e-mail só em carteira escritural (Nota 29); sacador com dados completos (Nota 30);
protesto e negativação não podem ser simultâneos (Nota 11 obs A); boleto de proposta (espécie 18)
sem juros, multa ou instruções (Anexo 7); nosso número zerado nas carteiras escriturais exceto
115 (Nota 3); nosso número dentro da faixa do Itaú quando a obs (D) se aplica.

**Regras internas (não estão no manual):** dígitos verificadores de CPF/CNPJ; cidade
obrigatória; vencimento ≥ emissão; data limite de desconto ≤ vencimento; prazo (392-393) só com
instrução que o utilize; instruções repetidas; nosso número único por perfil (mais restritivo que
a regra de 45 dias da Nota 3); nova data de vencimento não pode estar no passado.

**Instruções (Nota 11):** são aceitas apenas instruções sem dependência de campos extras (obs A,
G, H). As instruções 30, 33, 44, 93, 94 e 98 e as marcadas "USO DO BANCO" são rejeitadas com
`INSTRUCTION_UNSUPPORTED`. Instrução não utilizada é enviada em **brancos**, conforme a regra
geral da p.5. Ponto a confirmar na homologação (ver §8).

## 6. Nosso número e DAC

* Diretas (108, 109, 121, 180) e escritural 115: o nosso número é atribuído pela empresa e
  alocado em sequência por perfil, com trava de linha.
* Escriturais 112 e 188: enviado zerado. O banco devolve o número na confirmação (02), e o
  título é localizado pelo campo **uso da empresa** (38-62), que guarda `company_reference`.
* DAC pelo módulo 10 (Nota 23 / Anexo 4). Usa agência + conta + carteira + nosso número, exceto
  nas escriturais e nas carteiras de exceção, que usam carteira + nosso número. Os exemplos
  numéricos do manual são testes automatizados (`tests/unit/test_manual_examples.py`).
* O DAC agência/conta do perfil é conferido pelo módulo 10 (posição 41 do código de barras,
  p.49, e Anexo 3). Confere com o exemplo "0057/12345-7" do Anexo 2.

## 7. Retorno: interpretação e efeitos

O significado de cada código vem da Nota 17. O **efeito** sobre o título é decisão interna e
conservadora: na dúvida, `REVIEW_REQUIRED` e nenhuma transição de status. A tabela completa
está em [`itau_cnab400_campos.md`](itau_cnab400_campos.md#ocorrências-de-retorno-nota-17-p23-25-e-efeito-aplicado).

| Efeito | Códigos | Ação |
|---|---|---|
| ENTRY_CONFIRMED | 02, 64, 73 | `REMITTANCE_GENERATED/SENT_TO_BANK → REGISTERED`; grava nosso número devolvido |
| ENTRY_REJECTED | 03, 60 | `→ REJECTED`; códigos da Tabela 1 decodificados em `last_bank_message` |
| SETTLEMENT | 06, 08 | `→ PAID`; movimento `SETTLEMENT` = valor principal (254-266); conciliação |
| PARTIAL_SETTLEMENT | 07 | Movimento `PARTIAL_SETTLEMENT`; status mantido; revisão |
| WRITE_OFF | 09, 32, 47 | `REGISTERED/CANCEL_REQUESTED → CANCELLED` |
| WRITE_OFF_REJECTED | 15 | `CANCEL_REQUESTED → REGISTERED` (Tabela 4) |
| DUE_DATE_CHANGED | 14 | Atualiza o vencimento com o valor de 147-152 |
| INSTRUCTION_REJECTED | 16, 17, 18 | Informativo, com as Tabelas 3, 2 e 5 decodificadas |
| FEE | tarifas/custas | Movimento `FEE` negativo com o valor de 176-188 |
| REVIEW_REQUIRED | 05, 59, 63, 69, 72 | Sem transição; vira pendência de conciliação |
| INFORMATIONAL | demais | Registrado; o 10 sem liquidação prévia vira revisão |

Também:

* Qualquer registro com tarifa (176-188) > 0 gera **um** movimento `FEE` por ocorrência.
* Posição 107 = `I` (indicador 23.2 = 2, p.41) é registro informativo: não gera movimento.
* Código desconhecido → `UNKNOWN_CODE`, preservado, sem efeito.
* Título não localizado → `UNMATCHED` e conciliação `UNMATCHED`.
* Conciliação da liquidação (**regra interna**): divergência quando o valor nominal informado
  (153-165) difere do título, ou quando o valor principal ≠ valor − desconto − abatimento +
  juros/multa. O manual **não** define essa fórmula, então ela precisa ser confirmada na
  homologação.

## 8. Lacunas e ambiguidades documentais

| # | Ponto | Tratamento atual |
|---|---|---|
| 1 | Encoding e terminador de linha não especificados | ASCII + CRLF configurável (remessa); latin-1, CRLF/LF (retorno) |
| 2 | Instrução não utilizada: brancos ou "00"? | Brancos (regra geral p.5) |
| 3 | Obs (A) da Nota 6 manda zerar "demais campos" nas instruções 02/06, inclusive a inscrição da empresa | Seguido literalmente |
| 4 | Anexo 4 lista exceções de DAC 126-131-**146**-150-168; Nota 23 lista 126-131-**145**-150-168 | Ambas tratadas como exceção; nenhuma é suportada para emissão |
| 5 | Carteira 104: escritural (envia zerado, Nota 3) e obs (D) (faixa do Itaú) ao mesmo tempo | Carteira bloqueada até esclarecimento |
| 6 | Obs (E) da Nota 5 (108, 180, 150, 147) não tem texto explicativo | Sem regra associada |
| 7 | Posições dos códigos das Tabelas 11/12 (ocorrências 74/79) não informadas | Campo bruto preservado; sem decodificação |
| 8 | Semântica de "QTDE DE DETALHES" e "VLR TOTAL INFORMADO" do trailer de retorno | Divergência gera aviso, não erro |
| 9 | Fórmula do valor principal na liquidação | Regra interna (§7), pendente de confirmação |
| 10 | Ocorrência 05 "ALTERAÇÃO DE DADOS – BAIXA" ambígua | Revisão manual |
| 11 | Indicador 04.2 = 1 (header/trailer por conta) | Não suportado; múltiplos headers são erro estrutural |
| 12 | CNPJ alfanumérico (vigente desde jul/2026) não cabe em `9(14)` do manual de 2017 | Rejeitado; confirmar com o Itaú se há leiaute atualizado |
| 13 | Manual de 2017 pode ter sido revisado | Confirmar com o gerente a versão vigente antes da homologação |
| 14 | Nome do arquivo de remessa não definido | `CB<DDMMAA>_<carteira>_<id>.REM` (regra interna) |

## 9. Fora do escopo desta versão

Moeda variável (carteiras 147 e 150, qtde. de moeda 71-83); rateio de crédito (registro 4);
registro 6 (emissão de boleto pela empresa); impressão de boleto, código de barras e linha
digitável; instruções com campos extras; ocorrências de remessa além de 01/02/06; 2º e 3º
descontos (Nota 16); retorno mensal (código 11) com tratamento específico; transmissão
automática ao banco.
