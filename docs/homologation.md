# Guia de homologação — Itaú CNAB 400

O adaptador **não está homologado**. Todos os arquivos de teste do repositório são
**sintéticos**: foram montados a partir das posições do manual, não fornecidos pelo Itaú.

## Pré-requisitos

1. Confirmar com o gerente Itaú a **versão vigente** do manual CNAB 400 de cobrança. Se houver
   versão posterior a JANEIRO 2017, revisar `docs/itau_cnab400.md` §8 e as tabelas.
2. Obter agência, conta, DAC, carteira contratada e, para as carteiras com obs (D), a faixa de
   nosso número definida pelo Itaú.
3. Confirmar os indicadores de condições personalizadas (manual seção 5): 04.2, 23.2, 25.7,
   36.4, 37.2, 38.0, 40.6, 41.4 e 47.1. A interpretação do retorno depende deles.
4. Acesso ao Itaú Empresas → Transmissão de arquivos → **Validação** (validador on-line de
   leiaute, manual p.3 e p.43).

## Roteiro

| Passo | Ação | Evidência a guardar |
|---|---|---|
| 1 | Criar banco, conta e perfil (`POST /api/v1/profiles`) com os dados reais | JSON do perfil |
| 2 | Cadastrar até 30 títulos de teste (limite da fase de testes, p.43) cobrindo: CPF e CNPJ, multa, juros, desconto, sacador, instrução de protesto | Lista de títulos |
| 3 | Gerar a remessa e baixar o arquivo | Arquivo `.REM` e SHA-256 |
| 4 | Submeter ao **validador on-line** do Itaú | Relatório do validador |
| 5 | Corrigir divergências; registrar cada uma em `docs/itau_cnab400.md` §8 | Commit |
| 6 | Enviar pelo canal autorizado em ambiente de teste; `POST /remittances/{id}/mark-sent` | Protocolo de envio |
| 7 | Importar o retorno de teste (`POST /api/v1/returns`) | Relatório `GET /returns/{id}/report` |
| 8 | Conferir confirmações e rejeições contra o relatório do banco | Planilha de conferência |
| 9 | Testar baixa (02) e alteração de vencimento (06) | Retornos 09/15 e 14 |
| 10 | Conferir uma liquidação real contra o extrato (valor principal, tarifa, data de crédito) | Extrato e movimentos |
| 11 | Guardar um retorno real **anonimizado** como fixture `tests/fixtures/oficial/` com teste de regressão | Fixture + teste |

## Pontos a confirmar explicitamente com o Itaú

* CRLF após o último registro e encoding aceito.
* Instrução não utilizada: brancos ou "00".
* Preenchimento das ocorrências 02/06: zerar a inscrição da empresa e o uso da empresa (obs A).
* Ordem dos registros 2 e 5 após o registro 1.
* Fórmula do "valor principal" na liquidação (desconto, abatimento, juros, outros créditos).
* Significado de "QTDE DE DETALHES" e "VLR TOTAL INFORMADO" no trailer de retorno.
* Posição dos códigos das Tabelas 11 e 12 (ocorrências 74 e 79).
* Tratamento do CNPJ alfanumérico neste leiaute.
* Tarifas: se os débitos mensais (30, 40-46, 51-55...) se sobrepõem às tarifas por evento
  conforme o contrato (indicador 47.1). Isso evita contar tarifa em dobro.

## Critério para declarar homologado

Validador on-line sem erros, retorno de teste processado sem `UNKNOWN_CODE` nem `INVALID`
inesperados, conciliação de liquidação real batendo com o extrato e evidências arquivadas. Só
então altere o status no topo de `docs/itau_cnab400.md`.
