"""Importação e (re)processamento de arquivos de retorno."""

from __future__ import annotations

import hashlib
import logging
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application import audit
from app.application.reconciliation_service import apply_detail
from app.cnab.base import BankLayoutAdapter, ReturnDetail
from app.cnab.registry import detect_return_layout, get_adapter
from app.domain.enums import AttemptStatus, FileDirection, FileStatus
from app.domain.errors import ConflictError
from app.infrastructure.database.base import utcnow
from app.infrastructure.database.models import (
    BankFile,
    BankOccurrence,
    FileProcessingAttempt,
)
from app.infrastructure.repositories import get_or_404
from app.infrastructure.storage.local import LocalFileStorage

log = logging.getLogger(__name__)


def occurrence_key(adapter: BankLayoutAdapter, detail: ReturnDetail) -> str:
    """Chave de negócio: conteúdo do registro sem o número sequencial (395-400).

    O mesmo evento reenviado em outro arquivo (com outra sequência) gera a mesma chave.
    """
    payload = f"{adapter.layout_id}|{detail.raw_line[:394]}"
    return hashlib.sha256(payload.encode("latin-1")).hexdigest()


def import_return(
    session: Session,
    storage: LocalFileStorage,
    content: bytes,
    filename: str,
    actor: str,
    layout_id: str | None = None,
) -> BankFile:
    sha = hashlib.sha256(content).hexdigest()
    existing = session.scalars(select(BankFile).where(BankFile.dedup_key == f"RET:{sha}")).first()
    if existing is not None:
        raise ConflictError("Arquivo de retorno já importado", file_id=existing.id)
    adapter = get_adapter(layout_id) if layout_id else detect_return_layout(content)
    key = storage.key_for(FileDirection.RETURN.value, sha)
    storage.put(key, content)
    bank_file = BankFile(
        direction=FileDirection.RETURN.value,
        layout_id=adapter.layout_id,
        manual_version=adapter.manual_version,
        filename=filename[:255] or "retorno.ret",
        sha256=sha,
        dedup_key=f"RET:{sha}",
        size=len(content),
        storage_key=key,
        status=FileStatus.RECEIVED.value,
        created_by=actor,
    )
    session.add(bank_file)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Arquivo de retorno já importado (concorrência)") from exc
    audit.record(session, actor, "return.upload", "bank_file", bank_file.id, {"sha256": sha})
    session.commit()  # o arquivo original fica registrado mesmo que o processamento falhe
    process(session, storage, bank_file.id, actor, content=content)
    return bank_file


def process(
    session: Session,
    storage: LocalFileStorage,
    file_id: int,
    actor: str,
    content: bytes | None = None,
) -> FileProcessingAttempt:
    bank_file = get_or_404(session, BankFile, file_id, "Arquivo")
    if bank_file.direction != FileDirection.RETURN.value:
        raise ConflictError("Somente arquivos de retorno podem ser processados")
    if content is None:
        content = storage.get(bank_file.storage_key, bank_file.sha256)
    adapter = get_adapter(bank_file.layout_id)
    attempt = FileProcessingAttempt(
        bank_file_id=bank_file.id, status=AttemptStatus.RUNNING.value, actor=actor
    )
    session.add(attempt)
    session.commit()

    parsed = adapter.parse_return(content)
    bank_file.validation_report = parsed.report.as_dict()
    bank_file.header_info = _jsonable(parsed.header | {"trailer": parsed.trailer})
    if not parsed.report.is_valid:
        bank_file.status = FileStatus.INVALID.value
        attempt.status = AttemptStatus.FAILED.value
        attempt.error = "Arquivo rejeitado na validação estrutural"
        attempt.finished_at = utcnow()
        attempt.summary = {"errors": len(parsed.report.errors)}
        session.commit()
        return attempt

    counts: Counter[str] = Counter()
    by_code: Counter[str] = Counter()
    duplicates: list[int] = []
    failures: list[dict[str, Any]] = []
    for detail in parsed.details:
        key = occurrence_key(adapter, detail)
        if session.scalars(
            select(BankOccurrence.id).where(BankOccurrence.idempotency_key == key)
        ).first():
            duplicates.append(detail.line_number)
            continue
        savepoint = session.begin_nested()
        try:
            occurrence = apply_detail(session, adapter, bank_file.id, detail, key, actor)
            savepoint.commit()
        except IntegrityError:
            savepoint.rollback()
            duplicates.append(detail.line_number)  # gravada por processamento concorrente
            continue
        except Exception as exc:  # falha isolada na linha; demais linhas seguem
            savepoint.rollback()
            log.exception(
                "Falha ao processar linha", extra={"file_id": file_id, "line": detail.line_number}
            )
            failures.append(
                {"line": detail.line_number, "error": type(exc).__name__, "message": str(exc)[:500]}
            )
            continue
        counts[occurrence.processing_status] += 1
        by_code[detail.occurrence_code] += 1

    attempt.summary = {
        "details": len(parsed.details),
        "by_status": dict(counts),
        "by_code": dict(by_code),
        "duplicates": duplicates,
        "failures": failures,
        "warnings": len(parsed.report.warnings),
    }
    attempt.status = (AttemptStatus.PARTIAL if failures else AttemptStatus.SUCCEEDED).value
    attempt.finished_at = utcnow()
    bank_file.status = (FileStatus.PARTIALLY_PROCESSED if failures else FileStatus.PROCESSED).value
    audit.record(
        session,
        actor,
        "return.process",
        "bank_file",
        bank_file.id,
        {"attempt_id": attempt.id, "status": attempt.status},
    )
    session.commit()
    return attempt


def build_report(session: Session, file_id: int) -> dict[str, Any]:
    bank_file = get_or_404(session, BankFile, file_id, "Arquivo")
    occurrences = list(
        session.scalars(
            select(BankOccurrence)
            .where(BankOccurrence.bank_file_id == file_id)
            .order_by(BankOccurrence.line_number)
        )
    )
    status_counts = Counter(o.processing_status for o in occurrences)
    return {
        "file_id": bank_file.id,
        "filename": bank_file.filename,
        "status": bank_file.status,
        "layout_id": bank_file.layout_id,
        "manual_version": bank_file.manual_version,
        "validation": bank_file.validation_report,
        "header": bank_file.header_info,
        "occurrences_by_status": dict(status_counts),
        "attention": [
            {
                "occurrence_id": o.id,
                "line": o.line_number,
                "code": o.occurrence_code,
                "status": o.processing_status,
                "title_id": o.title_id,
                "message": o.message,
            }
            for o in occurrences
            if o.processing_status not in ("APPLIED", "INFORMATIONAL")
        ],
        "attempts": [
            {
                "id": a.id,
                "status": a.status,
                "started_at": a.started_at,
                "finished_at": a.finished_at,
                "summary": a.summary,
                "error": a.error,
            }
            for a in bank_file.attempts
        ],
    }


def _jsonable(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            out[key] = _jsonable(value)
        elif value is None or isinstance(value, (str, int, float, bool)):
            out[key] = value
        else:
            out[key] = str(value)
    return out
