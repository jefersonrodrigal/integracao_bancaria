from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any


class DomainError(Exception):
    """Erro de regra de negócio."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.context = context


class InvalidStateTransition(DomainError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Transição de status não permitida: {current} -> {target}")
        self.current = current
        self.target = target


@dataclass(frozen=True, slots=True)
class Issue:
    """Problema de validação. ``reference`` aponta para a regra (manual ou regra interna)."""

    code: str
    message: str
    severity: str = "error"
    field: str | None = None
    line: int | None = None
    reference: str | None = None
    context: dict[str, Any] = dc_field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        for key in ("field", "line", "reference"):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        if self.context:
            data["context"] = self.context
        return data


class ValidationFailed(DomainError):
    def __init__(self, issues: list[Issue], message: str = "Falha de validação") -> None:
        super().__init__(message)
        self.issues = issues
