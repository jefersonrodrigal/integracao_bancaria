"""Validações genéricas brasileiras (regras internas da aplicação, não do manual Itaú)."""

from __future__ import annotations

from app.domain.enums import DocumentType

BRAZILIAN_STATES = frozenset(
    [
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    ]
)


def only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def is_valid_cpf(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(cpf[i]) * (size + 1 - i) for i in range(size))
        digit = (total * 10) % 11 % 10
        if digit != int(cpf[size]):
            return False
    return True


def is_valid_cnpj(cnpj: str) -> bool:
    """CNPJ numérico. O CNPJ alfanumérico (2026) não cabe no campo 9(14) do manual de 2017."""
    if len(cnpj) != 14 or not cnpj.isdigit() or cnpj == cnpj[0] * 14:
        return False
    for size in (12, 13):
        weights = list(range(size - 7, 1, -1)) + list(range(9, 1, -1))
        total = sum(int(cnpj[i]) * weights[i] for i in range(size))
        remainder = total % 11
        digit = 0 if remainder < 2 else 11 - remainder
        if digit != int(cnpj[size]):
            return False
    return True


def is_valid_document(document_type: DocumentType, document: str) -> bool:
    if document_type is DocumentType.CPF:
        return is_valid_cpf(document)
    return is_valid_cnpj(document)
