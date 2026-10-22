# Arquitetura

## Camadas

```mermaid
flowchart LR
    subgraph API["app/api (FastAPI)"]
        R[routes] --> D[dependencies: sessão, storage, X-API-Key]
    end
    subgraph APP["app/application (casos de uso)"]
        TS[title_service]
        RS[remittance_service]
        RT[return_service]
        RC[reconciliation_service]
    end
    subgraph DOM["app/domain"]
        E[enums / erros]
        SM[máquina de estados]
        VO[CPF/CNPJ/UF]
    end
    subgraph CNAB["app/cnab (núcleo de leiaute)"]
        F[fields: Field/RecordLayout]
        V[validators: linhas/sequencial]
        B[base: DTOs + BankLayoutAdapter]
        REG[registry]
        IT[layouts/itau/cnab400]
    end
    subgraph INF["app/infrastructure"]
        DB[(SQLAlchemy / PostgreSQL)]
        ST[(LocalFileStorage SHA-256)]
    end
    R --> APP
    APP --> DOM
    APP --> REG --> IT
    IT --> F & V & B
    APP --> DB & ST
```

Dependências apontam para dentro. O domínio não conhece banco de dados nem leiaute. Os
adaptadores trocam apenas DTOs (`app/cnab/base.py`) e não conhecem o ORM. A conciliação recebe
o `ReturnDetail` já interpretado, sem depender do parser físico.

## Ciclo remessa → retorno

```mermaid
sequenceDiagram
    participant U as Operador
    participant API
    participant A as Adaptador Itaú 400
    participant DB as Banco de dados
    participant FS as Armazenamento
    U->>API: POST /titles
    API->>A: validate_item (regras do manual)
    API->>DB: título OPEN
    U->>API: POST /remittances
    API->>A: generate_remittance + validate_remittance
    API->>FS: arquivo original (SHA-256)
    API->>DB: lote, itens, títulos REMITTANCE_GENERATED
    U->>API: GET /remittances/{id}/download → envio pelo canal autorizado
    U->>API: POST /remittances/{id}/mark-sent
    U->>API: POST /returns (arquivo do banco)
    API->>DB: arquivo (dedup por SHA-256) + tentativa
    API->>A: parse_return (estrutura → INVALID se falhar)
    loop cada detalhe (SAVEPOINT)
        API->>DB: ocorrência (chave idempotente única)
        API->>DB: transição de status, movimento, conciliação
    end
```

## Modelo de dados

```mermaid
erDiagram
    bank ||--o{ bank_account : possui
    bank_account ||--o{ bank_integration_profile : "carteira + leiaute"
    bank_integration_profile ||--o{ receivable_title : cobra
    customer ||--o{ receivable_title : paga
    bank_integration_profile ||--o{ remittance_batch : gera
    remittance_batch ||--|| bank_file : arquivo
    remittance_batch ||--o{ remittance_batch_item : contém
    remittance_batch_item }o--|| receivable_title : comando
    bank_file ||--o{ file_processing_attempt : tentativas
    bank_file ||--o{ bank_occurrence : linhas
    bank_occurrence }o--o| receivable_title : afeta
    bank_occurrence ||--o| reconciliation_result : concilia
    bank_occurrence ||--o{ financial_movement : "≤1 por tipo"
```

Restrições relevantes:

* `bank_file.dedup_key` é único: um arquivo de retorno não é reimportado.
* `bank_occurrence.idempotency_key` é único: é o SHA-256 do layout mais as posições 1-394, sem o
  sequencial. O mesmo evento reenviado em outro arquivo é ignorado.
* `financial_movement (occurrence_id, kind)` é único: no máximo um movimento de cada tipo por
  ocorrência.
* `receivable_title (profile_id, nosso_numero)` e `company_reference` são únicos.
* `receivable_title.version` serve de trava otimista (`version_id_col`).
* `bank_integration_profile (bank_account_id, wallet)` é único: a resolução de perfil no
  retorno é determinística.
* Valores monetários: `NUMERIC(15,2)` (tipo `Money`), sem arredondamento silencioso.

## Máquina de estados do título (regra interna)

```mermaid
stateDiagram-v2
    [*] --> OPEN
    OPEN --> REMITTANCE_GENERATED: remessa 01 gerada
    REMITTANCE_GENERATED --> OPEN: remessa descartada
    REMITTANCE_GENERATED --> SENT_TO_BANK: mark-sent
    REMITTANCE_GENERATED --> REGISTERED: retorno 02
    SENT_TO_BANK --> REGISTERED: retorno 02/64/73
    REMITTANCE_GENERATED --> REJECTED: retorno 03/60
    SENT_TO_BANK --> REJECTED: retorno 03/60
    REJECTED --> OPEN: PATCH (correção)
    REGISTERED --> CANCEL_REQUESTED: remessa 02 gerada
    CANCEL_REQUESTED --> REGISTERED: retorno 15 ou descarte
    REGISTERED --> CANCELLED: retorno 09/32/47
    CANCEL_REQUESTED --> CANCELLED: retorno 09/32/47
    REGISTERED --> PAID: retorno 06/08
    SENT_TO_BANK --> PAID: retorno 06/08
    CANCEL_REQUESTED --> PAID: retorno 06/08
    CANCELLED --> PAID: liquidação após baixa (divergência)
    PAID --> [*]
```

`OVERDUE` não é persistido. A API o expõe como `is_overdue` (título `REGISTERED`/`SENT_TO_BANK`
com vencimento passado), porque é uma condição temporal e não um evento confirmado pelo banco.
Transições não previstas viram `REVIEW_REQUIRED` na ocorrência, sem alterar o título.

## Transações e falhas

* A remessa é gerada numa única transação. Se o arquivo gerado não passa no validador do
  próprio adaptador, nada é persistido.
* No retorno, o arquivo original é gravado e confirmado antes do processamento. Cada linha roda
  num SAVEPOINT. Uma falha numa linha não desfaz as outras; o arquivo fica
  `PARTIALLY_PROCESSED`, e `POST /returns/{id}/reprocess` processa só o que faltou.
* Concorrência: as restrições únicas acima protegem contra reimportação simultânea. A alocação
  de nosso número usa `SELECT ... FOR UPDATE` no perfil.
