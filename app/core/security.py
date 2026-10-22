"""Autenticação por chave de API e autorização por papel.

Implementação mínima: chaves configuradas em ``IB_API_KEYS``. Em produção, substitua por
um provedor de identidade (OIDC) mantendo a mesma interface ``Principal``.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from app.core.config import ApiKey

ROLE_LEVEL = {"reader": 1, "operator": 2, "admin": 3}


@dataclass(frozen=True, slots=True)
class Principal:
    actor: str
    role: str

    def has_role(self, minimum: str) -> bool:
        return ROLE_LEVEL[self.role] >= ROLE_LEVEL[minimum]


def authenticate(presented: str | None, keys: list[ApiKey]) -> Principal | None:
    if not presented:
        return None
    match: Principal | None = None
    # Compara todas as chaves para não vazar tempo de resposta.
    for key in keys:
        if hmac.compare_digest(presented.encode(), key.key.encode()):
            match = Principal(actor=key.actor, role=key.role)
    return match
