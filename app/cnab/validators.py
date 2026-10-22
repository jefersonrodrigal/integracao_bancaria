"""Validações estruturais genéricas para arquivos posicionais de registro fixo."""

from __future__ import annotations

from dataclasses import dataclass

from app.cnab.base import ValidationReport

TERMINATORS = {"CRLF": b"\r\n", "LF": b"\n"}


@dataclass(frozen=True, slots=True)
class RawLine:
    number: int
    data: bytes


def split_records(content: bytes, report: ValidationReport, record_length: int) -> list[RawLine]:
    """Separa registros por linha, aceitando CRLF ou LF (sem misturar).

    Um terminador após o último registro é aceito; caractere EOF (0x1A) final é ignorado
    com aviso. Linhas vazias no meio do arquivo são erro.
    """
    if not content:
        report.error("EMPTY_FILE", "Arquivo vazio")
        return []
    if content.endswith(b"\x1a"):
        content = content[:-1]
        report.warning("EOF_CHAR", "Caractere de fim de arquivo (0x1A) ignorado")
    if b"\r\n" in content:
        if b"\n" in content.replace(b"\r\n", b"") or b"\r" in content.replace(b"\r\n", b""):
            report.error("MIXED_TERMINATORS", "Terminadores de linha misturados")
        chunks = content.split(b"\r\n")
    else:
        if b"\r" in content:
            report.error("INVALID_TERMINATOR", "Terminador CR isolado não é suportado")
        chunks = content.split(b"\n")
    if chunks and chunks[-1] == b"":
        chunks.pop()
    lines: list[RawLine] = []
    for index, chunk in enumerate(chunks, start=1):
        if len(chunk) != record_length:
            report.error(
                "INVALID_RECORD_LENGTH",
                f"Registro com {len(chunk)} posições; esperado {record_length}",
                line=index,
            )
        lines.append(RawLine(index, chunk))
    return lines


def check_sequence(numbers: list[tuple[int, str | None]], report: ValidationReport) -> None:
    """Confere o número sequencial (posições 395-400 nos leiautes CNAB 400)."""
    for expected, (line, value) in enumerate(numbers, start=1):
        if value is None or not value.isdigit() or int(value) != expected:
            report.error(
                "INVALID_SEQUENCE",
                f"Número sequencial {value!r}; esperado {expected:06d}",
                line=line,
                field="numero_sequencial",
            )
