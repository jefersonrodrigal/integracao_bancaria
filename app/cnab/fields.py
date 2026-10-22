"""Campos e registros posicionais genéricos (núcleo reutilizável entre leiautes).

Convenções de formatação seguidas por padrão (Itaú CNAB 400, seção 2.2, p.5 — também
usuais no padrão FEBRABAN):

* Alfanumérico ``X``: alinhado à esquerda, completado com brancos, maiúsculo, sem acentos.
* Numérico ``9``: alinhado à direita, completado com zeros; não utilizado = zeros.
* Vírgula assumida ``V``: ``9(5)V9(2)`` com 876,54 vira ``0087654``.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any


class FieldType(StrEnum):
    NUMERIC = "9"
    ALPHA = "X"
    DATE_DDMMYY = "DDMMAA"
    DATE_DDMMYYYY = "DDMMAAAA"


class FieldFormatError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


# Caracteres aceitos em campos alfanuméricos após remoção de acentos.
# O manual "aconselha a não utilização de caracteres especiais" (p.5); mantemos um conjunto
# conservador de pontuação comum em endereços e e-mails.
ALLOWED_ALPHA = frozenset(
    " ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:-/()&@_+'#"
)


def normalize_text(value: str, *, uppercase: bool = True) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    stripped = " ".join(stripped.split())
    return stripped.upper() if uppercase else stripped


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    start: int
    end: int
    type: FieldType
    decimals: int = 0
    constant: str | None = None
    truncate: bool = False
    uppercase: bool = True
    reference: str = ""
    description: str = ""

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    @property
    def picture(self) -> str:
        if self.type is FieldType.NUMERIC and self.decimals:
            return f"9({self.length - self.decimals:02d})V9({self.decimals})"
        if self.type is FieldType.NUMERIC:
            return f"9({self.length:02d})"
        if self.type is FieldType.ALPHA:
            return f"X({self.length:02d})"
        return self.type.value

    def blank(self) -> str:
        return " " * self.length if self.type is FieldType.ALPHA else "0" * self.length

    def format(self, value: object, warnings: list[str] | None = None) -> str:
        if self.constant is not None:
            if value is not None and str(value) != self.constant:
                raise FieldFormatError(self.name, f"valor fixo {self.constant!r} esperado")
            return self.constant
        if value is None:
            return self.blank()
        if self.type is FieldType.NUMERIC:
            return self._format_numeric(value)
        if self.type is FieldType.ALPHA:
            return self._format_alpha(value, warnings)
        if not isinstance(value, date):
            raise FieldFormatError(self.name, "data esperada")
        if not 2000 <= value.year <= 2099:
            raise FieldFormatError(self.name, "ano fora do intervalo 2000-2099")
        return value.strftime("%d%m%y" if self.type is FieldType.DATE_DDMMYY else "%d%m%Y")

    def _format_numeric(self, value: object) -> str:
        if self.decimals:
            if not isinstance(value, (Decimal, int)) or isinstance(value, bool):
                raise FieldFormatError(self.name, "valor decimal esperado")
            number = Decimal(value)
            if number < 0:
                raise FieldFormatError(self.name, "valor negativo não é permitido")
            scaled = number.scaleb(self.decimals)
            if scaled != scaled.to_integral_value():
                raise FieldFormatError(
                    self.name, f"mais de {self.decimals} casas decimais não é permitido"
                )
            text = str(int(scaled))
        else:
            if isinstance(value, bool):
                raise FieldFormatError(self.name, "valor numérico esperado")
            if isinstance(value, int):
                if value < 0:
                    raise FieldFormatError(self.name, "valor negativo não é permitido")
                text = str(value)
            elif isinstance(value, str) and value.isdigit():
                text = value
            else:
                raise FieldFormatError(self.name, "somente dígitos são permitidos")
        if len(text) > self.length:
            raise FieldFormatError(self.name, f"excede {self.length} posições")
        return text.rjust(self.length, "0")

    def _format_alpha(self, value: object, warnings: list[str] | None) -> str:
        if not isinstance(value, str):
            raise FieldFormatError(self.name, "texto esperado")
        text = normalize_text(value, uppercase=self.uppercase)
        invalid = sorted({ch for ch in text if ch not in ALLOWED_ALPHA})
        if invalid:
            raise FieldFormatError(self.name, f"caracteres não permitidos: {''.join(invalid)!r}")
        if len(text) > self.length:
            if not self.truncate:
                raise FieldFormatError(self.name, f"excede {self.length} posições")
            if warnings is not None:
                warnings.append(f"{self.name}: truncado para {self.length} posições")
            text = text[: self.length]
        return text.ljust(self.length, " ")

    def parse(self, raw: str) -> object:
        if len(raw) != self.length:
            raise FieldFormatError(self.name, "tamanho inconsistente")
        if self.type is FieldType.ALPHA:
            return raw.rstrip(" ")
        if self.type is FieldType.NUMERIC:
            if not raw.isdigit():
                raise FieldFormatError(self.name, f"conteúdo não numérico: {raw!r}")
            if self.decimals:
                return Decimal(raw).scaleb(-self.decimals)
            return raw
        if raw.strip("0 ") == "":
            return None
        if not raw.isdigit():
            raise FieldFormatError(self.name, f"data não numérica: {raw!r}")
        try:
            if self.type is FieldType.DATE_DDMMYY:
                return date(2000 + int(raw[4:6]), int(raw[2:4]), int(raw[0:2]))
            return date(int(raw[4:8]), int(raw[2:4]), int(raw[0:2]))
        except ValueError as exc:
            raise FieldFormatError(self.name, f"data inválida: {raw!r}") from exc


@dataclass(frozen=True, slots=True)
class RecordLayout:
    name: str
    fields: tuple[Field, ...]
    length: int = 400
    reference: str = ""

    def __post_init__(self) -> None:
        expected = 1
        names: set[str] = set()
        for field in self.fields:
            if field.start != expected or field.end < field.start:
                raise ValueError(f"{self.name}.{field.name}: posição {field.start} != {expected}")
            if field.name in names:
                raise ValueError(f"{self.name}: campo duplicado {field.name}")
            if field.constant is not None and len(field.constant) != field.length:
                raise ValueError(f"{self.name}.{field.name}: constante com tamanho incorreto")
            names.add(field.name)
            expected = field.end + 1
        if expected != self.length + 1:
            raise ValueError(f"{self.name}: cobre {expected - 1} posições, esperado {self.length}")

    def field(self, name: str) -> Field:
        for field in self.fields:
            if field.name == name:
                return field
        raise KeyError(name)

    def render(self, values: Mapping[str, object], warnings: list[str] | None = None) -> str:
        unknown = set(values) - {f.name for f in self.fields}
        if unknown:
            raise KeyError(f"{self.name}: campos desconhecidos {sorted(unknown)}")
        line = "".join(f.format(values.get(f.name), warnings) for f in self.fields)
        assert len(line) == self.length
        return line

    def parse(self, line: str) -> tuple[dict[str, Any], list[FieldFormatError]]:
        values: dict[str, Any] = {}
        errors: list[FieldFormatError] = []
        for field in self.fields:
            raw = line[field.start - 1 : field.end]
            try:
                values[field.name] = field.parse(raw)
            except FieldFormatError as exc:
                values[field.name] = None
                errors.append(exc)
                continue
            if field.constant is not None and raw != field.constant:
                errors.append(FieldFormatError(field.name, f"esperado {field.constant!r}"))
        return values, errors
