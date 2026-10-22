# Como adicionar CNAB 240 ou outro banco

O domínio, a persistência, a API e a conciliação já são independentes de banco e leiaute. Um
novo par banco/leiaute é um **adaptador isolado** registrado em `app/cnab/registry.py`.

## Regra principal

Cada regra do novo adaptador precisa vir do manual oficial **daquele** banco e leiaute, com
referência de página. Não copie regras do adaptador Itaú CNAB 400: o CNAB 240 tem outra
estrutura (header e trailer de lote, segmentos P/Q/R/T/U, 240 posições) e outros códigos.

## Passo a passo

1. Obter o manual oficial e registrar título, versão e origem no topo de um novo
   `docs/<banco>_<leiaute>.md`.
2. Criar o pacote `app/cnab/layouts/<banco>/<leiaute>/` com:
   * `records.py`: `RecordLayout` de cada registro ou segmento, com `reference="p.X"` em
     todos os campos (o `RecordLayout` garante cobertura contígua; use `length=240` no CNAB 240);
   * `tables.py`: códigos de ocorrência mapeados para `OccurrenceEffect`, carteiras, espécies;
   * `rules.py`: validação de perfil e título;
   * `adapter.py`: classe que implementa o protocolo `BankLayoutAdapter` (`app/cnab/base.py`).
3. Reutilizar o núcleo: `Field`/`RecordLayout` (formatação e parse),
   `validators.split_records`/`check_sequence`, `checksums.mod10`. Se o leiaute exigir um
   recurso genérico novo (ex.: contagem por lote do CNAB 240), adicione-o ao núcleo `app/cnab/`
   com testes próprios, sem colocá-lo dentro de um banco específico.
4. Registrar: `register(NovoAdapter())` em `app/cnab/registry.py`. O `layout_id` deve ser
   único (ex.: `ITAU_CNAB240`, `BB_CNAB400`).
5. `looks_like_return` precisa ser específico o bastante para não colidir com outros
   adaptadores. Se dois reconhecerem o mesmo arquivo, a importação exige o parâmetro
   `layout_id`; nunca há escolha silenciosa.
6. Testes obrigatórios: posições conferidas contra o manual, exemplos numéricos do manual,
   golden file montado de forma independente, parser de retorno e ciclo de integração pela API
   com um perfil do novo leiaute.
7. Gerar a documentação de campos (adapte `scripts/export_layout_doc.py`) e seguir um guia de
   homologação equivalente a `docs/homologation.md`.

## CNAB 240: pontos de atenção

* `RecordLayout(length=240)` já é suportado; o validador estrutural recebe o tamanho do registro.
* O CNAB 240 tem hierarquia arquivo → lote → segmentos. Um título ocupa vários registros
  (ex.: P + Q + R), o que exige um agrupador no adaptador e trailers de lote com contagens e
  somatórios.
* `ReturnDetail` já carrega os campos que a conciliação usa. O adaptador 240 precisa juntar os
  segmentos T + U num único `ReturnDetail`.
* O protocolo não muda; a aplicação continua chamando `generate_remittance`,
  `validate_remittance`, `parse_return` e `describe_occurrence`.
