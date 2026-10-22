# Operação

## Configuração (variáveis `IB_*`)

| Variável | Padrão | Descrição |
|---|---|---|
| `IB_DATABASE_URL` | **obrigatória** | `postgresql+psycopg://usuario:senha@host:5432/banco`; outros bancos são rejeitados |
| `IB_STORAGE_DIR` | `./data/files` | Arquivos bancários originais, endereçados por SHA-256 |
| `IB_MAX_UPLOAD_BYTES` | 5 MiB | Limite de upload; acima disso, HTTP 413 |
| `IB_API_KEYS` | vazio | `ator:papel:chave,...`; papéis `reader` < `operator` < `admin` |
| `IB_LOG_LEVEL` | `INFO` | Logs em JSON no stdout |
| `IB_TEST_DATABASE_URL` | — | Obrigatória para os testes que usam banco: PostgreSQL **dedicado a testes** (o esquema `public` é apagado e recriado a cada teste) |

Sem `IB_API_KEYS`, todas as rotas protegidas respondem 401.

## Perfis de acesso

| Papel | Pode |
|---|---|
| reader | Consultar títulos, remessas, retornos, ocorrências e conciliação; validar arquivo |
| operator | + cadastrar e alterar títulos, gerar, baixar, enviar e descartar remessas, importar e reprocessar retornos, resolver divergências |
| admin | + cadastrar bancos, contas e perfis |

## Rotina diária sugerida

1. `POST /api/v1/remittances` com os títulos do dia → `GET .../download`.
2. Enviar o arquivo **pelo canal autorizado da empresa** (Itaú Empresas). A aplicação não
   transmite ao banco.
3. `POST /api/v1/remittances/{id}/mark-sent`.
4. Importar cada retorno recebido: `POST /api/v1/returns`.
5. Tratar pendências: `GET /api/v1/reconciliation?resolved=false` e
   `GET /api/v1/occurrences?status=REVIEW_REQUIRED` (também `UNMATCHED`, `UNKNOWN_CODE`,
   `INVALID`).

## Diagnóstico de erros

| Sintoma | Causa provável | Ação |
|---|---|---|
| 422 ao criar título, `reference` com nota do manual | Dado fora da regra do Itaú | Corrigir o campo indicado em `field` |
| 422 `INVALID_STATUS` na remessa | Comando incompatível com o status | Ver a máquina de estados em `architecture.md` |
| 409 no upload de retorno | Arquivo já importado | Use o `file_id` devolvido; não reenvie |
| Retorno `INVALID` | Erro estrutural (tamanho, sequencial, header/trailer) | Ver `validation_report.errors` em `GET /returns/{id}` |
| Ocorrência `UNMATCHED` | Conta/carteira sem perfil ou título desconhecido | Cadastrar perfil ou investigar título |
| Ocorrência `UNKNOWN_CODE` | Código fora da Nota 17 | Consultar o Itaú; atualizar `tables.py` com referência |
| Retorno `PARTIALLY_PROCESSED` | Exceção numa linha | Ver `attempts[].summary.failures`, corrigir e `POST /returns/{id}/reprocess` |
| `/ready` 503 | Banco ou diretório de arquivos indisponível | Ver `checks` |
| 500 "Falha de integridade" | Arquivo armazenado alterado | Restaurar do backup; investigar acesso indevido |

## Segurança

* **TLS** termina no proxy reverso ou balanceador. O contêiner escuta HTTP só na rede interna, e
  o `compose.yaml` publica a porta apenas em `127.0.0.1`.
* Segredos (`IB_API_KEYS`, senha do banco) vêm do ambiente ou de um gerenciador de segredos;
  nunca do repositório.
* Os logs não incluem CPF/CNPJ, nomes nem linhas CNAB. A auditoria (`audit_event`) registra
  ator, ação e IDs.
* Os arquivos bancários contêm dados pessoais (LGPD): restrinja o acesso ao `IB_STORAGE_DIR`,
  com criptografia em repouso no volume.
* Todo download de remessa é auditado.

## Backup, retenção e recuperação

* PostgreSQL: `pg_dump` diário e WAL archiving para recuperação ponto a ponto. Teste a
  restauração mensalmente.
* `IB_STORAGE_DIR`: backup junto com o banco, porque o banco referencia os arquivos pelo hash. A
  integridade é verificada a cada leitura.
* Retenção: defina com o jurídico e o fiscal; o prazo usual é ≥ 5 anos para documentos fiscais
  e financeiros. A aplicação não apaga arquivos nem ocorrências.
* Recuperação de processamento: o reprocessamento é idempotente, então é seguro reexecutar
  `POST /returns/{id}/reprocess`.

## Migrações

```bash
alembic upgrade head      # aplicar
alembic check             # confirma que o modelo e as migrações estão alinhados
alembic revision --autogenerate -m "descrição"   # nova migração (revise antes de aplicar)
```
