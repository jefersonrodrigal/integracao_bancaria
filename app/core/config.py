"""Configuração da aplicação, lida de variáveis de ambiente com prefixo ``IB_``."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True, slots=True)
class ApiKey:
    actor: str
    role: str
    key: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="IB_", extra="ignore")

    environment: str = "development"
    database_url: str
    storage_dir: Path = Path("./data/files")
    max_upload_bytes: int = 5 * 1024 * 1024
    log_level: str = "INFO"
    # Formato: "ator:papel:chave,ator:papel:chave". Papéis: reader, operator, admin.
    api_keys: str = ""

    @field_validator("database_url")
    @classmethod
    def _postgresql_only(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("IB_DATABASE_URL deve apontar para PostgreSQL (postgresql+psycopg://)")
        return value

    def parsed_api_keys(self) -> list[ApiKey]:
        keys: list[ApiKey] = []
        for chunk in self.api_keys.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = chunk.split(":", 2)
            if len(parts) != 3 or not all(parts):
                raise ValueError("IB_API_KEYS deve seguir o formato ator:papel:chave")
            actor, role, key = parts
            if role not in {"reader", "operator", "admin"}:
                raise ValueError(f"Papel inválido em IB_API_KEYS: {role}")
            if len(key) < 16:
                raise ValueError(f"A chave do ator {actor} deve ter ao menos 16 caracteres")
            keys.append(ApiKey(actor=actor, role=role, key=key))
        return keys


@lru_cache
def get_settings() -> Settings:
    return Settings()
