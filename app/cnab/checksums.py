"""Dígitos verificadores."""

from __future__ import annotations


def mod10(digits: str) -> int:
    """Módulo 10 com pesos 2,1,2,1... da direita para a esquerda, somando os algarismos
    de cada produto. DAC = 10 - resto; resto 0 => DAC 0.

    Itaú CNAB 400: Nota 23 (p.34-35), Anexo 3 (p.55) e Anexo 4 (p.56-57).
    """
    if not digits.isdigit():
        raise ValueError("somente dígitos")
    total = 0
    for index, char in enumerate(reversed(digits)):
        product = int(char) * (2 if index % 2 == 0 else 1)
        total += product // 10 + product % 10
    remainder = total % 10
    return 0 if remainder == 0 else 10 - remainder
