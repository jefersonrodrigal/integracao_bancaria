"""Aplicação FastAPI. Execute com: ``uvicorn app.main:app``."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.errors import install_error_handlers
from app.api.routes import occurrences, ops, remittances, returns, setup, titles
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.infrastructure.database.session import build_engine, build_session_factory
from app.infrastructure.storage.local import LocalFileStorage

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Financeiro - Integração Bancária — Cobrança",
        version="0.1.0",
        description=(
            "Cobrança registrada. Adaptador disponível: Itaú CNAB 400 (manual JANEIRO 2017). "
            "Autenticação: cabeçalho X-API-Key."
        ),
    )
    engine = build_engine(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.state.storage = LocalFileStorage(settings.storage_dir)
    app.state.api_keys = settings.parsed_api_keys()
    install_error_handlers(app)
    app.include_router(ops.router)
    for router in (
        setup.router,
        titles.router,
        remittances.router,
        returns.router,
        occurrences.occurrences,
        occurrences.reconciliation,
        occurrences.movements,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
