from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.infrastructure.database.models import AuditEvent


def record(
    session: Session,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: object,
    data: dict[str, Any] | None = None,
) -> None:
    """Registra evento de auditoria. Não inclua documentos pessoais em ``data``."""
    session.add(
        AuditEvent(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            data=data,
        )
    )
