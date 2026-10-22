"""Geração, envio e descarte de remessas."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import audit
from app.application.mappers import item_data, profile_data
from app.application.schemas import RemittanceCreate
from app.cnab.base import ValidationReport
from app.cnab.registry import get_adapter
from app.domain.enums import (
    BatchStatus,
    FileDirection,
    FileStatus,
    RemittanceCommand,
    TitleStatus,
)
from app.domain.errors import ConflictError, Issue, ValidationFailed
from app.domain.services.title_state import ensure_transition
from app.infrastructure.database.base import utcnow
from app.infrastructure.database.models import (
    BankFile,
    BankIntegrationProfile,
    ReceivableTitle,
    RemittanceBatch,
    RemittanceBatchItem,
)
from app.infrastructure.repositories import get_or_404
from app.infrastructure.storage.local import LocalFileStorage

# Status exigido e status resultante por comando (regra interna).
_COMMAND_RULES: dict[RemittanceCommand, tuple[TitleStatus, TitleStatus]] = {
    RemittanceCommand.REGISTER: (TitleStatus.OPEN, TitleStatus.REMITTANCE_GENERATED),
    RemittanceCommand.WRITE_OFF: (TitleStatus.REGISTERED, TitleStatus.CANCEL_REQUESTED),
    RemittanceCommand.CHANGE_DUE_DATE: (TitleStatus.REGISTERED, TitleStatus.REGISTERED),
}
_OCCURRENCE_CODES = {
    RemittanceCommand.REGISTER: "01",
    RemittanceCommand.WRITE_OFF: "02",
    RemittanceCommand.CHANGE_DUE_DATE: "06",
}


def generate(
    session: Session,
    storage: LocalFileStorage,
    data: RemittanceCreate,
    actor: str,
    today: date | None = None,
) -> tuple[RemittanceBatch, ValidationReport]:
    today = today or date.today()
    profile = get_or_404(session, BankIntegrationProfile, data.profile_id, "Perfil")
    if not profile.active:
        raise ConflictError("Perfil inativo")
    adapter = get_adapter(profile.layout_id)
    ids = [item.title_id for item in data.items]
    if len(set(ids)) != len(ids):
        raise ValidationFailed([Issue("DUPLICATED_TITLE", "Título repetido na requisição")])
    titles = {
        t.id: t
        for t in session.scalars(
            select(ReceivableTitle).where(ReceivableTitle.id.in_(ids)).with_for_update()
        )
    }
    issues: list[Issue] = []
    items = []
    for request in data.items:
        title = titles.get(request.title_id)
        ctx = {"title_id": request.title_id}
        if title is None:
            issues.append(Issue("NOT_FOUND", "Título não encontrado", context=ctx))
            continue
        if title.profile_id != profile.id:
            issues.append(Issue("PROFILE_MISMATCH", "Título pertence a outro perfil", context=ctx))
            continue
        required, _ = _COMMAND_RULES[request.command]
        if title.status != required.value:
            issues.append(
                Issue(
                    "INVALID_STATUS",
                    f"{request.command} exige status {required}; atual {title.status}",
                    context=ctx,
                )
            )
            continue
        if request.command is RemittanceCommand.CHANGE_DUE_DATE:
            if request.new_due_date is None or request.new_due_date == title.due_date:
                issues.append(
                    Issue(
                        "NEW_DUE_DATE",
                        "Informe nova data diferente da atual",
                        field="new_due_date",
                        reference="Tabela 2 cód. 05",
                        context=ctx,
                    )
                )
                continue
            if request.new_due_date < today:
                issues.append(
                    Issue(
                        "NEW_DUE_DATE",
                        "Nova data não pode tornar o título vencido",
                        field="new_due_date",
                        reference="Tabela 3 cód. 33",
                        context=ctx,
                    )
                )
                continue
        elif request.new_due_date is not None:
            issues.append(
                Issue(
                    "NEW_DUE_DATE",
                    "new_due_date só se aplica a CHANGE_DUE_DATE",
                    field="new_due_date",
                    context=ctx,
                )
            )
            continue
        items.append(
            (
                title,
                request,
                item_data(title, title.customer, request.command, request.new_due_date),
            )
        )
    if issues:
        raise ValidationFailed(issues, "Remessa não pode ser gerada")

    generated = adapter.generate_remittance(profile_data(profile), [i for *_, i in items], today)
    report = adapter.validate_remittance(generated.content)
    if not report.is_valid:
        # Defeito do gerador: nunca disponibilizar arquivo que não passa na própria validação.
        raise ValidationFailed(report.errors, "Arquivo gerado não passou na validação")
    report.issues.extend(generated.warnings)

    sha = hashlib.sha256(generated.content).hexdigest()
    key = storage.key_for(FileDirection.REMITTANCE.value, sha)
    storage.put(key, generated.content)
    bank_file = BankFile(
        direction=FileDirection.REMITTANCE.value,
        layout_id=adapter.layout_id,
        manual_version=adapter.manual_version,
        profile_id=profile.id,
        filename="pending",
        sha256=sha,
        size=len(generated.content),
        storage_key=key,
        status=FileStatus.GENERATED.value,
        validation_report=report.as_dict(),
        created_by=actor,
    )
    session.add(bank_file)
    session.flush()
    bank_file.filename = f"CB{today:%d%m%y}_{profile.wallet}_{bank_file.id:06d}.REM"
    total = sum(
        (t.amount for t, r, _ in items if r.command is RemittanceCommand.REGISTER), Decimal("0.00")
    )
    batch = RemittanceBatch(
        profile_id=profile.id,
        bank_file_id=bank_file.id,
        status=BatchStatus.GENERATED.value,
        record_count=generated.record_count,
        title_count=len(items),
        total_amount=total,
        created_by=actor,
    )
    session.add(batch)
    session.flush()
    for title, request, item in items:
        _, target = _COMMAND_RULES[request.command]
        previous = TitleStatus(title.status)
        if target is not previous:
            ensure_transition(previous, target)
            title.status = target.value
        session.add(
            RemittanceBatchItem(
                batch_id=batch.id,
                title_id=title.id,
                command=request.command.value,
                occurrence_code=_OCCURRENCE_CODES[request.command],
                line_number=generated.line_numbers[f"{item.company_reference}:{item.command}"],
                previous_status=previous.value,
                new_status=target.value,
                new_due_date=request.new_due_date,
            )
        )
    session.flush()
    audit.record(
        session,
        actor,
        "remittance.generate",
        "remittance",
        batch.id,
        {"file_id": bank_file.id, "sha256": sha, "titles": len(items)},
    )
    return batch, report


def mark_sent(session: Session, batch_id: int, actor: str) -> RemittanceBatch:
    batch = get_or_404(session, RemittanceBatch, batch_id, "Remessa")
    if batch.status != BatchStatus.GENERATED.value:
        raise ConflictError(f"Remessa em {batch.status} não pode ser marcada como enviada")
    batch.status = BatchStatus.SENT.value
    batch.sent_at = utcnow()
    for item in batch.items:
        title = session.get(ReceivableTitle, item.title_id)
        if title is not None and title.status == TitleStatus.REMITTANCE_GENERATED.value:
            title.status = TitleStatus.SENT_TO_BANK.value
    audit.record(session, actor, "remittance.mark_sent", "remittance", batch.id)
    session.flush()
    return batch


def discard(session: Session, batch_id: int, actor: str) -> RemittanceBatch:
    """Descarta remessa ainda não enviada, devolvendo os títulos ao status anterior."""
    batch = get_or_404(session, RemittanceBatch, batch_id, "Remessa")
    if batch.status != BatchStatus.GENERATED.value:
        raise ConflictError(f"Remessa em {batch.status} não pode ser descartada")
    reverted = []
    for item in batch.items:
        title = session.get(ReceivableTitle, item.title_id)
        if title is not None and title.status == item.new_status != item.previous_status:
            ensure_transition(TitleStatus(title.status), TitleStatus(item.previous_status))
            title.status = item.previous_status
            reverted.append(title.id)
    batch.status = BatchStatus.DISCARDED.value
    audit.record(
        session, actor, "remittance.discard", "remittance", batch.id, {"reverted_titles": reverted}
    )
    session.flush()
    return batch


def download(
    session: Session, storage: LocalFileStorage, batch_id: int, actor: str
) -> tuple[str, bytes]:
    batch = get_or_404(session, RemittanceBatch, batch_id, "Remessa")
    bank_file = batch.bank_file
    content = storage.get(bank_file.storage_key, bank_file.sha256)
    audit.record(session, actor, "remittance.download", "remittance", batch.id)
    return bank_file.filename, content
