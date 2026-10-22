"""Retornos com ocorrências desconhecidas, títulos inexistentes, falhas e divergências."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.application import reconciliation_service, return_service
from app.infrastructure.database.models import BankOccurrence, ReceivableTitle
from tests.fixtures.builders import Detail, return_file
from tests.integration.test_cycle import API, create_title, remit, title, upload


def det(t: dict[str, Any], code: str, **kwargs: Any) -> Detail:
    """Detalhe sintético apontando para o título ``t`` (uso da empresa + nosso número)."""
    return Detail(
        code,
        reference=t["company_reference"],
        nosso_numero=t["nosso_numero"] or "00000000",
        **kwargs,
    )


def registered_title(client: TestClient, profile: dict[str, Any]) -> dict[str, Any]:
    t = create_title(client, profile["id"])
    remit(client, profile["id"], {"title_id": t["id"]})
    upload(client, return_file([det(t, "02")], file_seq=900 + t["id"]))
    return t


def occurrences(client: TestClient, file_id: int) -> list[dict[str, Any]]:
    return list(client.get(f"{API}/occurrences", params={"file_id": file_id}).json())


def test_unknown_code_is_stored_without_effect(client: TestClient, profile: dict[str, Any]) -> None:
    t = registered_title(client, profile)
    response = upload(client, return_file([det(t, "01")]))
    occ = occurrences(client, response.json()["id"])
    assert occ[0]["processing_status"] == "UNKNOWN_CODE"
    assert occ[0]["raw_line"].startswith("1")
    assert title(client, t["id"])["status"] == "REGISTERED"


def test_title_not_found_is_unmatched(client: TestClient, profile: dict[str, Any]) -> None:
    response = upload(client, return_file([Detail("06", nosso_numero="99999999", principal=100)]))
    occ = occurrences(client, response.json()["id"])[0]
    assert occ["processing_status"] == "UNMATCHED" and occ["title_id"] is None
    rec = client.get(f"{API}/reconciliation", params={"status": "UNMATCHED"}).json()
    assert rec[0]["reasons"] == ["TITLE_NOT_FOUND"]
    assert client.get(f"{API}/movements").json() == []


def test_unknown_account_is_unmatched(client: TestClient, profile: dict[str, Any]) -> None:
    response = upload(client, return_file([Detail("06", wallet="112")]))
    occ = occurrences(client, response.json()["id"])[0]
    assert occ["processing_status"] == "UNMATCHED"
    assert "perfil" in occ["message"]


def test_invalid_line_does_not_change_title(client: TestClient, profile: dict[str, Any]) -> None:
    t = registered_title(client, profile)
    response = upload(
        client,
        return_file(
            [
                det(t, "06", amount_raw="0000000ABC345"),
            ]
        ),
    )
    assert response.json()["status"] == "PROCESSED"
    assert occurrences(client, response.json()["id"])[0]["processing_status"] == "INVALID"
    assert title(client, t["id"])["status"] == "REGISTERED"


def test_structurally_invalid_file_is_kept_but_not_processed(client: TestClient) -> None:
    lines = return_file([Detail("06")]).split(b"\r\n")
    lines[1] = lines[1][:399]
    response = upload(client, b"\r\n".join(lines))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "INVALID" and body["validation_report"]["valid"] is False
    assert occurrences(client, body["id"]) == []


def test_unrecognized_file_is_rejected(client: TestClient) -> None:
    assert upload(client, b"0" * 400).status_code == 404


def test_upload_limit(client: TestClient) -> None:
    assert upload(client, b"0" * 30_000).status_code == 413


def test_partial_failure_and_reprocess(
    client: TestClient, profile: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    t1, t2 = registered_title(client, profile), registered_title(client, profile)
    content = return_file(
        [
            det(t1, "06", principal=12345),
            det(t2, "06", principal=12345),
        ]
    )
    original = reconciliation_service.apply_detail

    def flaky(session: Any, adapter: Any, file_id: int, detail: Any, *args: Any) -> Any:
        if detail.company_reference == t2["company_reference"]:
            raise RuntimeError("falha simulada")
        return original(session, adapter, file_id, detail, *args)

    monkeypatch.setattr(return_service, "apply_detail", flaky)
    response = upload(client, content)
    body = response.json()
    assert body["status"] == "PARTIALLY_PROCESSED"
    assert body["attempts"][-1]["summary"]["failures"][0]["line"] == 3
    assert title(client, t1["id"])["status"] == "PAID"
    assert title(client, t2["id"])["status"] == "REGISTERED"

    monkeypatch.setattr(return_service, "apply_detail", original)
    attempt = client.post(f"{API}/returns/{body['id']}/reprocess").json()
    assert attempt["status"] == "SUCCEEDED"
    assert attempt["summary"]["duplicates"] == [2]
    assert title(client, t2["id"])["status"] == "PAID"
    assert client.get(f"{API}/returns/{body['id']}").json()["status"] == "PROCESSED"
    kinds = [m["kind"] for m in client.get(f"{API}/movements").json()]
    assert kinds == ["SETTLEMENT", "SETTLEMENT"]


def test_amount_divergence_requires_review_and_can_be_resolved(
    client: TestClient, profile: dict[str, Any]
) -> None:
    t = registered_title(client, profile)
    upload(client, return_file([det(t, "06", principal=10000)]))
    assert title(client, t["id"])["status"] == "PAID"
    rec = client.get(f"{API}/reconciliation", params={"title_id": t["id"]}).json()[0]
    assert rec["status"] == "DIVERGENT" and rec["reasons"] == ["NET_AMOUNT_MISMATCH"]
    assert rec["difference"] == "-23.45" and rec["resolved"] is False
    resolved = client.post(
        f"{API}/reconciliation/{rec['id']}/resolve",
        json={"note": "Pagamento a menor aceito pelo comercial"},
    )
    assert resolved.status_code == 200 and resolved.json()["resolved"] is True
    assert (
        client.post(
            f"{API}/reconciliation/{rec['id']}/resolve", json={"note": "de novo"}
        ).status_code
        == 409
    )


def test_discount_and_interest_are_considered(client: TestClient, profile: dict[str, Any]) -> None:
    t = registered_title(client, profile)
    upload(client, return_file([det(t, "06", discount=345, interest=100, principal=12100)]))
    rec = client.get(f"{API}/reconciliation", params={"title_id": t["id"]}).json()[0]
    assert rec["status"] == "MATCHED"


def test_second_distinct_settlement_is_flagged(client: TestClient, profile: dict[str, Any]) -> None:
    t = registered_title(client, profile)
    upload(client, return_file([det(t, "06", principal=12345)]))
    upload(client, return_file([det(t, "06", principal=12345, occurred="251026")], file_seq=5))
    rec = client.get(f"{API}/reconciliation", params={"title_id": t["id"]}).json()
    assert [r["reasons"] for r in rec] == [[], ["DUPLICATE_SETTLEMENT"]]
    assert len(client.get(f"{API}/movements", params={"title_id": t["id"]}).json()) == 2


def test_informational_settlement_creates_no_movement(
    client: TestClient, profile: dict[str, Any]
) -> None:
    t = registered_title(client, profile)
    upload(client, return_file([det(t, "06", principal=12345, fee=100, flag107="I")]))
    assert title(client, t["id"])["status"] == "REGISTERED"
    assert client.get(f"{API}/movements").json() == []


def test_review_required_code(client: TestClient, profile: dict[str, Any]) -> None:
    t = registered_title(client, profile)
    response = upload(client, return_file([det(t, "59")]))
    occ = occurrences(client, response.json()["id"])[0]
    assert occ["processing_status"] == "REVIEW_REQUIRED"
    assert title(client, t["id"])["status"] == "REGISTERED"


def test_fee_without_title(client: TestClient, profile: dict[str, Any]) -> None:
    response = upload(client, return_file([Detail("30", nosso_numero="00000000", fee=990)]))
    occ = occurrences(client, response.json()["id"])[0]
    assert occ["processing_status"] == "APPLIED"
    assert [m["amount"] for m in client.get(f"{API}/movements").json()] == ["-9.90"]
    assert client.get(f"{API}/reconciliation").json() == []


def test_occurrence_idempotency_constraint(
    app: FastAPI, client: TestClient, profile: dict[str, Any]
) -> None:
    """Garantia de banco contra corrida entre dois processamentos simultâneos."""
    response = upload(client, return_file([Detail("06", nosso_numero="99999999")]))
    with app.state.session_factory() as session:
        existing = session.query(BankOccurrence).one()
        session.add(
            BankOccurrence(
                bank_file_id=response.json()["id"],
                line_number=2,
                raw_line=existing.raw_line,
                idempotency_key=existing.idempotency_key,
                record_type="1",
                occurrence_code="06",
                processing_status="APPLIED",
                parsed={},
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_optimistic_lock_on_title(
    app: FastAPI, client: TestClient, profile: dict[str, Any]
) -> None:
    t = create_title(client, profile["id"])
    factory = app.state.session_factory
    with factory() as first, factory() as second:
        b = second.get(ReceivableTitle, t["id"])
        second.commit()  # encerra a transação de leitura; b mantém a versão lida
        a = first.get(ReceivableTitle, t["id"])
        assert a is not None and b is not None
        a.status = "REMITTANCE_GENERATED"
        first.commit()
        b.status = "REMITTANCE_GENERATED"
        with pytest.raises(StaleDataError):
            second.commit()
