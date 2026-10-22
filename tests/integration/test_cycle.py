"""Ciclo completo pela API: título -> remessa -> retorno -> conciliação (dados sintéticos)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.cnab.layouts.itau.cnab400.adapter import ItauCnab400Adapter
from tests.conftest import OPERATOR_KEY, READER_KEY, make_profile, title_payload
from tests.fixtures.builders import Detail, return_file

API = "/api/v1"
adapter = ItauCnab400Adapter()


def create_title(client: TestClient, profile_id: int, **overrides: Any) -> dict[str, Any]:
    response = client.post(f"{API}/titles", json=title_payload(profile_id, **overrides))
    assert response.status_code == 201, response.text
    return dict(response.json())


def remit(client: TestClient, profile_id: int, *items: dict[str, Any]) -> dict[str, Any]:
    response = client.post(
        f"{API}/remittances", json={"profile_id": profile_id, "items": list(items)}
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["remittance"])


def upload(client: TestClient, content: bytes, name: str = "ret.ret") -> Any:
    return client.post(f"{API}/returns", files={"file": (name, content, "text/plain")})


def title(client: TestClient, title_id: int) -> dict[str, Any]:
    return dict(client.get(f"{API}/titles/{title_id}").json())


def test_full_cycle_direct_wallet(client: TestClient, profile: dict[str, Any]) -> None:
    t = create_title(client, profile["id"])
    assert t["status"] == "OPEN" and t["nosso_numero"] == "00000001"
    assert t["nosso_numero_dac"] == adapter.nosso_numero_dac("0057", "12345", "109", "00000001")

    batch = remit(client, profile["id"], {"title_id": t["id"]})
    assert batch["record_count"] == 3 and batch["items"][0]["occurrence_code"] == "01"
    assert title(client, t["id"])["status"] == "REMITTANCE_GENERATED"

    download = client.get(f"{API}/remittances/{batch['id']}/download")
    assert download.status_code == 200 and len(download.content) == 3 * 402
    assert "attachment" in download.headers["content-disposition"]
    check = client.post(
        f"{API}/remittances/validate", files={"file": ("r.rem", download.content, "text/plain")}
    )
    assert check.json()["valid"] is True

    assert client.post(f"{API}/remittances/{batch['id']}/mark-sent").status_code == 200
    assert title(client, t["id"])["status"] == "SENT_TO_BANK"

    confirm = upload(
        client,
        return_file([Detail("02", reference=t["company_reference"], nn_dac=t["nosso_numero_dac"])]),
    )
    assert confirm.status_code == 201, confirm.text
    assert confirm.json()["status"] == "PROCESSED"
    assert title(client, t["id"])["status"] == "REGISTERED"

    paid = upload(
        client,
        return_file(
            [
                Detail(
                    "06",
                    nn_dac=t["nosso_numero_dac"],
                    principal=12345,
                    fee=180,
                    credit_date="241026",
                    liquidation="B1",
                )
            ],
            file_seq=2,
        ),
    )
    assert paid.status_code == 201
    final = title(client, t["id"])
    assert final["status"] == "PAID" and final["paid_amount"] == "123.45"
    assert final["credit_date"] == "2026-10-24"

    movements = client.get(f"{API}/movements", params={"title_id": t["id"]}).json()
    assert sorted((m["kind"], m["amount"]) for m in movements) == [
        ("FEE", "-1.80"),
        ("SETTLEMENT", "123.45"),
    ]
    rec = client.get(f"{API}/reconciliation", params={"title_id": t["id"]}).json()
    assert [r["status"] for r in rec] == ["MATCHED"]

    report = client.get(f"{API}/returns/{paid.json()['id']}/report").json()
    assert report["occurrences_by_status"] == {"APPLIED": 1}


def test_reimport_and_redelivered_occurrence_do_not_duplicate_money(
    client: TestClient, profile: dict[str, Any]
) -> None:
    t = create_title(client, profile["id"])
    remit(client, profile["id"], {"title_id": t["id"]})
    settle = Detail("06", reference=t["company_reference"], principal=12345)
    content = return_file([Detail("02", reference=t["company_reference"]), settle])
    assert upload(client, content).status_code == 201

    again = upload(client, content)
    assert again.status_code == 409 and "file_id" in again.json()["context"]

    # Mesmo evento em outro arquivo (outra sequência/cabeçalho): ignorado por idempotência.
    other = upload(client, return_file([Detail("09", nosso_numero="99999999"), settle], file_seq=7))
    assert other.status_code == 201
    summary = other.json()["attempts"][-1]["summary"]
    assert summary["duplicates"] == [3]
    movements = client.get(f"{API}/movements", params={"title_id": t["id"]}).json()
    assert [m["kind"] for m in movements] == ["SETTLEMENT"]


def test_escritural_wallet_bank_assigns_nosso_numero_and_write_off(client: TestClient) -> None:
    profile = make_profile(client, wallet="112")
    t = create_title(
        client,
        profile["id"],
        send_boleto_by_email=True,
        payer={**title_payload(0)["payer"], "email": "pagador@example.com"},
    )
    assert t["nosso_numero"] is None
    batch = remit(client, profile["id"], {"title_id": t["id"]})
    content = client.get(f"{API}/remittances/{batch['id']}/download").content
    lines = content.decode().split("\r\n")
    assert lines[1][62:70] == "00000000" and lines[2][0] == "5"
    assert "pagador@example.com" in lines[2]

    ret = return_file(
        [Detail("02", wallet="112", nosso_numero="55500001", reference=t["company_reference"])]
    )
    assert upload(client, ret).status_code == 201
    registered = title(client, t["id"])
    assert registered["status"] == "REGISTERED" and registered["nosso_numero"] == "55500001"

    wo = remit(client, profile["id"], {"title_id": t["id"], "command": "WRITE_OFF"})
    assert wo["items"][0]["occurrence_code"] == "02"
    assert title(client, t["id"])["status"] == "CANCEL_REQUESTED"
    rejected = return_file(
        [Detail("15", wallet="112", nosso_numero="55500001", messages="05      ")], file_seq=2
    )
    assert upload(client, rejected).status_code == 201
    back = title(client, t["id"])
    assert back["status"] == "REGISTERED"
    assert back["last_bank_message"][0]["table"] == "Tabela 4"

    remit(client, profile["id"], {"title_id": t["id"], "command": "WRITE_OFF"})
    done = return_file([Detail("09", wallet="112", nosso_numero="55500001")], file_seq=3)
    assert upload(client, done).status_code == 201
    assert title(client, t["id"])["status"] == "CANCELLED"


def test_rejected_entry_can_be_corrected(client: TestClient, profile: dict[str, Any]) -> None:
    t = create_title(client, profile["id"])
    remit(client, profile["id"], {"title_id": t["id"]})
    upload(
        client, return_file([Detail("03", reference=t["company_reference"], messages="1011    ")])
    )
    rejected = title(client, t["id"])
    assert rejected["status"] == "REJECTED"
    assert [m["code"] for m in rejected["last_bank_message"]] == ["10", "11"]
    patched = client.patch(
        f"{API}/titles/{t['id']}",
        json={"payer": {**title_payload(0)["payer"], "zip_code": "01310100"}},
    )
    assert patched.status_code == 200 and patched.json()["status"] == "OPEN"
    assert patched.json()["last_bank_message"] is None


def test_due_date_change(client: TestClient, profile: dict[str, Any]) -> None:
    t = create_title(client, profile["id"], due_date="2099-01-10")
    remit(client, profile["id"], {"title_id": t["id"]})
    upload(client, return_file([Detail("02", reference=t["company_reference"])]))
    batch = remit(
        client,
        profile["id"],
        {"title_id": t["id"], "command": "CHANGE_DUE_DATE", "new_due_date": "2099-02-10"},
    )
    line = client.get(f"{API}/remittances/{batch['id']}/download").content.decode().split("\r\n")[1]
    assert line[108:110] == "06" and line[120:126] == "100299"
    assert title(client, t["id"])["due_date"] == "2099-01-10"  # só muda com a confirmação
    upload(client, return_file([Detail("14", due="100299")], file_seq=2))
    assert title(client, t["id"])["due_date"] == "2099-02-10"


def test_discard_restores_status(client: TestClient, profile: dict[str, Any]) -> None:
    t = create_title(client, profile["id"])
    batch = remit(client, profile["id"], {"title_id": t["id"]})
    discarded = client.post(f"{API}/remittances/{batch['id']}/discard")
    assert discarded.json()["status"] == "DISCARDED"
    assert title(client, t["id"])["status"] == "OPEN"
    assert client.post(f"{API}/remittances/{batch['id']}/mark-sent").status_code == 409


def test_invalid_remittance_requests(client: TestClient, profile: dict[str, Any]) -> None:
    t = create_title(client, profile["id"])
    response = client.post(
        f"{API}/remittances",
        json={
            "profile_id": profile["id"],
            "items": [{"title_id": t["id"], "command": "WRITE_OFF"}],
        },
    )
    assert response.status_code == 422
    assert response.json()["issues"][0]["code"] == "INVALID_STATUS"
    dup = client.post(
        f"{API}/remittances",
        json={"profile_id": profile["id"], "items": [{"title_id": t["id"]}, {"title_id": t["id"]}]},
    )
    assert dup.status_code == 422


def test_title_validation_errors_reference_manual(
    client: TestClient, profile: dict[str, Any]
) -> None:
    response = client.post(
        f"{API}/titles",
        json=title_payload(
            profile["id"], species="10", instruction1="93", discount_amount="200.00"
        ),
    )
    assert response.status_code == 422
    issues = {i["code"]: i for i in response.json()["issues"]}
    assert {"SPECIES", "INSTRUCTION_UNSUPPORTED", "DISCOUNT_MAX"} <= issues.keys()
    assert issues["SPECIES"]["reference"].startswith("Nota 10")
    assert (
        client.post(f"{API}/titles", json=title_payload(profile["id"], amount="1.005")).status_code
        == 422
    )


def test_nosso_numero_conflict(client: TestClient, profile: dict[str, Any]) -> None:
    create_title(client, profile["id"], nosso_numero="500")
    response = client.post(f"{API}/titles", json=title_payload(profile["id"], nosso_numero="500"))
    assert response.status_code == 409


def test_authorization(client: TestClient) -> None:
    assert client.get(f"{API}/titles", headers={"X-API-Key": ""}).status_code == 401
    assert (
        client.get(f"{API}/titles", headers={"X-API-Key": "wrong-key-0000000000"}).status_code
        == 401
    )
    reader = {"X-API-Key": READER_KEY}
    assert client.get(f"{API}/titles", headers=reader).status_code == 200
    assert client.post(f"{API}/titles", headers=reader, json={}).status_code == 403
    operator = {"X-API-Key": OPERATOR_KEY}
    assert (
        client.post(f"{API}/banks", headers=operator, json={"code": "341", "name": "X"}).status_code
        == 403
    )


def test_health_and_ready(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready")
    assert ready.status_code == 200 and ready.json()["checks"]["database"] == "ok"
