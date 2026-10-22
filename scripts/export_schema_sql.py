"""Gera o DDL PostgreSQL a partir dos modelos e o insere no README.md (entre marcadores).

Uso: python -m scripts.export_schema_sql
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.infrastructure.database import models  # noqa: F401  (registra as tabelas)
from app.infrastructure.database.base import Base

README = Path(__file__).parents[1] / "README.md"
BEGIN = "<!-- schema:begin (gerado por scripts/export_schema_sql.py; não edite à mão) -->"
END = "<!-- schema:end -->"


def ddl() -> str:
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    statements: list[str] = []
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        for index in sorted(table.indexes, key=lambda i: i.name or ""):
            statements.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    body = "\n\n".join(s.replace("\t", "    ") for s in statements)
    body = "\n".join(line.rstrip() for line in body.splitlines())
    return f"{BEGIN}\n```sql\n{body}\n```\n{END}"


def render(readme: str) -> str:
    start, end = readme.index(BEGIN), readme.index(END) + len(END)
    return readme[:start] + ddl() + readme[end:]


def main() -> None:
    README.write_text(render(README.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    print(f"Esquema atualizado em {README}")


if __name__ == "__main__":
    main()
