"""Registro de adaptadores banco/leiaute. Novos bancos entram aqui sem mudar o domínio."""

from __future__ import annotations

from app.cnab.base import BankLayoutAdapter
from app.cnab.layouts.itau.cnab400.adapter import ItauCnab400Adapter
from app.domain.errors import ConflictError, NotFoundError

_ADAPTERS: dict[str, BankLayoutAdapter] = {}


def register(adapter: BankLayoutAdapter) -> None:
    if adapter.layout_id in _ADAPTERS:
        raise ValueError(f"Adaptador já registrado: {adapter.layout_id}")
    _ADAPTERS[adapter.layout_id] = adapter


def get_adapter(layout_id: str) -> BankLayoutAdapter:
    try:
        return _ADAPTERS[layout_id]
    except KeyError as exc:
        raise NotFoundError(f"Leiaute não suportado: {layout_id}") from exc


def available_layouts() -> list[str]:
    return sorted(_ADAPTERS)


def detect_return_layout(content: bytes) -> BankLayoutAdapter:
    """Identifica o adaptador pelo conteúdo. Ambiguidade é erro, nunca escolha silenciosa."""
    matches = [a for a in _ADAPTERS.values() if a.looks_like_return(content)]
    if not matches:
        raise NotFoundError("Nenhum leiaute de retorno reconhece este arquivo")
    if len(matches) > 1:
        raise ConflictError(
            "Mais de um leiaute reconhece o arquivo; informe o parâmetro layout",
            layouts=[a.layout_id for a in matches],
        )
    return matches[0]


register(ItauCnab400Adapter())
