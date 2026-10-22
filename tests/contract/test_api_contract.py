"""Contrato público: endpoints exigidos e migração equivalente ao modelo."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.infrastructure.database.base import Base
from tests.conftest import require_test_database, reset_schema

ROOT = Path(__file__).parents[2]

REQUIRED = [
    ("post", "/api/v1/titles"),
    ("get", "/api/v1/titles"),
    ("get", "/api/v1/titles/{title_id}"),
    ("patch", "/api/v1/titles/{title_id}"),
    ("post", "/api/v1/remittances"),
    ("get", "/api/v1/remittances"),
    ("get", "/api/v1/remittances/{remittance_id}"),
    ("get", "/api/v1/remittances/{remittance_id}/download"),
    ("post", "/api/v1/returns"),
    ("get", "/api/v1/returns"),
    ("get", "/api/v1/returns/{return_id}"),
    ("get", "/api/v1/returns/{return_id}/report"),
    ("get", "/api/v1/occurrences"),
    ("get", "/api/v1/reconciliation"),
    ("get", "/api/v1/reconciliation/{reconciliation_id}"),
    ("get", "/health"),
    ("get", "/ready"),
]


@pytest.mark.parametrize(("method", "path"), REQUIRED)
def test_required_endpoints_are_documented(client: TestClient, method: str, path: str) -> None:
    spec = client.get("/openapi.json").json()
    assert method in spec["paths"][path]


def test_api_key_scheme_is_documented(client: TestClient) -> None:
    schemes = client.get("/openapi.json").json()["components"]["securitySchemes"]
    assert any(s.get("name") == "X-API-Key" for s in schemes.values())


def test_migrations_build_the_same_schema_as_the_models() -> None:
    url = require_test_database()
    engine = create_engine(url)
    reset_schema(engine, create=False)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == []
    command.downgrade(config, "base")


def test_field_documentation_is_up_to_date() -> None:
    from scripts.export_layout_doc import OUTPUT, render

    assert OUTPUT.read_text(encoding="utf-8") == render(), (
        "Execute: python -m scripts.export_layout_doc"
    )


def test_readme_schema_is_up_to_date() -> None:
    from scripts.export_schema_sql import README, render

    content = README.read_text(encoding="utf-8")
    assert content == render(content), "Execute: python -m scripts.export_schema_sql"
