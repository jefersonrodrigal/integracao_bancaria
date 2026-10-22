# Integração Bancária 
API para o ciclo de cobrança registrada: cadastro de títulos → remessa → retorno → conciliação.
Primeiro adaptador: **Itaú CNAB 400**, conforme o manual *Layout de Arquivos — CNAB 400*,
versão **JANEIRO 2017**.

> **Status:** implementado e testado com arquivos **sintéticos**. **Não homologado** com o Itaú.
> Veja [docs/homologation.md](docs/homologation.md) antes de usar em produção.

## Requisitos

Python 3.12+ (testado em 3.15.0) e PostgreSQL 15+ (testado em 18.6). Não há suporte a outro banco.

## Início rápido

```bash
python -m venv .venv
.venv/Scripts/activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.lock -e ".[dev]"
createdb integracao_bancaria      # e integracao_bancaria_test para os testes
cp .env.example .env              # ajuste usuário, senha e chaves de API
alembic upgrade head
python -m scripts.seed_dev        # opcional: dados SINTÉTICOS (perfil Itaú 109 + 3 títulos)
uvicorn app.main:app --reload
```

A documentação OpenAPI fica em <http://127.0.0.1:8000/docs>. Toda rota `/api/v1` exige o
cabeçalho `X-API-Key`.

```bash
H="X-API-Key: troque-esta-chave-admin"
curl -H "$H" -H "Content-Type: application/json" \
     -d '{"profile_id":1,"items":[{"title_id":1},{"title_id":2}]}' \
     http://127.0.0.1:8000/api/v1/remittances
curl -H "$H" -OJ http://127.0.0.1:8000/api/v1/remittances/1/download
curl -H "$H" -F file=@RETORNO.RET http://127.0.0.1:8000/api/v1/returns
```

## Docker (PostgreSQL)

```bash
export POSTGRES_PASSWORD=... IB_API_KEYS="admin:admin:<chave-16+>"
docker compose up --build
```

O contêiner aplica as migrações e sobe a API em `127.0.0.1:8000`. Em produção, coloque um proxy
com TLS na frente.

## Testes e qualidade

```bash
pytest                 # unitários, integração (API) e contrato (OpenAPI, migrações)
# Requer IB_TEST_DATABASE_URL (ambiente ou .env) apontando para um PostgreSQL EXCLUSIVO de
# testes: o esquema é apagado e recriado a cada teste.
ruff check . && ruff format --check .
mypy                   # modo strict
python -m scripts.export_layout_doc   # regenera docs/itau_cnab400_campos.md
python -m scripts.export_schema_sql   # regenera o esquema SQL do README
```

## Endpoints (`/api/v1`)

| Grupo | Rotas |
|---|---|
| Configuração | `GET /layouts`, `POST/GET /banks`, `POST/GET /bank-accounts`, `POST/GET /profiles`, `GET /profiles/{id}` |
| Títulos | `POST /titles`, `GET /titles`, `GET /titles/{id}`, `PATCH /titles/{id}` |
| Remessas | `POST /remittances`, `GET /remittances`, `GET /remittances/{id}`, `GET /remittances/{id}/download`, `POST /remittances/{id}/mark-sent`, `POST /remittances/{id}/discard`, `POST /remittances/validate` |
| Retornos | `POST /returns`, `GET /returns`, `GET /returns/{id}`, `GET /returns/{id}/report`, `POST /returns/{id}/reprocess` |
| Ocorrências e conciliação | `GET /occurrences`, `GET /occurrences/{id}`, `GET /reconciliation`, `GET /reconciliation/{id}`, `POST /reconciliation/{id}/resolve`, `GET /movements` |
| Operação (sem prefixo) | `GET /health`, `GET /ready` |

## Esquema do banco de dados (PostgreSQL)

O esquema é criado e versionado pelo Alembic (`alembic upgrade head`); **não aplique o DDL abaixo
manualmente** em bancos gerenciados pelo Alembic. O DDL é gerado a partir dos modelos
(`app/infrastructure/database/models.py`) e um teste falha se esta seção divergir do código.
Regenerar: `python -m scripts.export_schema_sql`. Além destas tabelas, o Alembic mantém
`alembic_version`.

| Tabela | Conteúdo |
|---|---|
| `bank` | Bancos (código de compensação, ex.: 341) |
| `bank_account` | Contas do beneficiário (agência, conta, DAC, titular) |
| `bank_integration_profile` | Perfil de cobrança: conta + carteira + leiaute/versão do manual + faixa de nosso número |
| `customer` | Pagadores (CPF/CNPJ e endereço) |
| `receivable_title` | Títulos a receber, status, nosso número, encargos, liquidação; `version` = trava otimista |
| `bank_file` | Arquivos de remessa e retorno (SHA-256, relatório de validação); `dedup_key` impede reimportar retorno |
| `file_processing_attempt` | Cada tentativa de processamento de retorno, com resumo e falhas |
| `remittance_batch` / `remittance_batch_item` | Lote de remessa e o comando (01/02/06) de cada título, com status anterior e novo |
| `bank_occurrence` | Cada linha de retorno: linha original, campos interpretados, efeito; `idempotency_key` única |
| `reconciliation_result` | Resultado da conciliação por ocorrência (MATCHED/DIVERGENT/UNMATCHED) e resolução |
| `financial_movement` | Movimentos financeiros (liquidação +, tarifa −); no máximo um por tipo e ocorrência |
| `audit_event` | Trilha de auditoria (ator, ação, entidade), sem dados pessoais |

Valores monetários usam `NUMERIC(15,2)`; datas e horas, `TIMESTAMP WITH TIME ZONE` (UTC).
Códigos de status são texto (ver `app/domain/enums.py`).

<!-- schema:begin (gerado por scripts/export_schema_sql.py; não edite à mão) -->
```sql
CREATE TABLE audit_event (
    id SERIAL NOT NULL,
    actor VARCHAR(100) NOT NULL,
    action VARCHAR(60) NOT NULL,
    entity_type VARCHAR(40) NOT NULL,
    entity_id VARCHAR(40) NOT NULL,
    data JSON,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_audit_event PRIMARY KEY (id)
);

CREATE INDEX ix_audit_event_action ON audit_event (action);

CREATE TABLE bank (
    id SERIAL NOT NULL,
    code VARCHAR(3) NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_bank PRIMARY KEY (id),
    CONSTRAINT uq_bank_code UNIQUE (code)
);

CREATE TABLE customer (
    id SERIAL NOT NULL,
    name VARCHAR(100) NOT NULL,
    document_type VARCHAR(4) NOT NULL,
    document VARCHAR(14) NOT NULL,
    email VARCHAR(120),
    street VARCHAR(100) NOT NULL,
    district VARCHAR(60) NOT NULL,
    zip_code VARCHAR(8) NOT NULL,
    city VARCHAR(60) NOT NULL,
    state VARCHAR(2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_customer PRIMARY KEY (id),
    CONSTRAINT uq_customer_document_type_document UNIQUE (document_type, document)
);

CREATE TABLE bank_account (
    id SERIAL NOT NULL,
    bank_id INTEGER NOT NULL,
    agency VARCHAR(4) NOT NULL,
    account VARCHAR(5) NOT NULL,
    account_dac VARCHAR(1) NOT NULL,
    holder_name VARCHAR(100) NOT NULL,
    holder_document_type VARCHAR(4) NOT NULL,
    holder_document VARCHAR(14) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_bank_account PRIMARY KEY (id),
    CONSTRAINT uq_bank_account_bank_id_agency_account_account_dac UNIQUE (bank_id, agency, account, account_dac),
    CONSTRAINT fk_bank_account_bank_id_bank FOREIGN KEY(bank_id) REFERENCES bank (id)
);

CREATE TABLE bank_integration_profile (
    id SERIAL NOT NULL,
    bank_account_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    layout_id VARCHAR(40) NOT NULL,
    manual_version VARCHAR(20) NOT NULL,
    wallet VARCHAR(3) NOT NULL,
    company_name VARCHAR(30) NOT NULL,
    nosso_numero_min INTEGER,
    nosso_numero_max INTEGER,
    next_nosso_numero INTEGER,
    line_terminator VARCHAR(4) NOT NULL,
    active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_bank_integration_profile PRIMARY KEY (id),
    CONSTRAINT uq_bank_integration_profile_bank_account_id_wallet UNIQUE (bank_account_id, wallet),
    CONSTRAINT fk_bank_integration_profile_bank_account_id_bank_account FOREIGN KEY(bank_account_id) REFERENCES bank_account (id)
);

CREATE TABLE bank_file (
    id SERIAL NOT NULL,
    direction VARCHAR(12) NOT NULL,
    layout_id VARCHAR(40) NOT NULL,
    manual_version VARCHAR(20) NOT NULL,
    profile_id INTEGER,
    filename VARCHAR(255) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    dedup_key VARCHAR(80),
    size INTEGER NOT NULL,
    storage_key VARCHAR(255) NOT NULL,
    status VARCHAR(30) NOT NULL,
    validation_report JSON,
    header_info JSON,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_bank_file PRIMARY KEY (id),
    CONSTRAINT fk_bank_file_profile_id_bank_integration_profile FOREIGN KEY(profile_id) REFERENCES bank_integration_profile (id),
    CONSTRAINT uq_bank_file_dedup_key UNIQUE (dedup_key)
);

CREATE INDEX ix_bank_file_sha256 ON bank_file (sha256);

CREATE TABLE receivable_title (
    id SERIAL NOT NULL,
    profile_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    company_reference VARCHAR(25) NOT NULL,
    document_number VARCHAR(10) NOT NULL,
    species VARCHAR(2) NOT NULL,
    acceptance VARCHAR(1) NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    nosso_numero VARCHAR(8),
    nosso_numero_dac VARCHAR(1),
    interest_per_day NUMERIC(15, 2),
    interest_start_date DATE,
    discount_amount NUMERIC(15, 2),
    discount_limit_date DATE,
    rebate_amount NUMERIC(15, 2),
    iof_amount NUMERIC(15, 2),
    fine_type VARCHAR(10),
    fine_date DATE,
    fine_value NUMERIC(15, 2),
    instruction1 VARCHAR(2),
    instruction2 VARCHAR(2),
    protest_days INTEGER,
    guarantor JSON,
    send_email BOOLEAN NOT NULL,
    status VARCHAR(30) NOT NULL,
    last_bank_message JSON,
    paid_amount NUMERIC(15, 2),
    paid_at DATE,
    credit_date DATE,
    version INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_receivable_title PRIMARY KEY (id),
    CONSTRAINT uq_receivable_title_profile_id_nosso_numero UNIQUE (profile_id, nosso_numero),
    CONSTRAINT fk_receivable_title_profile_id_bank_integration_profile FOREIGN KEY(profile_id) REFERENCES bank_integration_profile (id),
    CONSTRAINT fk_receivable_title_customer_id_customer FOREIGN KEY(customer_id) REFERENCES customer (id),
    CONSTRAINT uq_receivable_title_company_reference UNIQUE (company_reference)
);

CREATE INDEX ix_receivable_title_status ON receivable_title (status);

CREATE TABLE bank_occurrence (
    id SERIAL NOT NULL,
    bank_file_id INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    raw_line VARCHAR(400) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL,
    profile_id INTEGER,
    title_id INTEGER,
    record_type VARCHAR(1) NOT NULL,
    occurrence_code VARCHAR(4) NOT NULL,
    occurrence_description VARCHAR(200),
    effect VARCHAR(30),
    occurrence_date DATE,
    nosso_numero VARCHAR(8),
    company_reference VARCHAR(25),
    wallet VARCHAR(3),
    amount NUMERIC(15, 2),
    principal_amount NUMERIC(15, 2),
    fee_amount NUMERIC(15, 2),
    processing_status VARCHAR(30) NOT NULL,
    message TEXT,
    parsed JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_bank_occurrence PRIMARY KEY (id),
    CONSTRAINT fk_bank_occurrence_bank_file_id_bank_file FOREIGN KEY(bank_file_id) REFERENCES bank_file (id),
    CONSTRAINT uq_bank_occurrence_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT fk_bank_occurrence_profile_id_bank_integration_profile FOREIGN KEY(profile_id) REFERENCES bank_integration_profile (id),
    CONSTRAINT fk_bank_occurrence_title_id_receivable_title FOREIGN KEY(title_id) REFERENCES receivable_title (id)
);

CREATE INDEX ix_bank_occurrence_bank_file_id ON bank_occurrence (bank_file_id);

CREATE INDEX ix_bank_occurrence_occurrence_code ON bank_occurrence (occurrence_code);

CREATE INDEX ix_bank_occurrence_processing_status ON bank_occurrence (processing_status);

CREATE INDEX ix_bank_occurrence_title_id ON bank_occurrence (title_id);

CREATE TABLE file_processing_attempt (
    id SERIAL NOT NULL,
    bank_file_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    actor VARCHAR(100) NOT NULL,
    summary JSON,
    error TEXT,
    CONSTRAINT pk_file_processing_attempt PRIMARY KEY (id),
    CONSTRAINT fk_file_processing_attempt_bank_file_id_bank_file FOREIGN KEY(bank_file_id) REFERENCES bank_file (id)
);

CREATE INDEX ix_file_processing_attempt_bank_file_id ON file_processing_attempt (bank_file_id);

CREATE TABLE remittance_batch (
    id SERIAL NOT NULL,
    profile_id INTEGER NOT NULL,
    bank_file_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    record_count INTEGER NOT NULL,
    title_count INTEGER NOT NULL,
    total_amount NUMERIC(15, 2) NOT NULL,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_remittance_batch PRIMARY KEY (id),
    CONSTRAINT fk_remittance_batch_profile_id_bank_integration_profile FOREIGN KEY(profile_id) REFERENCES bank_integration_profile (id),
    CONSTRAINT uq_remittance_batch_bank_file_id UNIQUE (bank_file_id),
    CONSTRAINT fk_remittance_batch_bank_file_id_bank_file FOREIGN KEY(bank_file_id) REFERENCES bank_file (id)
);

CREATE TABLE financial_movement (
    id SERIAL NOT NULL,
    occurrence_id INTEGER NOT NULL,
    title_id INTEGER,
    kind VARCHAR(20) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    movement_date DATE,
    credit_date DATE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_financial_movement PRIMARY KEY (id),
    CONSTRAINT uq_financial_movement_occurrence_id_kind UNIQUE (occurrence_id, kind),
    CONSTRAINT fk_financial_movement_occurrence_id_bank_occurrence FOREIGN KEY(occurrence_id) REFERENCES bank_occurrence (id),
    CONSTRAINT fk_financial_movement_title_id_receivable_title FOREIGN KEY(title_id) REFERENCES receivable_title (id)
);

CREATE INDEX ix_financial_movement_title_id ON financial_movement (title_id);

CREATE TABLE reconciliation_result (
    id SERIAL NOT NULL,
    occurrence_id INTEGER NOT NULL,
    title_id INTEGER,
    status VARCHAR(20) NOT NULL,
    expected_amount NUMERIC(15, 2),
    received_amount NUMERIC(15, 2),
    difference NUMERIC(15, 2),
    reasons JSON NOT NULL,
    resolved BOOLEAN NOT NULL,
    resolution_note TEXT,
    resolved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_reconciliation_result PRIMARY KEY (id),
    CONSTRAINT uq_reconciliation_result_occurrence_id UNIQUE (occurrence_id),
    CONSTRAINT fk_reconciliation_result_occurrence_id_bank_occurrence FOREIGN KEY(occurrence_id) REFERENCES bank_occurrence (id),
    CONSTRAINT fk_reconciliation_result_title_id_receivable_title FOREIGN KEY(title_id) REFERENCES receivable_title (id)
);

CREATE INDEX ix_reconciliation_result_status ON reconciliation_result (status);

CREATE INDEX ix_reconciliation_result_title_id ON reconciliation_result (title_id);

CREATE TABLE remittance_batch_item (
    id SERIAL NOT NULL,
    batch_id INTEGER NOT NULL,
    title_id INTEGER NOT NULL,
    command VARCHAR(20) NOT NULL,
    occurrence_code VARCHAR(2) NOT NULL,
    line_number INTEGER NOT NULL,
    previous_status VARCHAR(30) NOT NULL,
    new_status VARCHAR(30) NOT NULL,
    new_due_date DATE,
    CONSTRAINT pk_remittance_batch_item PRIMARY KEY (id),
    CONSTRAINT uq_remittance_batch_item_batch_id_title_id_command UNIQUE (batch_id, title_id, command),
    CONSTRAINT fk_remittance_batch_item_batch_id_remittance_batch FOREIGN KEY(batch_id) REFERENCES remittance_batch (id),
    CONSTRAINT fk_remittance_batch_item_title_id_receivable_title FOREIGN KEY(title_id) REFERENCES receivable_title (id)
);

CREATE INDEX ix_remittance_batch_item_title_id ON remittance_batch_item (title_id);
```
<!-- schema:end -->

## O que é confirmado, interno, sintético ou pendente

| Categoria | Conteúdo |
|---|---|
| **Confirmado no manual** | Posições e pictures de todos os registros (gerados em [docs/itau_cnab400_campos.md](docs/itau_cnab400_campos.md)); carteiras, espécies, instruções; ocorrências de remessa e retorno; Tabelas 1-12 da Nota 20; código de liquidação; DAC do nosso número (exemplos do manual testados) |
| **Regra interna** | Máquina de estados; efeito de cada ocorrência; fórmula de conciliação; encoding e fim de linha; dígitos de CPF/CNPJ; idempotência; nome do arquivo |
| **Dados sintéticos** | Tudo em `tests/fixtures` e `scripts/seed_dev.py`. **Nenhum arquivo oficial do Itaú** |
| **Não implementado** | Moeda variável, rateio (registro 4), registro 6, boleto e código de barras, instruções 04/05/09/10/18/31/35..., transmissão automática, CNAB 240 e outros bancos |
| **Implementado, não homologado** | Todo o adaptador Itaú CNAB 400 |

Lacunas documentais e decisões: [docs/itau_cnab400.md §8](docs/itau_cnab400.md#8-lacunas-e-ambiguidades-documentais).

## Documentação

* [Arquitetura, modelo de dados e máquina de estados](docs/architecture.md)
* [Adaptador Itaú CNAB 400](docs/itau_cnab400.md) e [tabela de campos](docs/itau_cnab400_campos.md)
* [Homologação](docs/homologation.md)
* [Operação, segurança e diagnóstico](docs/operations.md)
* [Novos adaptadores (CNAB 240, outros bancos)](docs/new_adapters.md)

## Limitações conhecidas

* Sem transmissão ao banco: o arquivo é baixado e enviado pelo canal autorizado da empresa.
* Autenticação por chave de API estática. Para produção, integre um provedor OIDC.
* Processamento de retorno síncrono na requisição; adequado a arquivos até o limite configurado.
* O manual de 2017 é anterior ao CNPJ alfanumérico (2026); inscrições alfanuméricas são
  rejeitadas.
* Migrações e suíte testadas em PostgreSQL 18. A imagem Docker não foi testada (Docker
  indisponível no ambiente de desenvolvimento).
