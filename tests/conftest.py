from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.core.config import Settings
from app.infrastructure.database.base import Base
from app.main import create_app

ADMIN_KEY = "admin-key-0123456789"
OPERATOR_KEY = "oper-key-0123456789"
READER_KEY = "read-key-0123456789"

# Banco PostgreSQL DEDICADO a testes: o esquema public é apagado e recriado a cada teste.
TEST_DATABASE_URL = os.environ.get("IB_TEST_DATABASE_URL") or dotenv_values(
    Path(__file__).parents[1] / ".env"
).get("IB_TEST_DATABASE_URL")


def require_test_database() -> str:
    if not TEST_DATABASE_URL:
        pytest.fail("Defina IB_TEST_DATABASE_URL (ambiente ou .env) com um PostgreSQL de testes")
    return TEST_DATABASE_URL


# Dados SINTÉTICOS. Agência/conta 0057/12345-7 vêm do exemplo do Anexo 2 do manual.
COMPANY_CNPJ = "11222333000181"
PAYER_CPF = "52998224725"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url=require_test_database(),
        storage_dir=tmp_path / "files",
        max_upload_bytes=20_000,
        api_keys=f"admin:admin:{ADMIN_KEY},op:operator:{OPERATOR_KEY},ro:reader:{READER_KEY}",
        log_level="WARNING",
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    reset_schema(application.state.engine)
    yield application
    application.state.engine.dispose()


def reset_schema(engine: Engine, create: bool = True) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    if create:
        Base.metadata.create_all(engine)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, headers={"X-API-Key": ADMIN_KEY})


def make_profile(client: TestClient, wallet: str = "109", **extra: Any) -> dict[str, Any]:
    banks = client.get("/api/v1/banks").json()
    bank = (
        banks[0]
        if banks
        else client.post("/api/v1/banks", json={"code": "341", "name": "ITAU UNIBANCO"}).json()
    )
    accounts = client.get("/api/v1/bank-accounts").json()
    account = (
        accounts[0]
        if accounts
        else client.post(
            "/api/v1/bank-accounts",
            json={
                "bank_id": bank["id"],
                "agency": "0057",
                "account": "12345",
                "account_dac": "7",
                "holder_name": "EMPRESA SINTETICA LTDA",
                "holder_document_type": "CNPJ",
                "holder_document": COMPANY_CNPJ,
            },
        ).json()
    )
    response = client.post(
        "/api/v1/profiles",
        json={
            "bank_account_id": account["id"],
            "name": f"Carteira {wallet}",
            "layout_id": "ITAU_CNAB400",
            "wallet": wallet,
            "company_name": "EMPRESA SINTETICA LTDA",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def title_payload(profile_id: int, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "profile_id": profile_id,
        "document_number": "NF0001",
        "issue_date": "2026-10-01",
        "due_date": "2026-11-01",
        "amount": "123.45",
        "payer": {
            "name": "José da Silva",
            "document_type": "CPF",
            "document": "529.982.247-25",
            "street": "Rua das Flores, 10",
            "district": "Centro",
            "zip_code": "01001-000",
            "city": "São Paulo",
            "state": "SP",
        },
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def profile(client: TestClient) -> dict[str, Any]:
    return make_profile(client)
