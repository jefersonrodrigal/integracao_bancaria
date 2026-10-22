from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Dialect, MetaData, Numeric, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

CENT = Decimal("0.01")


def utcnow() -> datetime:
    return datetime.now(UTC)


class Money(TypeDecorator[Decimal]):
    """Valor monetário exato em NUMERIC(15,2).

    Valores com mais de 2 casas são rejeitados (nunca arredondados silenciosamente).
    """

    impl = Numeric(15, 2, asdecimal=True)
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        number = Decimal(value)
        if number != number.quantize(CENT):
            raise ValueError(f"Valor monetário com mais de 2 casas decimais: {value}")
        return number.quantize(CENT)

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        return Decimal(value).quantize(CENT)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
